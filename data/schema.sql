CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    min_profit_percent REAL DEFAULT 1.0,
    selected_strategy TEXT DEFAULT 'all',
    notifications_enabled INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    opportunity_type TEXT NOT NULL,
    route TEXT NOT NULL,
    buy_price REAL,
    sell_price REAL,
    fees REAL,
    spread_percent REAL,
    liquidity REAL,
    metadata_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_opportunities_user_created
ON opportunities(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS scan_cache (
    cache_key TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    expires_at INTEGER NOT NULL
);
