-- Seed 50 sample symbols across various asset types
INSERT INTO symbol (symbol, name, exchange, asset_type) VALUES
-- Stocks
('AAPL', 'Apple Inc.', 'NASDAQ', 'stock'),
('GOOGL', 'Alphabet Inc. Class A', 'NASDAQ', 'stock'),
('MSFT', 'Microsoft Corporation', 'NASDAQ', 'stock'),
('AMZN', 'Amazon.com Inc.', 'NASDAQ', 'stock'),
('TSLA', 'Tesla Inc.', 'NASDAQ', 'stock'),
('META', 'Meta Platforms Inc.', 'NASDAQ', 'stock'),
('NVDA', 'NVIDIA Corporation', 'NASDAQ', 'stock'),
('JPM', 'JPMorgan Chase & Co.', 'NYSE', 'stock'),
('V', 'Visa Inc.', 'NYSE', 'stock'),
('WMT', 'Walmart Inc.', 'NYSE', 'stock'),
('JNJ', 'Johnson & Johnson', 'NYSE', 'stock'),
('PG', 'Procter & Gamble Co.', 'NYSE', 'stock'),
('UNH', 'UnitedHealth Group Inc.', 'NYSE', 'stock'),
('HD', 'Home Depot Inc.', 'NYSE', 'stock'),
('DIS', 'Walt Disney Co.', 'NYSE', 'stock'),
-- ETFs
('SPY', 'SPDR S&P 500 ETF Trust', 'NYSE', 'etf'),
('QQQ', 'Invesco QQQ Trust', 'NASDAQ', 'etf'),
('VOO', 'Vanguard S&P 500 ETF', 'NYSE', 'etf'),
('VTI', 'Vanguard Total Stock Market ETF', 'NYSE', 'etf'),
('IWM', 'iShares Russell 2000 ETF', 'NYSE', 'etf'),
('GLD', 'SPDR Gold Shares', 'NYSE', 'etf'),
('EEM', 'iShares MSCI Emerging Markets ETF', 'NYSE', 'etf'),
-- Crypto
('BTC', 'Bitcoin', 'CRYPTO', 'crypto'),
('ETH', 'Ethereum', 'CRYPTO', 'crypto'),
('SOL', 'Solana', 'CRYPTO', 'crypto'),
('XRP', 'Ripple', 'CRYPTO', 'crypto'),
('ADA', 'Cardano', 'CRYPTO', 'crypto'),
('AVAX', 'Avalanche', 'CRYPTO', 'crypto'),
('DOGE', 'Dogecoin', 'CRYPTO', 'crypto'),
-- Forex
('EURUSD', 'Euro/US Dollar', 'FX', 'forex'),
('GBPUSD', 'British Pound/US Dollar', 'FX', 'forex'),
('USDJPY', 'US Dollar/Japanese Yen', 'FX', 'forex'),
('AUDUSD', 'Australian Dollar/US Dollar', 'FX', 'forex'),
('USDCAD', 'US Dollar/Canadian Dollar', 'FX', 'forex'),
-- Index
('SPX', 'S&P 500 Index', 'CBOE', 'index'),
('NDX', 'NASDAQ 100 Index', 'NASDAQ', 'index'),
('DJI', 'Dow Jones Industrial Average', 'NYSE', 'index'),
('VIX', 'CBOE Volatility Index', 'CBOE', 'index'),
-- Commodity
('GC', 'Gold Futures', 'COMEX', 'commodity'),
('CL', 'Crude Oil WTI Futures', 'NYMEX', 'commodity'),
('SI', 'Silver Futures', 'COMEX', 'commodity'),
('NG', 'Natural Gas Futures', 'NYMEX', 'commodity'),
-- Bonds
('TLT', 'iShares 20+ Year Treasury Bond ETF', 'NASDAQ', 'bond'),
('BND', 'Vanguard Total Bond Market ETF', 'NASDAQ', 'bond'),
('BNDX', 'Vanguard Total International Bond ETF', 'NASDAQ', 'bond'),
-- Mutual Fund
('VFIAX', 'Vanguard 500 Index Fund Admiral', 'MUTUAL', 'mutual_fund'),
('VTSAX', 'Vanguard Total Stock Market Index Admiral', 'MUTUAL', 'mutual_fund'),
('VBMFX', 'Vanguard Total Bond Market Index Fund', 'MUTUAL', 'mutual_fund'),
-- Other
('GME', 'GameStop Corp.', 'NYSE', 'other'),
('AMC', 'AMC Entertainment Holdings Inc.', 'NYSE', 'other')
ON CONFLICT (symbol) DO NOTHING;
