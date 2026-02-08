-- ClarityBox Reference Data Seed
-- Run: mysql -u root claritybox < seed_reference_data.sql

-- REGIONS
INSERT INTO regions (id, code, name) VALUES
(1, 'ASIA', 'Asia Pacific'),
(2, 'US', 'United States'),
(3, 'EUROPE', 'Europe'),
(4, 'INDIA', 'India');

-- COUNTRIES
INSERT INTO countries (id, code, name, region_id) VALUES
(1, 'HK', 'Hong Kong', 1),
(2, 'JP', 'Japan', 1),
(3, 'US', 'United States', 2),
(4, 'IN', 'India', 4),
(5, 'DE', 'Germany', 3),
(6, 'GB', 'United Kingdom', 3),
(7, 'FR', 'France', 3);

-- MARKETS
INSERT INTO markets (id, name, description, label) VALUES
(1, 'crypto', NULL, 'Crypto'),
(4, 'india_stocks_indexes', NULL, 'India: Stock Indexes'),
(5, 'us_stocks_indexes', NULL, 'US: Stock Indexes'),
(6, 'precious_metals', NULL, 'Precious Metals'),
(7, 'international_stocks_indexes', NULL, 'International: Stock Indexes');

-- SYMBOLS
INSERT INTO symbols (id, name, label, market_id, country_id) VALUES
(1, 'BTC', 'Bitcoin', 1, NULL),
(2, 'ETH', 'Ethereum', 1, NULL),
(3, 'alts', 'Altcoins', 1, NULL),
(4, 'SENSEX', 'Sensex', 4, 4),
(5, 'NIFTY50', 'Nifty 50', 4, 4),
(6, 'NIFTYBANK', 'Nifty Bank', 4, 4),
(7, 'NIFTYIT', 'Nifty IT', 4, 4),
(8, 'NIFTYMIDCAP100', 'Nifty Midcap 100', 4, 4),
(9, 'NIFTYSMALLCAP100', 'Nifty Smallcap 100', 4, 4),
(10, 'NIFTYPHARMA', 'Nifty Pharma', 4, 4),
(11, 'NIFTYENERGY', 'Nifty Energy', 4, 4),
(12, 'NIFTYAUTO', 'Nifty Auto', 4, 4),
(13, 'IXIC', 'Nasdaq', 5, 3),
(14, 'SNP', 'S&P 500', 5, 3),
(15, 'DJI', 'Dow Jones', 5, 3),
(16, 'RUT', 'US Small Cap 2000', 5, 3),
(17, 'GOLD', 'Gold', 6, NULL),
(18, 'SILVER', 'Silver', 6, NULL),
(19, 'HSI', 'Hang Seng Index', 7, 1),
(20, 'N225', 'Nikkei 225', 7, 2),
(21, 'DAX', 'DAX 40', 7, 5),
(22, 'FTSE', 'FTSE 100 (UK)', 7, 6),
(23, 'CAC40', 'CAC 40 (France)', 7, 7);
