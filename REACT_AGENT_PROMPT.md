# ClarityBox UI — React Agent Prompt

You are building **ClarityBox UI**, a React frontend for a financial market analytics platform. The backend (Django REST API) is already built and running at `http://localhost:8002`. Your job is to build the complete React frontend from scratch.

---

## Tech Stack

- **Build tool:** Vite
- **Framework:** React 18 with TypeScript
- **Routing:** React Router v6
- **State management:** Redux Toolkit (createSlice + createAsyncThunk)
- **HTTP client:** Axios with request/response interceptors for JWT
- **Styling:** Tailwind CSS (dark theme — dark blues/grays, with green/red/gray accent colors for zones)
- **Charts:** Chart.js + react-chartjs-2 (with chartjs-plugin-zoom for pan/zoom, chartjs-adapter-date-fns for date axis)
- **Icons:** react-icons

---

## Project Setup

```bash
npm create vite@latest claritybox-ui -- --template react-ts
cd claritybox-ui
npm install react-router-dom @reduxjs/toolkit react-redux axios
npm install tailwindcss @tailwindcss/vite
npm install chart.js react-chartjs-2 chartjs-plugin-zoom chartjs-adapter-date-fns
npm install react-icons
```

Create `.env`:
```
VITE_API_BASE_URL=http://localhost:8002
```

---

## API Base URL & Auth

- **Base URL:** `import.meta.env.VITE_API_BASE_URL` (defaults to `http://localhost:8002`)
- **All API paths** are prefixed with `/api/claritybox/`
- **Auth:** JWT Bearer tokens
- **Token storage:** localStorage (`accessToken`, `refreshToken`)

### Axios Setup

Create an axios instance with interceptors:

**Request interceptor:**
- Attach `Authorization: Bearer <accessToken>` header from localStorage

**Response interceptor:**
- On 401 response: call `/api/claritybox/auth/refresh/` with the stored refresh token
- If refresh succeeds: update localStorage, retry the original request
- If refresh fails: clear localStorage, redirect to `/login`

---

## API Endpoints — Full Contract

### Auth (no token required)

#### POST `/api/claritybox/auth/signup/`
```json
// Request
{ "email": "user@example.com", "password": "SecurePass123", "first_name": "John", "last_name": "Doe" }

// Response 200
{ "message": "Registration successful", "accessToken": "eyJ...", "refreshToken": "eyJ..." }

// Response 400
{ "error": "Email is already in use" }
{ "error": "All fields are required" }
```

#### POST `/api/claritybox/auth/login/`
```json
// Request
{ "email": "user@example.com", "password": "SecurePass123" }

// Response 200
{ "accessToken": "eyJ...", "refreshToken": "eyJ..." }

// Response 400
{ "error": "Invalid email or password" }

// Response 403
{ "error": "Account is not active" }
```

#### POST `/api/claritybox/auth/refresh/`
```json
// Request
{ "refresh": "eyJ..." }

// Response 200
{ "accessToken": "eyJ...", "refreshToken": "eyJ..." }

// Response 400
{ "error": "Invalid or expired refresh token" }
```

### Auth (token required)

#### GET `/api/claritybox/auth/profile/`
```json
// Response 200
{ "email": "user@example.com", "first_name": "John", "last_name": "Doe" }
```

#### PUT `/api/claritybox/auth/profile/`
```json
// Request
{ "first_name": "John", "last_name": "Updated" }

// Response 200
{ "message": "Profile updated successfully", "first_name": "John", "last_name": "Updated" }
```

### Market Data (all require token)

#### GET `/api/claritybox/market-metadata/`
Returns all markets and their symbols. Use this to populate dropdowns in the simulator.
```json
// Response 200
[
  {
    "id": 1,
    "name": "india_stocks_indexes",
    "label": "Indian Stocks & Indexes",
    "symbols": [
      { "id": 1, "name": "NIFTY50", "label": "Nifty 50" },
      { "id": 2, "name": "SENSEX", "label": "Sensex" }
    ]
  },
  {
    "id": 4,
    "name": "crypto",
    "label": "Crypto",
    "symbols": [
      { "id": 19, "name": "BTC", "label": "Bitcoin" }
    ]
  }
]
```

#### GET `/api/claritybox/global-market-summary/`
Main dashboard data. Returns all indexes grouped by region > country > indexes with scores.
```json
// Response 200
{
  "regions": [
    {
      "code": "ASIA",
      "name": "Asia",
      "countries": [
        {
          "code": "IN",
          "name": "India",
          "indexes": [
            {
              "id": 1,
              "name": "NIFTY50",
              "label": "Nifty 50",
              "market": "india_stocks_indexes",
              "smart_index_st": 75,
              "status": "ready",
              "last_updated_at": "2026-02-07T10:30:00+00:00",
              "active_zone": "GREEN",
              "zone_since_date": "2026-01-15",
              "zone_entry_value": 72,
              "aes_leverage_moderate": "2X",
              "aes_leverage_aggressive": "3X"
            }
          ]
        }
      ]
    },
    {
      "code": "CRYPTO",
      "name": "Crypto",
      "countries": [
        {
          "code": "CRYPTO",
          "name": "Crypto",
          "indexes": [
            {
              "id": 19,
              "name": "BTC",
              "label": "Bitcoin",
              "market": "crypto",
              "smart_index_st": 55,
              "status": "ready",
              "last_updated_at": "2026-02-07T10:30:00+00:00",
              "active_zone": "GREY",
              "zone_since_date": "2026-02-01",
              "zone_entry_value": 50
            }
          ]
        }
      ]
    }
  ]
}
```

**Zone rules:**
- `GREEN` = score >= 71 (Bullish) — show in green, display leverage values
- `RED` = score <= 30 (Bearish) — show in red
- `GREY` = score 31-70 (Neutral) — show in gray

**`status` field:**
- `"ready"` — data is current
- `"processing"` — data is being polled (show spinner). When any index is processing, poll this endpoint every 10 seconds until all are ready.

**Leverage fields** (`aes_leverage_moderate`, `aes_leverage_aggressive`):
- Only present when `active_zone` is `GREEN`
- Values like `"2X"`, `"3X"` — display as leverage recommendation

#### GET `/api/claritybox/chart/{market_type}/{symbol_name}/`
Historical data for charting. Returns array sorted by date ascending.

**Valid `market_type` values:** `india_stocks_indexes`, `us_stocks_indexes`, `international_stocks_indexes`, `crypto`, `precious_metals`

**`symbol_name`:** Case-insensitive (e.g., `NIFTY50`, `BTC`, `SP500`, `GOLD`)

```json
// Example: GET /api/claritybox/chart/india_stocks_indexes/NIFTY50/
// Response 200
[
  {
    "date": "2025-01-01",
    "close_price": 25100.50,
    "open": 25000.00,
    "high": 25200.00,
    "low": 24800.00,
    "volume": 375500,
    "smart_index": 75,
    "aes_leverage_moderate": "2X",
    "aes_leverage_aggressive": "3X"
  },
  {
    "date": "2025-01-02",
    "close_price": 25250.00,
    "open": 25100.50,
    "high": 25300.00,
    "low": 25050.00,
    "volume": 400200,
    "smart_index": 60,
    "aes_leverage_moderate": null,
    "aes_leverage_aggressive": null
  }
]

// Response 400
{ "error": "Invalid market type" }

// Response 404
{ "error": "Symbol 'XYZ' not found" }
```

#### GET `/api/claritybox/momentum-alerts/`
Recent zone changes across all symbols, sorted by date descending.
```json
// Response 200
{
  "alerts": [
    {
      "symbol": "NIFTY50",
      "label": "Nifty 50",
      "market": "Indian Stocks & Indexes",
      "from_score": 68,
      "to_score": 73,
      "change_type": "BULLISH",
      "days_since_last_change": 5,
      "date": "2026-02-07"
    },
    {
      "symbol": "BTC",
      "label": "Bitcoin",
      "market": "Crypto",
      "from_score": 45,
      "to_score": 28,
      "change_type": "BEARISH",
      "days_since_last_change": 3,
      "date": "2026-02-05"
    }
  ]
}
```

**`change_type` values:**
- `"BULLISH"` — entered GREEN zone (score crossed above 71) — show green
- `"BEARISH"` — entered RED zone (score crossed below 30) — show red
- `"NEUTRAL"` — entered GREY zone — show gray

### Simulator Endpoints (all POST, token required)

#### POST `/api/claritybox/simulate/`
Single symbol buy-and-hold simulation.
```json
// Request
{
  "market_type": "india_stocks_indexes",
  "symbol_name": "NIFTY50",
  "amount": 100000,
  "start_date": "2020-01-01",
  "duration": 3
}

// Response 200
{
  "symbol": "NIFTY50",
  "start_date": "2020-01-01",
  "end_date": "2023-01-01",
  "initial_amount": 100000.0,
  "simple_returns": {
    "totalMoneyInvested": "100000.00",
    "totalMoneyReturned": "158432.50",
    "percentageChange": "58.43%"
  }
}

// Response 400
{ "error": "Missing required fields" }
{ "error": "Invalid market type" }
{ "error": "Not enough data for the selected period" }

// Response 404
{ "error": "Symbol 'XYZ' not found" }
```

**Fields:**
- `market_type` — one of the 5 valid market types
- `symbol_name` — case-insensitive symbol name
- `amount` — investment amount in local currency
- `start_date` — YYYY-MM-DD format
- `duration` — investment period in years (integer)

#### POST `/api/claritybox/simulate/portfolio/`
Multi-symbol portfolio simulation with allocation percentages.
```json
// Request
{
  "allocations": {
    "NIFTY50": 40,
    "SENSEX": 30,
    "SP500": 20,
    "GOLD": 10
  },
  "amount": 500000,
  "start_date": "2020-01-01",
  "duration": 3
}

// Response 200
{
  "simple_returns": {
    "totalMoneyInvested": "500000.00",
    "totalMoneyReturned": "725610.00",
    "percentageChange": "45.12%"
  }
}

// Response 400
{ "error": "Allocations must sum to 100%, got 60%" }
{ "error": "Unknown symbol: DOESNOTEXIST" }
```

**Rules:**
- `allocations` values must sum to 100 (within 1% tolerance)
- Each key is a symbol name (case-insensitive)

#### POST `/api/claritybox/simulate/portfolio/advanced/`
Advanced portfolio simulation with strategy mix. **This is a placeholder — returns a message indicating score_engine is required.**
```json
// Request
{
  "allocations": { "NIFTY50": 60, "SP500": 40 },
  "strategy_mix": { "conservative": 50, "moderate": 30, "aggressive": 20 },
  "amount": 100000,
  "start_date": "2020-01-01",
  "duration": 3
}

// Response 200
{
  "message": "Advanced portfolio simulation coming soon — requires score_engine",
  "config": { ... }
}
```

Build the UI form for this but show a "Coming Soon" badge. The form should still validate inputs.

---

## Pages & Routes

### Public Routes (no login required)

| Route | Page | Description |
|-------|------|-------------|
| `/login` | LoginPage | Email + password login form |
| `/signup` | SignupPage | Registration form (email, password, first name, last name) |

If user is already logged in (has valid accessToken), redirect `/login` and `/signup` to `/`.

### Protected Routes (login required)

| Route | Page | Description |
|-------|------|-------------|
| `/` | MarketOverviewPage | Global market summary dashboard (default home) |
| `/chart/:marketType/:symbolName` | ChartPage | Historical price + smart index chart |
| `/alerts` | MomentumAlertsPage | Zone change alerts across all symbols |
| `/simulator` | SimulatorPage | Single symbol investment simulator |
| `/simulator/portfolio` | PortfolioSimulatorPage | Multi-symbol portfolio simulator |
| `/simulator/advanced` | AdvancedSimulatorPage | Advanced portfolio with strategy mix (Coming Soon) |
| `/profile` | ProfilePage | View and edit user profile |

If user is not logged in, redirect all protected routes to `/login`.

---

## Page Descriptions

### LoginPage / SignupPage
- Clean forms with email + password fields
- SignupPage adds first_name + last_name fields
- On success: store tokens in localStorage, redirect to `/`
- Show API error messages (e.g., "Email is already in use")
- Link between login and signup pages

### MarketOverviewPage (Home — `/`)
This is the main dashboard. Call `GET /api/claritybox/global-market-summary/`.

**Layout:**
- Tab bar at top for each region (Asia, North America, Europe, Crypto, Precious Metals, etc.)
- Each region tab shows its countries
- Each country shows its index cards

**Index card displays:**
- Symbol label (e.g., "Nifty 50")
- Score value (smart_index_st) with color: green (>=71), red (<=30), gray (31-70)
- Zone label: "Bullish", "Bearish", or "Neutral"
- Zone since date + entry value (e.g., "Bullish since Jan 15 at 72")
- If GREEN zone: show leverage values (moderate & aggressive)
- Status: if "processing", show a spinner overlay
- Last updated timestamp
- Clicking a card navigates to `/chart/{market}/{symbolName}`

**Smart polling:**
- If any index has `status: "processing"`, re-fetch the summary every 10 seconds
- Stop polling when all indexes show `status: "ready"`

### ChartPage (`/chart/:marketType/:symbolName`)
Call `GET /api/claritybox/chart/{marketType}/{symbolName}/`.

**Layout:**
- Symbol name + label as page header
- Two-panel chart:
  - **Top panel (larger):** Close price line chart over time
  - **Bottom panel (smaller):** Smart Index score line chart over time, with horizontal lines at 30 and 71 marking zone boundaries
- Color the smart index line: green when >=71, red when <=30, gray in between
- Mark leverage points on the chart where `aes_leverage_moderate` or `aes_leverage_aggressive` is not null
- Enable zoom (scroll to zoom) and pan (drag to pan) using chartjs-plugin-zoom
- Show date range selector or zoom reset button

**Navigation:**
- Dropdown or sidebar to switch between symbols without going back to dashboard
- Use market-metadata endpoint to populate the symbol selector

### MomentumAlertsPage (`/alerts`)
Call `GET /api/claritybox/momentum-alerts/`.

**Layout:**
- List of alert cards, grouped by date
- Each alert card shows:
  - Symbol label + market name
  - Arrow indicator: up arrow (BULLISH, green), down arrow (BEARISH, red)
  - Score change: "68 → 73"
  - Change type badge: "Bullish" / "Bearish" / "Neutral"
  - Days since last change: "Changed 5 days ago"
  - Date of change

### SimulatorPage (`/simulator`)
Call `POST /api/claritybox/simulate/` on form submit.

**Form inputs:**
- Market dropdown (from market-metadata, grouped by market)
- Symbol dropdown (filtered by selected market)
- Investment amount (number input)
- Start date (date picker, YYYY-MM-DD)
- Duration in years (dropdown: 1, 2, 3, 5, 10)

**Results display:**
- Total invested vs. total returned
- Percentage change (color: green if positive, red if negative)
- Symbol name + period

### PortfolioSimulatorPage (`/simulator/portfolio`)
Call `POST /api/claritybox/simulate/portfolio/`.

**Form inputs:**
- Add symbols with allocation percentage (must sum to 100%)
- Each row: symbol dropdown + percentage input + remove button
- "Add Symbol" button to add more rows
- Total allocation indicator (shows sum, highlights red if != 100%)
- Investment amount
- Start date + duration

**Results display:**
- Same as single simulator but for the blended portfolio

### AdvancedSimulatorPage (`/simulator/advanced`)
Same as portfolio simulator plus strategy mix allocation.

**Additional inputs:**
- Strategy mix: Conservative, Moderate, Aggressive with percentage allocation (must sum to 100%)

**Note:** Show a "Coming Soon" badge. The form should validate but the API returns a placeholder response. Display the placeholder message from the API.

### ProfilePage (`/profile`)
Call `GET /api/claritybox/auth/profile/` on load, `PUT` on save.

**Form:**
- Email (read-only, displayed but not editable)
- First name (editable)
- Last name (editable)
- Save button
- Show success message on save

---

## Navigation

**Top navbar (shown on all protected pages):**
- Logo/brand: "ClarityBox" on the left
- Nav links: Market Overview, Alerts, Simulator, Profile
- Logout button on the right (clears tokens, redirects to `/login`)

**Simulator sub-nav:**
- Single Index | Portfolio | Advanced (as tabs or sub-links)

---

## Redux Store Structure

```typescript
interface RootState {
  auth: {
    accessToken: string | null;
    refreshToken: string | null;
    user: { email: string; first_name: string; last_name: string } | null;
    status: 'idle' | 'loading' | 'succeeded' | 'failed';
    error: string | null;
  };
  globalMarket: {
    data: GlobalMarketResponse | null;
    status: 'idle' | 'loading' | 'succeeded' | 'failed';
    error: string | null;
  };
  market: {
    markets: MarketMetadata[];
    status: 'idle' | 'loading' | 'succeeded' | 'failed';
    error: string | null;
  };
  chart: {
    data: ChartEntry[];
    status: 'idle' | 'loading' | 'succeeded' | 'failed';
    error: string | null;
  };
  momentumAlerts: {
    data: MomentumAlert[];
    status: 'idle' | 'loading' | 'succeeded' | 'failed';
    error: string | null;
  };
}
```

**Slices to create:**
1. `authSlice` — login, signup, refresh, profile, logout
2. `globalMarketSlice` — global market summary
3. `marketSlice` — market metadata (for dropdowns)
4. `chartSlice` — chart data for selected symbol
5. `momentumAlertsSlice` — momentum alerts

Each async thunk should use the axios instance (with interceptors) and handle `pending`, `fulfilled`, `rejected` states in `extraReducers`.

---

## Key TypeScript Interfaces

```typescript
interface Region {
  code: string;
  name: string;
  countries: Country[];
}

interface Country {
  code: string;
  name: string;
  indexes: MarketIndex[];
}

interface MarketIndex {
  id: number;
  name: string;
  label: string;
  market: string;
  smart_index_st: number | null;
  status: 'ready' | 'processing';
  last_updated_at: string | null;
  active_zone: 'GREEN' | 'RED' | 'GREY' | null;
  zone_since_date: string | null;
  zone_entry_value: number | null;
  aes_leverage_moderate?: string;
  aes_leverage_aggressive?: string;
}

interface ChartEntry {
  date: string;
  close_price: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  volume: number | null;
  smart_index: number | null;
  aes_leverage_moderate: string | null;
  aes_leverage_aggressive: string | null;
}

interface MomentumAlert {
  symbol: string;
  label: string;
  market: string;
  from_score: number;
  to_score: number;
  change_type: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  days_since_last_change: number;
  date: string;
}

interface MarketMetadata {
  id: number;
  name: string;
  label: string;
  symbols: { id: number; name: string; label: string }[];
}

interface SimulationResult {
  symbol?: string;
  start_date?: string;
  end_date?: string;
  initial_amount?: number;
  simple_returns: {
    totalMoneyInvested: string;
    totalMoneyReturned: string;
    percentageChange: string;
  };
}
```

---

## Design Guidelines

- **Theme:** Dark background (slate-900, gray-900), light text
- **Zone colors:** Green (#22c55e) for Bullish, Red (#ef4444) for Bearish, Gray (#6b7280) for Neutral
- **Cards:** Rounded corners, subtle border, slight shadow
- **Score display:** Large number with zone-colored background pill
- **Charts:** Dark chart background, green/red/gray line for smart index
- **Loading states:** Skeleton loaders or spinners while fetching
- **Error states:** Red banner with error message from API
- **Responsive:** Mobile-friendly, single column on small screens, multi-column grid on larger
- **Transitions:** Subtle fade/slide on page navigation

---

## What NOT to Build

- No Google OAuth (email/password only)
- No email validation flow
- No password reset flow
- No subscription/payment features
- No market events annotations on charts (not in API yet)
- No market report page (not in API yet)
- No landing page for non-logged-in users (just show login page)

---

## Available Symbols (23 total)

**India (9):** NIFTY50, SENSEX, NIFTYBANK, NIFTYIT, NIFTYMETAL, NIFTYPHARMA, NIFTYAUTO, NIFTYENERGY, NIFTYREALTY
**US (4):** SP500, NASDAQ, DOWJONES, RUSSELL2000
**International (5):** FTSE100, DAX, NIKKEI225, HANGSENG, SHANGHAI
**Crypto (3):** BTC, ETH, SOL
**Precious Metals (2):** GOLD, SILVER

---

## Folder Structure (Recommended)

```
src/
├── main.tsx
├── App.tsx
├── router.tsx                  # Route definitions
├── api/
│   ├── axiosInstance.ts        # Axios with interceptors
│   └── endpoints.ts            # API URL constants
├── store/
│   ├── store.ts                # Redux store config
│   └── slices/
│       ├── authSlice.ts
│       ├── globalMarketSlice.ts
│       ├── marketSlice.ts
│       ├── chartSlice.ts
│       └── momentumAlertsSlice.ts
├── types/
│   └── index.ts                # All TypeScript interfaces
├── pages/
│   ├── LoginPage.tsx
│   ├── SignupPage.tsx
│   ├── MarketOverviewPage.tsx
│   ├── ChartPage.tsx
│   ├── MomentumAlertsPage.tsx
│   ├── SimulatorPage.tsx
│   ├── PortfolioSimulatorPage.tsx
│   ├── AdvancedSimulatorPage.tsx
│   └── ProfilePage.tsx
├── components/
│   ├── Navbar.tsx
│   ├── ProtectedRoute.tsx
│   ├── IndexCard.tsx           # Market index card (used in dashboard)
│   ├── ZoneBadge.tsx           # GREEN/RED/GREY zone indicator
│   ├── ScoreDisplay.tsx        # Colored score number
│   ├── AlertCard.tsx           # Momentum alert card
│   ├── PriceChart.tsx          # Chart.js price chart
│   ├── SmartIndexChart.tsx     # Chart.js smart index chart
│   ├── SymbolSelector.tsx      # Market + symbol dropdown
│   └── SimulatorResults.tsx    # Simulation results display
└── hooks/
    └── useSmartPolling.ts      # Custom hook for polling when processing
```
