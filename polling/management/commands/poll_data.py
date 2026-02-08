import os
import time
import logging
import requests
from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.timezone import now

from core.models import (
    Symbol, Market,
    IndiaStocksIndexes, UsStocksIndexes, InternationalStocksIndexes,
    Crypto, PreciousMetals,
    DataPollingStatus, PollingLog,
)

logger = logging.getLogger(__name__)

# Market name → Django model mapping
TABLE_MODEL_MAP = {
    'india_stocks_indexes': IndiaStocksIndexes,
    'us_stocks_indexes': UsStocksIndexes,
    'international_stocks_indexes': InternationalStocksIndexes,
    'crypto': Crypto,
    'precious_metals': PreciousMetals,
}


class Command(BaseCommand):
    help = 'Polls market data from MarketVibes internal API'

    def add_arguments(self, parser):
        parser.add_argument('--symbol', type=str, help='Symbol name (e.g. NIFTY50). Comma-separated for multiple.')
        parser.add_argument('--allindia', action='store_true', help='Poll all Indian stock indexes')
        parser.add_argument('--allus', action='store_true', help='Poll all US stock indexes')
        parser.add_argument('--allcrypto', action='store_true', help='Poll all crypto symbols')
        parser.add_argument('--allmetals', action='store_true', help='Poll all precious metals')
        parser.add_argument('--allinternational', action='store_true', help='Poll all international stock indexes')
        parser.add_argument('--allindexes', action='store_true', help='Poll all symbols across all markets')
        parser.add_argument('--latest_only', action='store_true', help='Only fetch the most recent entry')
        parser.add_argument('--from_date', type=str, help='Fetch data from this date (YYYY-MM-DD)')
        parser.add_argument('--reset', action='store_true', help='Wipe existing data for the symbol(s) before polling')

    def handle(self, *args, **options):
        symbols_to_process = self._resolve_symbols(options)

        if not symbols_to_process:
            self.stderr.write("No valid symbols to process. Use --symbol, --allindia, --allus, --allindexes, etc.")
            return

        self.stdout.write(f"Processing {len(symbols_to_process)} symbol(s)")

        for symbol_name, symbol_id, table_model in symbols_to_process:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Processing {symbol_name} (ID: {symbol_id})")
            self.stdout.write(f"{'='*60}")
            self._process_symbol(symbol_name, symbol_id, table_model, options)

    def _resolve_symbols(self, options):
        """Resolve command flags into a list of (symbol_name, symbol_id, table_model) tuples."""
        symbols = []

        if options.get('allindia'):
            symbols.extend(self._get_symbols_for_market('india_stocks_indexes'))
        if options.get('allus'):
            symbols.extend(self._get_symbols_for_market('us_stocks_indexes'))
        if options.get('allcrypto'):
            symbols.extend(self._get_symbols_for_market('crypto'))
        if options.get('allmetals'):
            symbols.extend(self._get_symbols_for_market('precious_metals'))
        if options.get('allinternational'):
            symbols.extend(self._get_symbols_for_market('international_stocks_indexes'))
        if options.get('allindexes'):
            for market_name in TABLE_MODEL_MAP:
                symbols.extend(self._get_symbols_for_market(market_name))

        # --symbol flag (supports comma-separated)
        if not symbols and options.get('symbol'):
            symbol_names = [s.strip() for s in options['symbol'].split(',') if s.strip()]
            for name in symbol_names:
                try:
                    sym = Symbol.objects.get(name__iexact=name)
                    market_name = sym.market.name
                    if market_name not in TABLE_MODEL_MAP:
                        logger.error(f"Market '{market_name}' not recognized for symbol '{name}'")
                        continue
                    symbols.append((sym.name, sym.id, TABLE_MODEL_MAP[market_name]))
                except Symbol.DoesNotExist:
                    logger.error(f"Symbol '{name}' not found in database")

        return symbols

    def _get_symbols_for_market(self, market_name):
        """Get all symbols for a given market."""
        table_model = TABLE_MODEL_MAP[market_name]
        syms = Symbol.objects.filter(market__name=market_name)
        result = [(s.name, s.id, table_model) for s in syms]
        logger.info(f"Found {len(result)} symbols for {market_name}")
        return result

    def _process_symbol(self, symbol_name, symbol_id, table_model, options):
        """Poll data for a single symbol from MarketVibes API and save to DB."""
        start_time = time.time()

        # Update polling status
        self._update_polling_status(symbol_id, symbol_name, 'processing')

        try:
            # Reset if requested
            if options.get('reset'):
                count = table_model.objects.filter(symbol_id=symbol_id).count()
                table_model.objects.filter(symbol_id=symbol_id).delete()
                self.stdout.write(f"  Reset: deleted {count} existing rows for {symbol_name}")

            # Fetch from MV API
            data = self._fetch_from_marketvibes(symbol_name, options)
            if data is None:
                self._update_polling_status(symbol_id, symbol_name, 'failed')
                self._log_polling(symbol_id, 'failed', time.time() - start_time, error='API fetch failed')
                self.stderr.write(f"  FAILED: API fetch failed for {symbol_name}")
                return

            results = data.get('results', [])
            if not results:
                self.stdout.write(f"  No data returned for {symbol_name}")
                self._update_polling_status(symbol_id, symbol_name, 'ready')
                self._log_polling(symbol_id, 'success', time.time() - start_time, rows=0)
                return

            market_name = data.get('market', '')
            self.stdout.write(f"  Received {len(results)} rows from MV")
            rows_saved = self._save_results(symbol_id, table_model, market_name, results, options)

            elapsed = time.time() - start_time
            self.stdout.write(self.style.SUCCESS(f"  Done: {rows_saved} rows in {elapsed:.1f}s"))
            self._update_polling_status(symbol_id, symbol_name, 'ready')
            self._log_polling(symbol_id, 'success', elapsed, rows=rows_saved)

        except Exception as e:
            elapsed = time.time() - start_time
            self.stderr.write(self.style.ERROR(f"  ERROR: {symbol_name}: {e}"))
            self._update_polling_status(symbol_id, symbol_name, 'failed')
            self._log_polling(symbol_id, 'failed', elapsed, error=str(e))

    def _fetch_from_marketvibes(self, symbol_name, options):
        """Call MarketVibes internal API for a symbol."""
        host = os.getenv('MARKETVIBES_HOST', 'http://localhost:8001')
        api_key = os.getenv('MV_INTERNAL_API_KEY', '')
        url = f"{host}/api/claritybox/market-data/{symbol_name}/"

        params = {}
        if options.get('latest_only'):
            params['latest_only'] = 'true'
        if options.get('from_date'):
            params['from_date'] = options['from_date']

        headers = {'X-Internal-API-Key': api_key}

        logger.info(f"Fetching: {url} (params: {params})")

        try:
            response = requests.get(url, headers=headers, params=params, timeout=60)
            if response.status_code == 403:
                logger.error("Authentication failed. Check MV_INTERNAL_API_KEY in .env")
                return None
            if response.status_code == 404:
                logger.error(f"Symbol '{symbol_name}' not found on MarketVibes")
                return None
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    def _save_results(self, symbol_id, table_model, market_name, results, options):
        """Save API results to the appropriate data table.

        Uses update_or_create to prevent duplicates:
        - If a row with the same (symbol_id, price_timestamp) exists, it updates all fields.
        - If not, it creates a new row.
        - Running the same poll twice is safe — it overwrites with latest data from MV.
        """
        rows_created = 0
        rows_updated = 0

        for row in results:
            timestamp = row.get('price_timestamp')
            if not timestamp:
                continue

            fields = self._build_fields(row, market_name)

            obj, created = table_model.objects.update_or_create(
                symbol_id=symbol_id,
                price_timestamp=timestamp,
                defaults=fields,
            )

            if created:
                rows_created += 1
            else:
                rows_updated += 1

        self.stdout.write(f"  -> {rows_created} new, {rows_updated} updated")
        return rows_created + rows_updated

    def _build_fields(self, row, market_name):
        """Build a dict of fields to save from an API result row."""
        fields = {
            'open': row.get('open'),
            'high': row.get('high'),
            'low': row.get('low'),
            'close': row.get('close'),
            'volume_number': row.get('volume_number'),
            'mv_score': row.get('smart_index_st'),
            'aes_leverage_moderate': row.get('aes_leverage_moderate'),
            'aes_leverage_aggressive': row.get('aes_leverage_aggressive'),
        }

        # Crypto-specific fields
        if market_name == 'crypto':
            fields['volume_usd'] = row.get('volume_usd', 0)
            fields['bitmex_funding_rate'] = row.get('bitmex_funding_rate')

        # International-specific fields
        if market_name == 'international_stocks_indexes':
            fields['region'] = row.get('region')

        return fields

    def _update_polling_status(self, symbol_id, symbol_name, status):
        """Update or create polling status for a symbol."""
        try:
            symbol = Symbol.objects.get(id=symbol_id)
            obj, created = DataPollingStatus.objects.update_or_create(
                symbol_id=symbol_id,
                defaults={
                    'market': symbol.market,
                    'symbol_name': symbol_name,
                    'market_name': symbol.market.name,
                    'status': status,
                    'last_updated_at': now(),
                },
            )
        except Exception as e:
            logger.warning(f"Could not update polling status for {symbol_name}: {e}")

    def _log_polling(self, symbol_id, status, elapsed, rows=None, error=None):
        """Write a polling log entry."""
        try:
            symbol = Symbol.objects.get(id=symbol_id)
            PollingLog.objects.create(
                market=symbol.market,
                symbol=symbol,
                status=status,
                rows_updated=rows,
                error_message=error,
                time_to_execute=Decimal(str(round(elapsed, 2))),
            )
        except Exception as e:
            logger.warning(f"Could not write polling log: {e}")
