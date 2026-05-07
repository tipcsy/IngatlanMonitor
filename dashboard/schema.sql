-- IngatlanMonitor SQLite séma
-- Ez a fájl referencia célokat szolgál, a tényleges inicializálást a db.py végzi

CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id TEXT UNIQUE,                    -- Gmail message ID (deduplikáció)
    email_date DATETIME,                     -- Email érkezési idő
    portal TEXT,                             -- idealista/kyero/thinkspain/fotocasa
    city TEXT,                               -- Város neve
    region TEXT,                             -- Costa del Sol / Costa Blanca / stb.
    airport TEXT,                            -- AGP/ALC/RMU/VLC/BIO
    airport_km INTEGER,                      -- Reptér távolság
    sea_km INTEGER,                          -- Tenger távolság
    latitude REAL,                           -- GPS koordináta
    longitude REAL,                          -- GPS koordináta
    price_eur INTEGER,                       -- Ár EUR-ban
    size_m2 INTEGER,                         -- Alapterület
    parking TEXT,                            -- igen/nem/ismeretlen
    garden TEXT,                             -- igen/nem/ismeretlen
    score INTEGER,                           -- Pontszám 1-10
    legal_status TEXT,                       -- ok/kizart/kerdeses
    reason TEXT,                             -- AI indoklás magyarul
    property_url TEXT,                       -- Ingatlan link
    gmail_url TEXT,                          -- Gmail link
    maps_url TEXT,                           -- Google Maps link
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_archived INTEGER DEFAULT 0,           -- Archivált (soft delete)
    is_favorite INTEGER DEFAULT 0,           -- Kedvenc jelölés
    garden_m2 INTEGER,                       -- Kert mérete m²-ben (utólag szerkeszthető)
    user_notes TEXT                          -- Szabad megjegyzés (felhasználó által írható)
);

-- Indexek a gyors szűréshez
CREATE INDEX IF NOT EXISTS idx_score ON properties(score);
CREATE INDEX IF NOT EXISTS idx_airport ON properties(airport);
CREATE INDEX IF NOT EXISTS idx_city ON properties(city);
CREATE INDEX IF NOT EXISTS idx_is_archived ON properties(is_archived);
CREATE INDEX IF NOT EXISTS idx_email_date ON properties(email_date);
CREATE INDEX IF NOT EXISTS idx_region ON properties(region);
CREATE INDEX IF NOT EXISTS idx_price_eur ON properties(price_eur);
