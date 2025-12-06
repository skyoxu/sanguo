-- Base schema migrated from vitegame (adapted)

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    created_at INTEGER NOT NULL,
    last_login INTEGER
);

CREATE TABLE IF NOT EXISTS saves (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    slot_number INTEGER NOT NULL,
    data TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, slot_number)
);

CREATE TABLE IF NOT EXISTS statistics (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    stat_key TEXT NOT NULL,
    stat_value REAL NOT NULL,
    recorded_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at INTEGER NOT NULL,
    description TEXT
);

-- Extensions in godotgame
CREATE TABLE IF NOT EXISTS achievements (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    achievement_key TEXT NOT NULL,
    unlocked_at INTEGER NOT NULL,
    progress REAL DEFAULT 0.0,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, achievement_key)
);

CREATE TABLE IF NOT EXISTS settings (
    user_id TEXT PRIMARY KEY,
    audio_volume REAL DEFAULT 1.0,
    graphics_quality TEXT DEFAULT 'medium',
    language TEXT DEFAULT 'en',
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Inventory items dedicated table (replaces transitional snapshot in saves:slot 90)
CREATE TABLE IF NOT EXISTS inventory_items (
    user_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    qty INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, item_id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
