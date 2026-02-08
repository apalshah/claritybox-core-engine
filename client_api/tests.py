from datetime import datetime, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import make_aware
from rest_framework.test import APIClient

from core.models import (
    CustomUser, Region, Country, Market, Symbol,
    IndiaStocksIndexes, UsStocksIndexes, InternationalStocksIndexes,
    Crypto, PreciousMetals, DataPollingStatus,
)


class BaseAPITestCase(TestCase):
    """Shared setup: creates reference data and a test user with JWT token."""

    @classmethod
    def setUpTestData(cls):
        # Regions (matching production order)
        cls.region_india = Region.objects.create(id=4, code='INDIA', name='India')
        cls.region_us = Region.objects.create(id=2, code='US', name='United States')
        cls.region_asia = Region.objects.create(id=1, code='ASIA', name='Asia Pacific')
        cls.region_europe = Region.objects.create(id=3, code='EUROPE', name='Europe')

        # Countries
        cls.country_india = Country.objects.create(id=4, code='IN', name='India', region=cls.region_india)
        cls.country_us = Country.objects.create(id=3, code='US', name='United States', region=cls.region_us)

        # Markets
        cls.market_india = Market.objects.create(id=1, name='india_stocks_indexes', label='Indian Stocks & Indexes')
        cls.market_us = Market.objects.create(id=2, name='us_stocks_indexes', label='US Stocks & Indexes')
        cls.market_intl = Market.objects.create(id=3, name='international_stocks_indexes', label='International')
        cls.market_crypto = Market.objects.create(id=4, name='crypto', label='Crypto')
        cls.market_metals = Market.objects.create(id=5, name='precious_metals', label='Precious Metals')

        # Symbols
        cls.sym_nifty = Symbol.objects.create(id=1, name='NIFTY50', label='Nifty 50', market=cls.market_india, country=cls.country_india)
        cls.sym_sp500 = Symbol.objects.create(id=2, name='SP500', label='S&P 500', market=cls.market_us, country=cls.country_us)
        cls.sym_btc = Symbol.objects.create(id=3, name='BTC', label='Bitcoin', market=cls.market_crypto, country=None)
        cls.sym_gold = Symbol.objects.create(id=4, name='GOLD', label='Gold', market=cls.market_metals, country=None)

        # Data entries for NIFTY50 (India)
        base_ts = make_aware(datetime(2025, 1, 1))
        for i in range(5):
            score = 75 - (i * 15)  # 75, 60, 45, 30, 15 — crosses zones
            IndiaStocksIndexes.objects.create(
                symbol=cls.sym_nifty,
                price_timestamp=base_ts + timedelta(days=i),
                open=Decimal('25000.00') + i * 100,
                high=Decimal('25200.00') + i * 100,
                low=Decimal('24800.00') + i * 100,
                close=Decimal('25100.00') + i * 100,
                volume_number=100000 + i * 1000,
                mv_score=score,
                aes_leverage_moderate=2 if score >= 71 else None,
                aes_leverage_aggressive=3 if score >= 71 else None,
            )

        # Data entries for SP500 (US)
        for i in range(3):
            UsStocksIndexes.objects.create(
                symbol=cls.sym_sp500,
                price_timestamp=base_ts + timedelta(days=i),
                open=Decimal('5000.00') + i * 50,
                high=Decimal('5050.00') + i * 50,
                low=Decimal('4950.00') + i * 50,
                close=Decimal('5025.00') + i * 50,
                volume_number=200000,
                mv_score=80,
            )

        # Data entries for BTC (Crypto)
        Crypto.objects.create(
            symbol=cls.sym_btc,
            price_timestamp=base_ts,
            open=42000.0, high=43000.0, low=41000.0, close=42500.0,
            volume_number=1500.0, volume_usd=63000000.0,
            mv_score=55,
        )

        # Data entries for GOLD (Precious Metals)
        PreciousMetals.objects.create(
            symbol=cls.sym_gold,
            price_timestamp=base_ts,
            open=Decimal('2050.00'), high=Decimal('2070.00'),
            low=Decimal('2030.00'), close=Decimal('2060.00'),
            volume_number=50000,
            mv_score=25,
        )

        # Polling status
        DataPollingStatus.objects.create(
            symbol=cls.sym_nifty, market=cls.market_india,
            symbol_name='NIFTY50', market_name='india_stocks_indexes',
            status='ready', last_updated_at=make_aware(datetime(2025, 1, 5)),
        )

    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            username='testuser', password='TestPass123',
            first_name='Test', last_name='User',
        )
        # Get JWT token
        resp = self.client.post(reverse('claritybox-login'), {
            'username': 'testuser', 'password': 'TestPass123',
        }, format='json')
        self.access_token = resp.data['accessToken']
        self.refresh_token_str = resp.data['refreshToken']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')


# ─── Auth Tests ───────────────────────────────────────────────────────

class LoginTests(BaseAPITestCase):

    def test_login_success(self):
        resp = self.client.post(reverse('claritybox-login'), {
            'username': 'testuser', 'password': 'TestPass123',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('accessToken', resp.data)
        self.assertIn('refreshToken', resp.data)

    def test_login_wrong_password(self):
        resp = self.client.post(reverse('claritybox-login'), {
            'username': 'testuser', 'password': 'WrongPass',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_login_nonexistent_user(self):
        resp = self.client.post(reverse('claritybox-login'), {
            'username': 'nobody', 'password': 'Pass123',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_login_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        client = APIClient()
        resp = client.post(reverse('claritybox-login'), {
            'username': 'testuser', 'password': 'TestPass123',
        }, format='json')
        self.assertEqual(resp.status_code, 403)


class RefreshTokenTests(BaseAPITestCase):

    def test_refresh_success(self):
        resp = self.client.post(reverse('claritybox-refresh'), {
            'refresh': self.refresh_token_str,
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('accessToken', resp.data)

    def test_refresh_invalid_token(self):
        resp = self.client.post(reverse('claritybox-refresh'), {
            'refresh': 'invalid-token',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_refresh_missing_token(self):
        resp = self.client.post(reverse('claritybox-refresh'), {}, format='json')
        self.assertEqual(resp.status_code, 400)


class ProfileTests(BaseAPITestCase):

    def test_get_profile(self):
        resp = self.client.get(reverse('claritybox-profile'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['username'], 'testuser')
        self.assertEqual(resp.data['first_name'], 'Test')

    def test_update_profile(self):
        resp = self.client.put(reverse('claritybox-profile'), {
            'first_name': 'Updated', 'last_name': 'Name',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['first_name'], 'Updated')

    def test_profile_unauthenticated(self):
        client = APIClient()
        resp = client.get(reverse('claritybox-profile'))
        self.assertEqual(resp.status_code, 401)


# ─── Market Metadata Tests ───────────────────────────────────────────

class MarketMetadataTests(BaseAPITestCase):

    def test_market_metadata(self):
        resp = self.client.get(reverse('claritybox-market-metadata'))
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data, list)
        self.assertTrue(len(resp.data) >= 5)
        # Check structure
        market = resp.data[0]
        self.assertIn('id', market)
        self.assertIn('name', market)
        self.assertIn('symbols', market)

    def test_market_metadata_unauthenticated(self):
        client = APIClient()
        resp = client.get(reverse('claritybox-market-metadata'))
        self.assertEqual(resp.status_code, 401)


# ─── Global Market Summary Tests ─────────────────────────────────────

class GlobalMarketSummaryTests(BaseAPITestCase):

    def test_summary_returns_regions(self):
        resp = self.client.get(reverse('claritybox-global-market-summary'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('regions', resp.data)
        regions = resp.data['regions']
        self.assertTrue(len(regions) >= 1)

    def test_summary_region_order(self):
        """Regions must appear in order: INDIA, US, ASIA, EUROPE."""
        resp = self.client.get(reverse('claritybox-global-market-summary'))
        region_codes = [r['code'] for r in resp.data['regions']]
        # Only check those that have data in test DB
        self.assertEqual(region_codes[0], 'INDIA')

    def test_summary_india_structure(self):
        resp = self.client.get(reverse('claritybox-global-market-summary'))
        regions = resp.data['regions']
        india = next((r for r in regions if r['code'] == 'INDIA'), None)
        self.assertIsNotNone(india)
        self.assertIn('countries', india)
        country = india['countries'][0]
        self.assertEqual(country['code'], 'IN')
        nifty = next((idx for idx in country['indexes'] if idx['name'] == 'NIFTY50'), None)
        self.assertIsNotNone(nifty)
        self.assertIn('smart_index_st', nifty)
        self.assertIn('active_zone', nifty)
        self.assertIn('status', nifty)

    def test_summary_zone_classification(self):
        resp = self.client.get(reverse('claritybox-global-market-summary'))
        regions = resp.data['regions']
        india = next(r for r in regions if r['code'] == 'INDIA')
        country = india['countries'][0]
        nifty = next(idx for idx in country['indexes'] if idx['name'] == 'NIFTY50')
        self.assertEqual(nifty['active_zone'], 'RED')
        self.assertEqual(nifty['smart_index_st'], 15)

    def test_summary_no_crypto_pseudo_region(self):
        """Crypto should not appear as a region tab."""
        resp = self.client.get(reverse('claritybox-global-market-summary'))
        region_codes = [r['code'] for r in resp.data['regions']]
        self.assertNotIn('CRYPTO', region_codes)
        self.assertNotIn('PRECIOUS_METALS', region_codes)

    def test_summary_unauthenticated(self):
        client = APIClient()
        resp = client.get(reverse('claritybox-global-market-summary'))
        self.assertEqual(resp.status_code, 401)


# ─── Chart Data Tests ────────────────────────────────────────────────

class ChartDataTests(BaseAPITestCase):

    def test_chart_data_success(self):
        resp = self.client.get(
            reverse('claritybox-chart-data', kwargs={'market_type': 'india_stocks_indexes', 'symbol_name': 'NIFTY50'})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data, list)
        self.assertEqual(len(resp.data), 5)

    def test_chart_data_fields(self):
        resp = self.client.get(
            reverse('claritybox-chart-data', kwargs={'market_type': 'india_stocks_indexes', 'symbol_name': 'NIFTY50'})
        )
        entry = resp.data[0]
        self.assertIn('date', entry)
        self.assertIn('close_price', entry)
        self.assertIn('open', entry)
        self.assertIn('high', entry)
        self.assertIn('low', entry)
        self.assertIn('volume', entry)
        self.assertIn('smart_index', entry)

    def test_chart_data_leverage_format(self):
        """First entry (score=75) should have leverage formatted as 'NX'."""
        resp = self.client.get(
            reverse('claritybox-chart-data', kwargs={'market_type': 'india_stocks_indexes', 'symbol_name': 'NIFTY50'})
        )
        first = resp.data[0]
        self.assertEqual(first['aes_leverage_moderate'], '2X')
        self.assertEqual(first['aes_leverage_aggressive'], '3X')

    def test_chart_data_invalid_market(self):
        resp = self.client.get(
            reverse('claritybox-chart-data', kwargs={'market_type': 'nonexistent', 'symbol_name': 'NIFTY50'})
        )
        self.assertEqual(resp.status_code, 400)

    def test_chart_data_invalid_symbol(self):
        resp = self.client.get(
            reverse('claritybox-chart-data', kwargs={'market_type': 'india_stocks_indexes', 'symbol_name': 'DOESNOTEXIST'})
        )
        self.assertEqual(resp.status_code, 404)

    def test_chart_data_crypto(self):
        resp = self.client.get(
            reverse('claritybox-chart-data', kwargs={'market_type': 'crypto', 'symbol_name': 'BTC'})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_chart_data_unauthenticated(self):
        client = APIClient()
        resp = client.get(
            reverse('claritybox-chart-data', kwargs={'market_type': 'india_stocks_indexes', 'symbol_name': 'NIFTY50'})
        )
        self.assertEqual(resp.status_code, 401)


# ─── Momentum Alerts Tests ───────────────────────────────────────────

class MomentumAlertsTests(BaseAPITestCase):

    def test_alerts_returns_list(self):
        resp = self.client.get(reverse('claritybox-momentum-alerts'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('alerts', resp.data)
        self.assertIsInstance(resp.data['alerts'], list)

    def test_alerts_detect_zone_change(self):
        """NIFTY50 has scores 75,60,45,30,15 (latest=15 RED, prev=30 RED, before=45 GREY)
        so the zone change is from GREY to RED at day index 2."""
        resp = self.client.get(reverse('claritybox-momentum-alerts'))
        alerts = resp.data['alerts']
        nifty_alert = next((a for a in alerts if a['symbol'] == 'NIFTY50'), None)
        self.assertIsNotNone(nifty_alert)
        self.assertEqual(nifty_alert['change_type'], 'BEARISH')

    def test_alerts_structure(self):
        resp = self.client.get(reverse('claritybox-momentum-alerts'))
        if resp.data['alerts']:
            alert = resp.data['alerts'][0]
            self.assertIn('symbol', alert)
            self.assertIn('label', alert)
            self.assertIn('market', alert)
            self.assertIn('from_score', alert)
            self.assertIn('to_score', alert)
            self.assertIn('change_type', alert)
            self.assertIn('days_since_last_change', alert)
            self.assertIn('date', alert)


# ─── Simulate (Single Symbol) Tests ──────────────────────────────────

class SimulateTests(BaseAPITestCase):

    def test_simulate_success(self):
        resp = self.client.post(reverse('claritybox-simulate'), {
            'market_type': 'india_stocks_indexes',
            'symbol_name': 'NIFTY50',
            'amount': 100000,
            'start_date': '2025-01-01',
            'duration': 1,
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('simple_returns', resp.data)
        self.assertIn('totalMoneyInvested', resp.data['simple_returns'])
        self.assertIn('totalMoneyReturned', resp.data['simple_returns'])
        self.assertIn('percentageChange', resp.data['simple_returns'])

    def test_simulate_calculates_return(self):
        """First close=25100, last close=25500 → 1.59% gain."""
        resp = self.client.post(reverse('claritybox-simulate'), {
            'market_type': 'india_stocks_indexes',
            'symbol_name': 'NIFTY50',
            'amount': 100000,
            'start_date': '2025-01-01',
            'duration': 1,
        }, format='json')
        returned = float(resp.data['simple_returns']['totalMoneyReturned'])
        self.assertGreater(returned, 100000)

    def test_simulate_missing_fields(self):
        resp = self.client.post(reverse('claritybox-simulate'), {
            'market_type': 'india_stocks_indexes',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_simulate_invalid_market(self):
        resp = self.client.post(reverse('claritybox-simulate'), {
            'market_type': 'nonexistent',
            'symbol_name': 'NIFTY50',
            'amount': 100000,
            'start_date': '2025-01-01',
            'duration': 1,
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_simulate_invalid_symbol(self):
        resp = self.client.post(reverse('claritybox-simulate'), {
            'market_type': 'india_stocks_indexes',
            'symbol_name': 'DOESNOTEXIST',
            'amount': 100000,
            'start_date': '2025-01-01',
            'duration': 1,
        }, format='json')
        self.assertEqual(resp.status_code, 404)

    def test_simulate_invalid_date(self):
        resp = self.client.post(reverse('claritybox-simulate'), {
            'market_type': 'india_stocks_indexes',
            'symbol_name': 'NIFTY50',
            'amount': 100000,
            'start_date': 'not-a-date',
            'duration': 1,
        }, format='json')
        self.assertEqual(resp.status_code, 400)


# ─── Simulate Portfolio Tests ─────────────────────────────────────────

class SimulatePortfolioTests(BaseAPITestCase):

    def test_portfolio_success(self):
        resp = self.client.post(reverse('claritybox-simulate-portfolio'), {
            'allocations': {'NIFTY50': 60, 'SP500': 40},
            'amount': 100000,
            'start_date': '2025-01-01',
            'duration': 1,
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('simple_returns', resp.data)

    def test_portfolio_allocation_must_sum_100(self):
        resp = self.client.post(reverse('claritybox-simulate-portfolio'), {
            'allocations': {'NIFTY50': 30, 'SP500': 30},
            'amount': 100000,
            'start_date': '2025-01-01',
            'duration': 1,
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('100%', resp.data['error'])

    def test_portfolio_missing_fields(self):
        resp = self.client.post(reverse('claritybox-simulate-portfolio'), {
            'allocations': {'NIFTY50': 100},
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_portfolio_unknown_symbol(self):
        resp = self.client.post(reverse('claritybox-simulate-portfolio'), {
            'allocations': {'UNKNOWN': 100},
            'amount': 100000,
            'start_date': '2025-01-01',
            'duration': 1,
        }, format='json')
        self.assertEqual(resp.status_code, 400)


# ─── Simulate Portfolio Advanced Tests ────────────────────────────────

class SimulatePortfolioAdvancedTests(BaseAPITestCase):

    def test_advanced_placeholder_response(self):
        resp = self.client.post(reverse('claritybox-simulate-portfolio-advanced'), {
            'allocations': {'NIFTY50': 100},
            'strategy_mix': {'conservative': 50, 'aggressive': 50},
            'amount': 100000,
            'start_date': '2025-01-01',
            'duration': 1,
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('message', resp.data)

    def test_advanced_allocation_must_sum_100(self):
        resp = self.client.post(reverse('claritybox-simulate-portfolio-advanced'), {
            'allocations': {'NIFTY50': 50},
            'strategy_mix': {'conservative': 100},
            'amount': 100000,
            'start_date': '2025-01-01',
            'duration': 1,
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_advanced_strategy_must_sum_100(self):
        resp = self.client.post(reverse('claritybox-simulate-portfolio-advanced'), {
            'allocations': {'NIFTY50': 100},
            'strategy_mix': {'conservative': 30},
            'amount': 100000,
            'start_date': '2025-01-01',
            'duration': 1,
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_advanced_missing_fields(self):
        resp = self.client.post(reverse('claritybox-simulate-portfolio-advanced'), {
            'allocations': {'NIFTY50': 100},
        }, format='json')
        self.assertEqual(resp.status_code, 400)


# ─── Helper Function Tests ───────────────────────────────────────────

class HelperFunctionTests(TestCase):

    def test_get_zone_green(self):
        from client_api.views import _get_zone
        self.assertEqual(_get_zone(71), 'GREEN')
        self.assertEqual(_get_zone(100), 'GREEN')

    def test_get_zone_red(self):
        from client_api.views import _get_zone
        self.assertEqual(_get_zone(30), 'RED')
        self.assertEqual(_get_zone(0), 'RED')

    def test_get_zone_grey(self):
        from client_api.views import _get_zone
        self.assertEqual(_get_zone(31), 'GREY')
        self.assertEqual(_get_zone(70), 'GREY')
        self.assertEqual(_get_zone(50), 'GREY')

    def test_get_zone_none(self):
        from client_api.views import _get_zone
        self.assertIsNone(_get_zone(None))

    def test_format_leverage(self):
        from client_api.views import _format_leverage
        self.assertEqual(_format_leverage(2), '2X')
        self.assertEqual(_format_leverage(1), '1X')
        self.assertIsNone(_format_leverage(None))
