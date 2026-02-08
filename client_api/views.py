from datetime import datetime, timedelta

from django.utils.timezone import make_aware
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import (
    Region, Country, Market, Symbol, DataPollingStatus,
    IndiaStocksIndexes, UsStocksIndexes, InternationalStocksIndexes,
    Crypto, PreciousMetals,
)

# Market name → model mapping
TABLE_MODEL_MAP = {
    'india_stocks_indexes': IndiaStocksIndexes,
    'us_stocks_indexes': UsStocksIndexes,
    'international_stocks_indexes': InternationalStocksIndexes,
    'crypto': Crypto,
    'precious_metals': PreciousMetals,
}


def _get_zone(score):
    """Determine zone from score."""
    if score is None:
        return None
    if score >= 71:
        return 'GREEN'
    if score <= 30:
        return 'RED'
    return 'GREY'


def _format_leverage(value):
    """Format leverage value for display."""
    if value is None:
        return None
    return f"{value}X"


def _get_score(entry):
    """Get the best available score: cb_score if set, otherwise mv_score."""
    if entry is None:
        return None
    if entry.cb_score is not None:
        return entry.cb_score
    return entry.mv_score


def _get_latest_entry(symbol_id, table_model):
    """Get the most recent data entry for a symbol."""
    return table_model.objects.filter(
        symbol_id=symbol_id
    ).order_by('-price_timestamp').first()


def _get_zone_since(symbol_id, table_model, current_zone):
    """Find when the current zone started by looking back through history."""
    if current_zone is None:
        return None, None

    entries = table_model.objects.filter(
        symbol_id=symbol_id,
        mv_score__isnull=False,
    ).order_by('-price_timestamp').values_list('price_timestamp', 'mv_score', 'cb_score')[:500]

    zone_since_date = None
    zone_entry_value = None

    for ts, mv, cb in entries:
        score = cb if cb is not None else mv
        entry_zone = _get_zone(score)
        if entry_zone != current_zone:
            break
        zone_since_date = ts.strftime('%Y-%m-%d')
        zone_entry_value = score

    return zone_since_date, zone_entry_value


def _build_index_data(symbol, table_model):
    """Build index data dict for a symbol."""
    latest = _get_latest_entry(symbol.id, table_model)
    score = _get_score(latest)
    active_zone = _get_zone(score)
    zone_since_date, zone_entry_value = _get_zone_since(symbol.id, table_model, active_zone)

    polling = DataPollingStatus.objects.filter(symbol_id=symbol.id).first()
    poll_status = polling.status if polling else 'ready'
    last_updated = polling.last_updated_at.isoformat() if polling and polling.last_updated_at else None

    data = {
        'id': symbol.id,
        'name': symbol.name,
        'label': symbol.label,
        'market': symbol.market.name if symbol.market else None,
        'smart_index_st': score,
        'status': poll_status,
        'last_updated_at': last_updated,
        'active_zone': active_zone,
        'zone_since_date': zone_since_date,
        'zone_entry_value': zone_entry_value,
    }

    if latest and latest.aes_leverage_moderate is not None:
        data['aes_leverage_moderate'] = _format_leverage(latest.aes_leverage_moderate)
        data['aes_leverage_aggressive'] = _format_leverage(latest.aes_leverage_aggressive)

    return data


# ─── Market Metadata ───────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def market_metadata(request):
    """Returns available markets and their symbols."""
    markets = Market.objects.all()
    result = []
    for market in markets:
        symbols = Symbol.objects.filter(market=market)
        result.append({
            'id': market.id,
            'name': market.name,
            'label': market.label,
            'symbols': [
                {'id': s.id, 'name': s.name, 'label': s.label}
                for s in symbols
            ],
        })
    return Response(result)


# ─── Global Market Summary V2 (by region) ──────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def global_market_summary_v2(request):
    """Returns all indexes grouped by region > country > indexes with scores."""
    regions = Region.objects.all().order_by('id')
    result = []

    for region in regions:
        countries_data = []
        countries = Country.objects.filter(region=region).order_by('id')

        for country in countries:
            symbols = Symbol.objects.filter(country=country).select_related('market')
            indexes_data = []

            for symbol in symbols:
                market_name = symbol.market.name if symbol.market else None
                table_model = TABLE_MODEL_MAP.get(market_name)
                if not table_model:
                    continue
                indexes_data.append(_build_index_data(symbol, table_model))

            if indexes_data:
                countries_data.append({
                    'code': country.code,
                    'name': country.name,
                    'indexes': indexes_data,
                })

        if countries_data:
            result.append({
                'code': region.code,
                'name': region.name,
                'countries': countries_data,
            })

    # Add crypto and precious metals as separate pseudo-regions
    for market_name, label in [('crypto', 'Crypto'), ('precious_metals', 'Precious Metals')]:
        symbols = Symbol.objects.filter(market__name=market_name)
        if not symbols:
            continue

        table_model = TABLE_MODEL_MAP[market_name]
        indexes_data = [_build_index_data(s, table_model) for s in symbols]

        if indexes_data:
            result.append({
                'code': market_name.upper(),
                'name': label,
                'countries': [{
                    'code': market_name.upper(),
                    'name': label,
                    'indexes': indexes_data,
                }],
            })

    return Response({'regions': result})


# ─── Charts ─────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chart_data(request, market_type, symbol_name):
    """Returns historical chart data for a symbol."""
    table_model = TABLE_MODEL_MAP.get(market_type)
    if not table_model:
        return Response({'error': 'Invalid market type'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        symbol = Symbol.objects.get(name__iexact=symbol_name)
    except Symbol.DoesNotExist:
        return Response({'error': f"Symbol '{symbol_name}' not found"}, status=status.HTTP_404_NOT_FOUND)

    entries = table_model.objects.filter(
        symbol_id=symbol.id
    ).order_by('price_timestamp').values(
        'price_timestamp', 'open', 'high', 'low', 'close', 'volume_number',
        'mv_score', 'cb_score', 'aes_leverage_moderate', 'aes_leverage_aggressive',
    )

    result = []
    for e in entries:
        score = e['cb_score'] if e['cb_score'] is not None else e['mv_score']
        result.append({
            'date': e['price_timestamp'].strftime('%Y-%m-%d'),
            'close_price': float(e['close']) if e['close'] else None,
            'open': float(e['open']) if e['open'] else None,
            'high': float(e['high']) if e['high'] else None,
            'low': float(e['low']) if e['low'] else None,
            'volume': e['volume_number'],
            'smart_index': score,
            'aes_leverage_moderate': _format_leverage(e['aes_leverage_moderate']),
            'aes_leverage_aggressive': _format_leverage(e['aes_leverage_aggressive']),
        })

    return Response(result)


# ─── Momentum Alerts ────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def momentum_alerts(request):
    """Returns recent score zone changes across all symbols."""
    alerts = []

    for market_name, table_model in TABLE_MODEL_MAP.items():
        symbols = Symbol.objects.filter(market__name=market_name).select_related('market')

        for symbol in symbols:
            recent = list(table_model.objects.filter(
                symbol_id=symbol.id,
                mv_score__isnull=False,
            ).order_by('-price_timestamp').values(
                'price_timestamp', 'mv_score', 'cb_score'
            )[:60])

            if len(recent) < 2:
                continue

            current_score = recent[0]['cb_score'] if recent[0]['cb_score'] is not None else recent[0]['mv_score']
            current_zone = _get_zone(current_score)

            for i in range(1, len(recent)):
                prev_score = recent[i]['cb_score'] if recent[i]['cb_score'] is not None else recent[i]['mv_score']
                prev_zone = _get_zone(prev_score)

                if prev_zone != current_zone:
                    change_type = 'BULLISH' if current_zone == 'GREEN' else 'BEARISH' if current_zone == 'RED' else 'NEUTRAL'
                    alerts.append({
                        'symbol': symbol.name,
                        'label': symbol.label,
                        'market': symbol.market.label if symbol.market else market_name,
                        'from_score': prev_score,
                        'to_score': current_score,
                        'change_type': change_type,
                        'days_since_last_change': i,
                        'date': recent[0]['price_timestamp'].strftime('%Y-%m-%d'),
                    })
                    break

    alerts.sort(key=lambda a: a['date'], reverse=True)
    return Response({'alerts': alerts})


# ─── Simulation ─────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def simulate(request):
    """Simulate investment returns for a single symbol."""
    market_type = request.data.get('market_type')
    symbol_name = request.data.get('symbol_name')
    amount = request.data.get('amount')
    start_date = request.data.get('start_date')
    duration = request.data.get('duration')

    if not all([market_type, symbol_name, amount, start_date, duration]):
        return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

    table_model = TABLE_MODEL_MAP.get(market_type)
    if not table_model:
        return Response({'error': 'Invalid market type'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        symbol = Symbol.objects.get(name__iexact=symbol_name)
    except Symbol.DoesNotExist:
        return Response({'error': f"Symbol '{symbol_name}' not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        start = make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
        end = start + timedelta(days=int(duration) * 365)
    except (ValueError, TypeError):
        return Response({'error': 'Invalid start_date format (expected YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

    entries = list(table_model.objects.filter(
        symbol_id=symbol.id,
        price_timestamp__gte=start,
        price_timestamp__lte=end,
    ).order_by('price_timestamp').values('close'))

    if len(entries) < 2:
        return Response({'error': 'Not enough data for the selected period'}, status=status.HTTP_400_BAD_REQUEST)

    amount = float(amount)
    first_close = float(entries[0]['close'])
    last_close = float(entries[-1]['close'])
    simple_return = amount * (last_close / first_close)
    simple_pct = ((last_close / first_close) - 1) * 100

    return Response({
        'symbol': symbol.name,
        'start_date': start_date,
        'end_date': end.strftime('%Y-%m-%d'),
        'initial_amount': amount,
        'simple_returns': {
            'totalMoneyInvested': f"{amount:.2f}",
            'totalMoneyReturned': f"{simple_return:.2f}",
            'percentageChange': f"{simple_pct:.2f}%",
        },
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def simulate_portfolio(request):
    """Simulate portfolio investment returns."""
    allocations = request.data.get('allocations')
    amount = request.data.get('amount')
    start_date = request.data.get('start_date')
    duration = request.data.get('duration')

    if not all([allocations, amount, start_date, duration]):
        return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

    total_allocation = sum(allocations.values())
    if abs(total_allocation - 100) > 1:
        return Response({'error': f'Allocations must sum to 100%, got {total_allocation}%'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        start = make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
        end = start + timedelta(days=int(duration) * 365)
    except (ValueError, TypeError):
        return Response({'error': 'Invalid start_date format (expected YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

    amount = float(amount)
    total_simple = 0

    for sym_name, pct in allocations.items():
        try:
            symbol = Symbol.objects.get(name__iexact=sym_name)
        except Symbol.DoesNotExist:
            return Response({'error': f"Unknown symbol: {sym_name}"}, status=status.HTTP_400_BAD_REQUEST)

        table_model = TABLE_MODEL_MAP.get(symbol.market.name)
        if not table_model:
            continue

        entries = list(table_model.objects.filter(
            symbol_id=symbol.id,
            price_timestamp__gte=start,
            price_timestamp__lte=end,
        ).order_by('price_timestamp').values('close'))

        if len(entries) < 2:
            continue

        first_close = float(entries[0]['close'])
        last_close = float(entries[-1]['close'])
        allocated_amount = amount * (float(pct) / 100)
        total_simple += allocated_amount * (last_close / first_close)

    simple_pct = ((total_simple / amount) - 1) * 100 if amount > 0 else 0

    return Response({
        'simple_returns': {
            'totalMoneyInvested': f"{amount:.2f}",
            'totalMoneyReturned': f"{total_simple:.2f}",
            'percentageChange': f"{simple_pct:.2f}%",
        },
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def simulate_portfolio_advanced(request):
    """Advanced portfolio simulation with strategy mix. Placeholder for score_engine."""
    allocations = request.data.get('allocations')
    strategy_mix = request.data.get('strategy_mix')
    amount = request.data.get('amount')
    start_date = request.data.get('start_date')
    duration = request.data.get('duration')

    if not all([allocations, strategy_mix, amount, start_date, duration]):
        return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

    total_allocation = sum(allocations.values())
    if abs(total_allocation - 100) > 1:
        return Response({'error': f'Allocations must sum to 100%, got {total_allocation}%'}, status=status.HTTP_400_BAD_REQUEST)

    total_strategy = sum(strategy_mix.values())
    if abs(total_strategy - 100) > 1:
        return Response({'error': f'Strategy mix must sum to 100%, got {total_strategy}%'}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'message': 'Advanced portfolio simulation coming soon — requires score_engine',
        'config': {
            'allocations': allocations,
            'strategy_mix': strategy_mix,
            'amount': amount,
            'start_date': start_date,
            'duration': duration,
        },
    })
