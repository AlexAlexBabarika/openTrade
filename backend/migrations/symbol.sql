CREATE TABLE symbol (
    symbol VARCHAR(8) NOT NULL PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    asset_type asset_type NOT NULL
);