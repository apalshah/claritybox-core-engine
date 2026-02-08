# ClarityBox Core Engine - Deployment Guide

## Prerequisites
- Python 3.10+
- MySQL 8.0+
- Git

## 1. Clone & Setup Virtual Environment

```bash
git clone <repo-url> claritybox-core-engine
cd claritybox-core-engine
python3 -m venv .venv
source .venv/bin/activate
pip install django requests djangorestframework python-dotenv mysqlclient
```

## 2. Create MySQL Database

```sql
CREATE DATABASE IF NOT EXISTS claritybox CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

If using a dedicated DB user (recommended for production):
```sql
CREATE USER 'claritybox_user'@'localhost' IDENTIFIED BY '<strong-password>';
GRANT ALL PRIVILEGES ON claritybox.* TO 'claritybox_user'@'localhost';
FLUSH PRIVILEGES;
```

## 3. Environment Variables

Create `.env` in the project root:

```env
SECRET_KEY=<generate-a-strong-secret-key>
DEBUG=False

DATABASE_NAME=claritybox
DATABASE_USER=claritybox_user
DATABASE_PASSWORD=<your-db-password>
DATABASE_HOST=localhost
DATABASE_PORT=3306

MARKETVIBES_HOST=http://localhost:8000
MV_INTERNAL_API_KEY=<shared-api-key-matching-marketvibes>
```

Generate a secret key:
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Generate an API key (must match MarketVibes `.env`):
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Important:** The `MV_INTERNAL_API_KEY` must be identical in both ClarityBox `.env` and MarketVibes `.env`. Generate a new key for production — do not reuse the dev key.

## 4. Run Migrations

```bash
source .venv/bin/activate
python manage.py migrate
```

## 5. Seed Reference Data

```bash
mysql -u claritybox_user -p claritybox < seed_reference_data.sql
```

IDs must match MarketVibes exactly (4 regions, 7 countries, 5 markets, 23 symbols).

## 6. Poll Data from MarketVibes

See [Polling Guide](#polling-data-from-marketvibes) below for full usage.

Initial full load (all symbols, all history):
```bash
python manage.py poll_data --allindexes
```

## 7. Create Superuser

```bash
python manage.py createsuperuser
```

## 8. Run the Server

Development:
```bash
python manage.py runserver 8002
```

Production (with gunicorn):
```bash
pip install gunicorn
gunicorn core_engine.wsgi:application --bind 0.0.0.0:8002 --workers 3
```

## 9. Verify

- Admin: http://localhost:8002/admin/
- Check DB: `mysql -u root claritybox -e "SELECT COUNT(*) FROM symbols;"`  (should return 23)

---

## Project Structure

```
claritybox-core-engine/
├── .venv/                  # Virtual environment
├── .env                    # Environment variables (NOT in git)
├── .gitignore
├── manage.py
├── seed_reference_data.sql # Reference data INSERT statements
├── DEPLOYMENT.md           # This file
├── core_engine/            # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                   # Shared models (User, markets, symbols, data tables)
├── polling/                # Polls data from MarketVibes
│   └── management/commands/poll_data.py
├── score_engine/           # Computes ClarityBox scores (not yet built)
├── client_api/             # REST API for React client (not yet built)
└── reporting_api/          # REST API for reporting server (not yet built)
```

## Ports

| Service                | Port |
|------------------------|------|
| MarketVibes            | 8000 |
| ClarityBox Core Engine | 8002 |

---

## Internal API Contract (MarketVibes ↔ ClarityBox)

### Authentication
- Header: `X-Internal-API-Key`
- Value: must match `MV_INTERNAL_API_KEY` in both `.env` files
- Returns `403 Forbidden` if missing or wrong

### Endpoint
```
GET {MARKETVIBES_HOST}/api/claritybox/market-data/<symbol_name>/
```

### Query Parameters
| Param | Type | Description |
|-------|------|-------------|
| `from_date` | `YYYY-MM-DD` (optional) | Return data from this date onward |
| `latest_only` | `true` (optional) | Return only the most recent entry |

### Response Format
```json
{
  "symbol": "NIFTY50",
  "market": "india_stocks_indexes",
  "count": 7413,
  "results": [
    {
      "price_timestamp": "2026-02-06T00:00:00+00:00",
      "open": "25605.80",
      "high": "25703.95",
      "low": "25491.90",
      "close": "25693.70",
      "volume_number": 375500,
      "smart_index_st": 49,
      "aes_leverage_moderate": 1,
      "aes_leverage_aggressive": 1
    }
  ]
}
```

### Field Mapping (MarketVibes → ClarityBox)
| MV API Field | ClarityBox Column | Notes |
|--------------|-------------------|-------|
| `smart_index_st` | `mv_score` | MarketVibes short-term score |
| `aes_leverage_moderate` | `aes_leverage_moderate` | Null for most rows, set on zone flips |
| `aes_leverage_aggressive` | `aes_leverage_aggressive` | Null for most rows, set on zone flips |
| All other fields | Same name | Direct mapping |

### Extra Fields by Market
| Market | Extra fields |
|--------|-------------|
| `crypto` | `volume_usd`, `bitmex_funding_rate` |
| `international_stocks_indexes` | `region` |

---

## Polling Data from MarketVibes

### Command: `poll_data`

```bash
source .venv/bin/activate
python manage.py poll_data [OPTIONS]
```

### Symbol Selection

```bash
# Single symbol
python manage.py poll_data --symbol=NIFTY50

# Multiple symbols (comma-separated)
python manage.py poll_data --symbol=NIFTY50,SENSEX,NIFTYBANK

# All Indian indexes (9 symbols)
python manage.py poll_data --allindia

# All US indexes (4 symbols)
python manage.py poll_data --allus

# All crypto (3 symbols)
python manage.py poll_data --allcrypto

# All precious metals (2 symbols)
python manage.py poll_data --allmetals

# All international indexes (5 symbols)
python manage.py poll_data --allinternational

# Everything (23 symbols)
python manage.py poll_data --allindexes
```

### Data Modes

```bash
# Full history (default) — fetches all data from the beginning
python manage.py poll_data --symbol=NIFTY50

# Latest only — fetches only the most recent entry (daily update)
python manage.py poll_data --allindexes --latest_only

# From a specific date
python manage.py poll_data --symbol=NIFTY50 --from_date=2025-01-01

# Reset — deletes existing data for symbol(s) then re-fetches everything
python manage.py poll_data --allindexes --reset
```

### Deduplication

Polling is **idempotent** — safe to run multiple times:
- Each row is keyed by `(symbol_id, price_timestamp)`
- If a row already exists, it **updates** all fields (OHLCV, mv_score, aes values)
- If a row is new, it **inserts**
- No duplicates are ever created
- Null values from MV are stored as null; non-null values overwrite previous values

### Typical Usage

```bash
# Initial setup (run once)
python manage.py poll_data --allindexes

# Daily update (run after MarketVibes finishes processing)
python manage.py poll_data --allindexes --latest_only

# Re-sync a specific symbol (if something went wrong)
python manage.py poll_data --symbol=NIFTY50 --reset

# Full reset of everything
python manage.py poll_data --allindexes --reset
```

### Monitoring

Polling status is tracked in `data_polling_status` table:
```sql
SELECT symbol_name, status, last_updated_at FROM data_polling_status ORDER BY market_name;
```

Detailed logs in `polling_logs` table:
```sql
SELECT symbol_id, status, rows_updated, time_to_execute, error_message
FROM polling_logs ORDER BY created_at DESC LIMIT 20;
```

---

## Database Reset (if needed)

To wipe all market data but keep reference tables:
```sql
TRUNCATE TABLE india_stocks_indexes;
TRUNCATE TABLE us_stocks_indexes;
TRUNCATE TABLE international_stocks_indexes;
TRUNCATE TABLE crypto;
TRUNCATE TABLE precious_metals;
TRUNCATE TABLE data_polling_status;
TRUNCATE TABLE polling_logs;
```

Then re-poll:
```bash
python manage.py poll_data --allindexes
```
