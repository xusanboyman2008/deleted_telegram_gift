import os
import json
import time
import logging
import asyncio
import aiosqlite
import asyncpg
try:
    from config import DB_PATH, DEFAULT_COMMISSION
except ImportError:
    from backend.config import DB_PATH, DEFAULT_COMMISSION

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")
IS_POSTGRES = DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")

GIFTS_SEED = [
    ("🥷", "Terrorist Bear","08/13/26", "6046178578163303744", 50, DEFAULT_COMMISSION, "terrorist.lottie"),
    ("🧸", "Bunny Basket",  "03/08/26", "5866352046986232958", 50, DEFAULT_COMMISSION, "bunny_bear.lottie"),
    ("🧸", "Balloon Bear",  "03/17/26", "5893356958802511476", 50, DEFAULT_COMMISSION, "joker_bear.lottie"),
    ("🧸", "Rose Bear",     "02/14/26", "5801108895304779062", 50, DEFAULT_COMMISSION, "pink_bear.lottie"),
    ("🧸", "Worker Bear",   "04/01/26", "5935895822435615975", 50, DEFAULT_COMMISSION, "worker_bear.lottie"),
    ("🧸", "Football Bear", "05/01/26", "6026193266406327981", 50, DEFAULT_COMMISSION, "football_bear.lottie"),
    ("🧸", "Santa Teddy",   "12/25/25", "5922558454332916696", 50, DEFAULT_COMMISSION, "santa_bear.lottie"),
    ("🧸", "Gnome Bear",    "07/20/26", "5974210632977745012", 50, DEFAULT_COMMISSION, "gnome_bear.lottie"),
    ("💖", "I Love U",      "02/14/26", "5800655655995968839", 50, DEFAULT_COMMISSION, "hear.lottie"),
    ("🎄", "Christmas Tree","12/31/25", "5956217000635139069", 50, DEFAULT_COMMISSION, "green_tree.lottie"),
    ("🧸", "Hug Bear",      "05/10/26", "5800655655995968830", 50, DEFAULT_COMMISSION, "hug_bear.lottie"),
]


CREATE_GIFTS_SQLITE = """
CREATE TABLE IF NOT EXISTS gifts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    emoji       TEXT NOT NULL,
    display_name TEXT,
    date_label  TEXT NOT NULL,
    gift_tg_id  TEXT NOT NULL UNIQUE,
    base_stars  INTEGER NOT NULL DEFAULT 50,
    commission  INTEGER NOT NULL DEFAULT 10,
    active      INTEGER NOT NULL DEFAULT 1,
    animation   TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
)
"""

CREATE_ORDERS_SQLITE = """
CREATE TABLE IF NOT EXISTS orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_tg_id     INTEGER NOT NULL,
    buyer_username  TEXT,
    recipient_id    TEXT,
    recipient_type  TEXT DEFAULT 'username',
    gift_id         INTEGER NOT NULL,
    total_stars     INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    payment_charge  TEXT,
    gift_text       TEXT,
    sender_type     TEXT DEFAULT 'bot',
    userbot_id      INTEGER,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
)
"""

CREATE_GIFTS_POSTGRES = """
CREATE TABLE IF NOT EXISTS gifts (
    id          SERIAL PRIMARY KEY,
    emoji       TEXT NOT NULL,
    display_name TEXT,
    date_label  TEXT NOT NULL,
    gift_tg_id  TEXT NOT NULL UNIQUE,
    base_stars  INTEGER NOT NULL DEFAULT 50,
    commission  INTEGER NOT NULL DEFAULT 10,
    active      INTEGER NOT NULL DEFAULT 1,
    animation   TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_ORDERS_POSTGRES = """
CREATE TABLE IF NOT EXISTS orders (
    id              SERIAL PRIMARY KEY,
    buyer_tg_id     BIGINT NOT NULL,
    buyer_username  TEXT,
    recipient_id    TEXT,
    recipient_type  TEXT DEFAULT 'username',
    gift_id         INTEGER NOT NULL,
    total_stars     INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    payment_charge  TEXT,
    gift_text       TEXT,
    sender_type     TEXT DEFAULT 'bot',
    userbot_id      INTEGER,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_USERBOTS_SQLITE = """
CREATE TABLE IF NOT EXISTS userbot_accounts (
    id              INTEGER PRIMARY KEY,
    session         TEXT,
    phone           TEXT,
    session_string  TEXT,
    api_id          INTEGER,
    api_hash        TEXT,
    first_name      TEXT,
    last_name       TEXT,
    username        TEXT,
    bio             TEXT,
    photo           TEXT,
    active          INTEGER DEFAULT 1,
    owner_tg_id     INTEGER,
    stars_balance   INTEGER DEFAULT 0
)
"""

CREATE_USERBOTS_POSTGRES = """
CREATE TABLE IF NOT EXISTS userbot_accounts (
    id              INTEGER PRIMARY KEY,
    session         TEXT,
    phone           TEXT,
    session_string  TEXT,
    api_id          INTEGER,
    api_hash        TEXT,
    first_name      TEXT,
    last_name       TEXT,
    username        TEXT,
    bio             TEXT,
    photo           TEXT,
    active          INTEGER DEFAULT 1,
    owner_tg_id     BIGINT,
    stars_balance   INTEGER DEFAULT 0
)
"""

CREATE_SETTINGS_SQLITE = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
"""

CREATE_SETTINGS_POSTGRES = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
"""

CREATE_MANAGED_BOTS_SQLITE = """
CREATE TABLE IF NOT EXISTS managed_bots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    token           TEXT NOT NULL UNIQUE,
    bot_username    TEXT,
    bot_name        TEXT,
    bot_id          INTEGER,
    active          INTEGER DEFAULT 1,
    commands_json   TEXT DEFAULT '[]',
    scripts_json    TEXT DEFAULT '{}',
    created_at      TEXT DEFAULT (datetime('now'))
)
"""

CREATE_BOT_USER_MESSAGES_SQLITE = """
CREATE TABLE IF NOT EXISTS bot_user_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_token       TEXT NOT NULL,
    user_id         INTEGER NOT NULL,
    user_username   TEXT,
    user_first_name TEXT,
    message_id      INTEGER,
    text            TEXT,
    out             INTEGER DEFAULT 0,
    date            TEXT,
    media_type      TEXT,
    media_data      TEXT,
    file_name       TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
)
"""

CREATE_MANAGED_BOTS_POSTGRES = """
CREATE TABLE IF NOT EXISTS managed_bots (
    id              SERIAL PRIMARY KEY,
    token           TEXT NOT NULL UNIQUE,
    bot_username    TEXT,
    bot_name        TEXT,
    bot_id          BIGINT,
    active          INTEGER DEFAULT 1,
    commands_json   TEXT DEFAULT '[]',
    scripts_json    TEXT DEFAULT '{}',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_BOT_USER_MESSAGES_POSTGRES = """
CREATE TABLE IF NOT EXISTS bot_user_messages (
    id              SERIAL PRIMARY KEY,
    bot_token       TEXT NOT NULL,
    user_id         BIGINT NOT NULL,
    user_username   TEXT,
    user_first_name TEXT,
    message_id      INTEGER,
    text            TEXT,
    out             INTEGER DEFAULT 0,
    date            TEXT,
    media_type      TEXT,
    media_data      TEXT,
    file_name       TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_BOT_USERS_SQLITE = """
CREATE TABLE IF NOT EXISTS bot_users (
    bot_token       TEXT NOT NULL,
    user_id         INTEGER NOT NULL,
    username        TEXT,
    first_name      TEXT,
    photo           TEXT,
    info            TEXT,
    PRIMARY KEY (bot_token, user_id)
)
"""

CREATE_BOT_USERS_POSTGRES = """
CREATE TABLE IF NOT EXISTS bot_users (
    bot_token       TEXT NOT NULL,
    user_id         BIGINT NOT NULL,
    username        TEXT,
    first_name      TEXT,
    photo           TEXT,
    info            TEXT,
    PRIMARY KEY (bot_token, user_id)
)
"""

pool = None


async def init_db():
    global pool, IS_POSTGRES, DATABASE_URL
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    IS_POSTGRES = DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")

    if IS_POSTGRES:
        pg_url = DATABASE_URL.replace("postgres://", "postgresql://")
        try:
            pool = await asyncio.wait_for(asyncpg.create_pool(pg_url, min_size=2, max_size=10, command_timeout=5.0), timeout=8.0)
            async with pool.acquire() as conn:
                combined_schema_sql = f"""
                {CREATE_GIFTS_POSTGRES};
                {CREATE_ORDERS_POSTGRES};
                {CREATE_USERBOTS_POSTGRES};
                {CREATE_SETTINGS_POSTGRES};
                {CREATE_MANAGED_BOTS_POSTGRES};
                {CREATE_BOT_USER_MESSAGES_POSTGRES};
                {CREATE_BOT_USERS_POSTGRES};
                ALTER TABLE bot_user_messages ADD COLUMN IF NOT EXISTS media_type TEXT;
                ALTER TABLE bot_user_messages ADD COLUMN IF NOT EXISTS media_data TEXT;
                ALTER TABLE bot_user_messages ADD COLUMN IF NOT EXISTS file_name TEXT;
                ALTER TABLE orders ADD COLUMN IF NOT EXISTS gift_text TEXT;
                ALTER TABLE orders ADD COLUMN IF NOT EXISTS sender_type TEXT DEFAULT 'bot';
                ALTER TABLE orders ADD COLUMN IF NOT EXISTS userbot_id INTEGER;
                ALTER TABLE userbot_accounts ADD COLUMN IF NOT EXISTS owner_tg_id BIGINT;
                ALTER TABLE userbot_accounts ADD COLUMN IF NOT EXISTS stars_balance INTEGER DEFAULT 0;
                UPDATE gifts SET animation='worker_bear.lottie' WHERE display_name='Worker Bear' OR animation='plumber_bear.json' OR animation='worker_bear.json';
                UPDATE gifts SET display_name='Hug Bear', emoji='🧸', animation='hug_bear.lottie' WHERE gift_tg_id='5800655655995968830';
                UPDATE gifts SET animation = REPLACE(animation, '.json', '.lottie') WHERE animation LIKE '%.json';
                DELETE FROM gifts WHERE id IN (SELECT id FROM (SELECT id, ROW_NUMBER() OVER(PARTITION BY gift_tg_id ORDER BY id) as row_num FROM gifts) t WHERE t.row_num > 1);
                """
                await conn.execute(combined_schema_sql)

                # Seed userbot accounts from account.json if table is empty
                try:
                    cnt = await conn.fetchval("SELECT COUNT(*) FROM userbot_accounts")
                    if cnt == 0:
                        acc_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "userbot", "account.json")
                        if os.path.exists(acc_path):
                            with open(acc_path, "r", encoding="utf-8") as f:
                                acc_data = json.load(f).get("accounts", [])
                                if acc_data:
                                    records = [
                                        (
                                            a.get("id"), a.get("session",""), a.get("phone",""), a.get("session_string",""),
                                            int(a.get("api_id") or 0), str(a.get("api_hash") or ""), a.get("first_name",""), a.get("last_name",""),
                                            a.get("username",""), a.get("bio",""), a.get("photo",""), 1 if a.get("active", True) else 0,
                                            a.get("owner_tg_id")
                                        )
                                        for a in acc_data
                                    ]
                                    await conn.executemany(
                                        """INSERT INTO userbot_accounts (id, session, phone, session_string, api_id, api_hash, first_name, last_name, username, bio, photo, active, owner_tg_id)
                                           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                                           ON CONFLICT (id) DO NOTHING""",
                                        records
                                    )
                except Exception as e:
                    logger.warning(f"Failed to seed userbots to PG: {e}")

                gift_seed_params = [(g[0], g[1], g[2], g[3], g[4], g[5], g[6]) for g in GIFTS_SEED]
                await conn.executemany(
                    """INSERT INTO gifts (emoji, display_name, date_label, gift_tg_id, base_stars, commission, animation)
                       VALUES ($1, $2, $3, $4, $5, $6, $7)
                       ON CONFLICT (gift_tg_id) DO NOTHING""",
                    gift_seed_params
                )
            print(f"[DB] PostgreSQL database initialized with {len(GIFTS_SEED)} gifts.")
        except Exception as pg_err:
            logger.warning(f"PostgreSQL connection failed ({pg_err}), falling back to SQLite.")
            IS_POSTGRES = False
            pool = None
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(CREATE_GIFTS_SQLITE)
                await db.execute(CREATE_ORDERS_SQLITE)
                await db.execute(CREATE_USERBOTS_SQLITE)
                await db.execute(CREATE_SETTINGS_SQLITE)
                await db.execute(CREATE_MANAGED_BOTS_SQLITE)
                await db.execute(CREATE_BOT_USER_MESSAGES_SQLITE)
                await db.execute(CREATE_BOT_USERS_SQLITE)
                try: await db.execute("ALTER TABLE bot_user_messages ADD COLUMN media_type TEXT")
                except Exception: pass
                try: await db.execute("ALTER TABLE bot_user_messages ADD COLUMN media_data TEXT")
                except Exception: pass
                try: await db.execute("ALTER TABLE bot_user_messages ADD COLUMN file_name TEXT")
                except Exception: pass
                try: await db.execute("ALTER TABLE orders ADD COLUMN gift_text TEXT")
                except Exception: pass
                try: await db.execute("ALTER TABLE orders ADD COLUMN sender_type TEXT DEFAULT 'bot'")
                except Exception: pass
                try: await db.execute("ALTER TABLE orders ADD COLUMN userbot_id INTEGER")
                except Exception: pass
                try: await db.execute("ALTER TABLE userbot_accounts ADD COLUMN owner_tg_id INTEGER")
                except Exception: pass
                try: await db.execute("ALTER TABLE userbot_accounts ADD COLUMN stars_balance INTEGER DEFAULT 0")
                except Exception: pass
                
                try:
                    await db.execute("UPDATE gifts SET animation='worker_bear.lottie' WHERE display_name='Worker Bear' OR animation='plumber_bear.json' OR animation='worker_bear.json'")
                    await db.execute("UPDATE gifts SET display_name='Hug Bear', emoji='🧸', animation='hug_bear.lottie' WHERE gift_tg_id='5800655655995968830'")
                    await db.execute("UPDATE gifts SET animation = REPLACE(animation, '.json', '.lottie') WHERE animation LIKE '%.json'")
                    await db.execute("DELETE FROM gifts WHERE id NOT IN (SELECT MIN(id) FROM gifts GROUP BY gift_tg_id)")
                    await db.commit()
                except Exception: pass

                await db.executemany(
                    "INSERT OR IGNORE INTO gifts (emoji, display_name, date_label, gift_tg_id, base_stars, commission, animation) VALUES (?,?,?,?,?,?,?)",
                    GIFTS_SEED,
                )
                await db.commit()
                print(f"[DB] SQLite fallback database initialized with {len(GIFTS_SEED)} gifts.")
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")
            await db.execute("PRAGMA temp_store=MEMORY")
            await db.execute("PRAGMA cache_size=-64000")
            await db.execute("PRAGMA mmap_size=268435456")
            await db.execute(CREATE_GIFTS_SQLITE)
            await db.execute(CREATE_ORDERS_SQLITE)
            await db.execute(CREATE_USERBOTS_SQLITE)
            await db.execute(CREATE_SETTINGS_SQLITE)
            await db.execute(CREATE_MANAGED_BOTS_SQLITE)
            await db.execute(CREATE_BOT_USER_MESSAGES_SQLITE)
            await db.execute(CREATE_BOT_USERS_SQLITE)
            try: await db.execute("ALTER TABLE bot_user_messages ADD COLUMN media_type TEXT")
            except Exception: pass
            try: await db.execute("ALTER TABLE bot_user_messages ADD COLUMN media_data TEXT")
            except Exception: pass
            try: await db.execute("ALTER TABLE bot_user_messages ADD COLUMN file_name TEXT")
            except Exception: pass
            try: await db.execute("ALTER TABLE orders ADD COLUMN gift_text TEXT")
            except Exception: pass
            try: await db.execute("ALTER TABLE orders ADD COLUMN sender_type TEXT DEFAULT 'bot'")
            except Exception: pass
            try: await db.execute("ALTER TABLE orders ADD COLUMN userbot_id INTEGER")
            except Exception: pass
            try: await db.execute("ALTER TABLE userbot_accounts ADD COLUMN owner_tg_id INTEGER")
            except Exception: pass
            try: await db.execute("ALTER TABLE userbot_accounts ADD COLUMN stars_balance INTEGER DEFAULT 0")
            except Exception: pass
            
            # Legacy cleanup: fix Worker Bear animation, Hug Bear gift_tg_id mapping, update json to lottie, and remove duplicate rows
            try:
                await db.execute("UPDATE gifts SET animation='worker_bear.lottie' WHERE display_name='Worker Bear' OR animation='plumber_bear.json' OR animation='worker_bear.json'")
                await db.execute("UPDATE gifts SET display_name='Hug Bear', emoji='🧸', animation='hug_bear.lottie' WHERE gift_tg_id='5800655655995968830'")
                await db.execute("UPDATE gifts SET animation = REPLACE(animation, '.json', '.lottie') WHERE animation LIKE '%.json'")
                await db.execute("DELETE FROM gifts WHERE id NOT IN (SELECT MIN(id) FROM gifts GROUP BY gift_tg_id)")
                await db.commit()
            except Exception: pass

            await db.executemany(
                "INSERT OR IGNORE INTO gifts (emoji, display_name, date_label, gift_tg_id, base_stars, commission, animation) VALUES (?,?,?,?,?,?,?)",
                GIFTS_SEED,
            )
            await db.commit()
            print(f"[DB] SQLite database initialized with {len(GIFTS_SEED)} gifts.")

    bot_tok = os.getenv("BOT_TOKEN", "")
    if bot_tok:
        try:
            await set_setting("bot_token", bot_tok)
        except Exception as e:
            logger.warning(f"Could not save bot_token to settings table: {e}")


# ── Gift CRUD ──────────────────────────────────────────────────────────────

_CACHE_GIFTS = {"data": None, "ts": 0}

def invalidate_gifts_cache():
    _CACHE_GIFTS["data"] = None

async def get_all_gifts(active_only: bool = True):
    now = time.time()
    if _CACHE_GIFTS["data"] is not None and (now - _CACHE_GIFTS["ts"]) < 5.0:
        cached = _CACHE_GIFTS["data"]
        if active_only:
            return [g for g in cached if g.get("active") == 1 or g.get("active") is True]
        return cached

    rows_data = None
    if IS_POSTGRES and pool:
        try:
            async with pool.acquire() as conn:
                q = "SELECT * FROM gifts ORDER BY id"
                rows = await conn.fetch(q)
                if rows:
                    rows_data = [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"PostgreSQL get_all_gifts error: {e}")

    if rows_data is None:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                q = "SELECT * FROM gifts ORDER BY id"
                cur = await db.execute(q)
                rows = await cur.fetchall()
                if rows:
                    rows_data = [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"SQLite get_all_gifts error: {e}")

    if rows_data is None:
        rows_data = [
            {"id": i+1, "emoji": g[0], "display_name": g[1], "date_label": g[2], "gift_tg_id": g[3], "base_stars": g[4], "commission": g[5], "active": 1, "animation": g[6]}
            for i, g in enumerate(GIFTS_SEED)
        ]

    _CACHE_GIFTS["data"] = rows_data
    _CACHE_GIFTS["ts"] = now

    if active_only:
        return [g for g in rows_data if g.get("active") == 1 or g.get("active") is True]
    return rows_data


async def get_gift(gift_id: int):
    if IS_POSTGRES and pool:
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM gifts WHERE id=$1", gift_id)
                if row:
                    return dict(row)
        except Exception as e:
            logger.error(f"PostgreSQL get_gift error: {e}")

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM gifts WHERE id=?", (gift_id,))
            row = await cur.fetchone()
            if row:
                return dict(row)
    except Exception as e:
        logger.error(f"SQLite get_gift error: {e}")

    for i, g in enumerate(GIFTS_SEED):
        if (i + 1) == gift_id:
            return {"id": i+1, "emoji": g[0], "display_name": g[1], "date_label": g[2], "gift_tg_id": g[3], "base_stars": g[4], "commission": g[5], "active": 1, "animation": g[6]}
    return None


async def add_gift(emoji, date_label, gift_tg_id, base_stars, commission, animation=None):
    if IS_POSTGRES:
        async with pool.acquire() as conn:
            new_id = await conn.fetchval(
                """INSERT INTO gifts (emoji, date_label, gift_tg_id, base_stars, commission, animation)
                   VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
                emoji, date_label, str(gift_tg_id), base_stars, commission, animation
            )
            return new_id
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "INSERT INTO gifts (emoji, date_label, gift_tg_id, base_stars, commission, animation) VALUES (?,?,?,?,?,?)",
                (emoji, date_label, str(gift_tg_id), base_stars, commission, animation),
            )
            await db.commit()
            return cur.lastrowid


async def update_gift(gift_id: int, **fields):
    allowed = {"emoji", "date_label", "gift_tg_id", "base_stars", "commission", "active", "animation", "display_name"}
    valid_fields = {k: v for k, v in fields.items() if k in allowed}
    if not valid_fields:
        return

    if IS_POSTGRES:
        sets = ", ".join(f"{k}=${i+1}" for i, k in enumerate(valid_fields.keys()))
        vals = list(valid_fields.values())
        vals.append(gift_id)
        async with pool.acquire() as conn:
            await conn.execute(f"UPDATE gifts SET {sets} WHERE id=${len(vals)}", *vals)
    else:
        sets = ", ".join(f"{k}=?" for k in valid_fields.keys())
        vals = list(valid_fields.values())
        vals.append(gift_id)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(f"UPDATE gifts SET {sets} WHERE id=?", vals)
            await db.commit()


async def delete_gift(gift_id: int):
    """Soft-delete gift by setting active=0 so admin can keep track of deleted gifts."""
    await update_gift(gift_id, active=0)


async def hard_delete_gift(gift_id: int):
    """Permanently delete gift from database."""
    if IS_POSTGRES:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM gifts WHERE id=$1", gift_id)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM gifts WHERE id=?", (gift_id,))
            await db.commit()


# ── Order CRUD ─────────────────────────────────────────────────────────────

async def create_order(buyer_tg_id, buyer_username, recipient_id, recipient_type, gift_id, total_stars, gift_text: str = None, sender_type: str = "bot", userbot_id: int = None):
    if IS_POSTGRES:
        async with pool.acquire() as conn:
            new_id = await conn.fetchval(
                """INSERT INTO orders
                   (buyer_tg_id, buyer_username, recipient_id, recipient_type, gift_id, total_stars, gift_text, sender_type, userbot_id)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING id""",
                int(buyer_tg_id), buyer_username, recipient_id, recipient_type, int(gift_id), int(total_stars), gift_text, sender_type, userbot_id
            )
            return new_id
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                """INSERT INTO orders
                   (buyer_tg_id, buyer_username, recipient_id, recipient_type, gift_id, total_stars, gift_text, sender_type, userbot_id)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (buyer_tg_id, buyer_username, recipient_id, recipient_type, gift_id, total_stars, gift_text, sender_type, userbot_id),
            )
            await db.commit()
            return cur.lastrowid


async def get_order(order_id: int):
    if IS_POSTGRES:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM orders WHERE id=$1", order_id)
            return dict(row) if row else None
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM orders WHERE id=?", (order_id,))
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_order_status(order_id: int, status: str, charge_id: str = None) -> bool:
    if IS_POSTGRES:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT status FROM orders WHERE id=$1", order_id)
            if not row or row["status"] == "paid":
                return False

            await conn.execute(
                "UPDATE orders SET status=$1, payment_charge=$2, updated_at=CURRENT_TIMESTAMP WHERE id=$3",
                status, charge_id, order_id,
            )
            return True
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT status FROM orders WHERE id=?", (order_id,))
            row = await cur.fetchone()
            if not row or row[0] == "paid":
                return False

            await db.execute(
                "UPDATE orders SET status=?, payment_charge=?, updated_at=datetime('now') WHERE id=?",
                (status, charge_id, order_id),
            )
            await db.commit()
            return True


async def get_all_orders():
    if IS_POSTGRES:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT o.*, g.emoji, g.date_label, g.display_name FROM orders o
                   LEFT JOIN gifts g ON g.id=o.gift_id
                   ORDER BY o.id DESC"""
            )
            return [dict(r) for r in rows]
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                """SELECT o.*, g.emoji, g.date_label, g.display_name FROM orders o
                   LEFT JOIN gifts g ON g.id=o.gift_id
                   ORDER BY o.id DESC"""
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_all_users() -> list:
    """Returns a list of distinct users who have interacted/ordered, with their order counts."""
    query = """
        SELECT buyer_tg_id, MAX(buyer_username) as buyer_username, COUNT(*) as orders_count
        FROM orders
        GROUP BY buyer_tg_id
        ORDER BY orders_count DESC
    """
    if IS_POSTGRES:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [dict(r) for r in rows]
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(query)
            rows = await cur.fetchall()
            return [dict(r) for r in rows]



async def get_orders_by_user(buyer_tg_id: int, limit: int = 15, offset: int = 0):
    if IS_POSTGRES:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT o.*, g.emoji, g.date_label, g.display_name, g.animation FROM orders o
                   LEFT JOIN gifts g ON g.id=o.gift_id
                   WHERE o.buyer_tg_id=$1
                   ORDER BY o.id DESC
                   LIMIT $2 OFFSET $3""",
                int(buyer_tg_id), int(limit), int(offset)
            )
            return [dict(r) for r in rows]
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                """SELECT o.*, g.emoji, g.date_label, g.display_name, g.animation FROM orders o
                   LEFT JOIN gifts g ON g.id=o.gift_id
                   WHERE o.buyer_tg_id=?
                   ORDER BY o.id DESC
                   LIMIT ? OFFSET ?""",
                (buyer_tg_id, limit, offset)
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


import sqlite3

import hashlib

def hash_userbot_id(raw_id) -> str:
    """Generates an obfuscated 12-char hash for public API exposure."""
    try:
        val = int(raw_id)
        return hashlib.sha256(f"ub_secret_salt_2026_{val}".encode()).hexdigest()[:12]
    except (ValueError, TypeError):
        return str(raw_id)

_CACHE_USERBOT_ACCS = {"data": None, "ts": 0}

def invalidate_userbot_accs_cache():
    _CACHE_USERBOT_ACCS["data"] = None

async def async_get_userbot_accounts(active_only: bool = True, user_tg_id: int = None, is_admin: bool = False) -> list:
    """Async database fetch for userbot accounts from PostgreSQL or SQLite."""
    now = time.time()
    accounts = []
    if _CACHE_USERBOT_ACCS["data"] is not None and (now - _CACHE_USERBOT_ACCS["ts"]) < 3.0:
        accounts = [dict(a) for a in _CACHE_USERBOT_ACCS["data"]]
    else:
        if IS_POSTGRES and pool:
            try:
                async with pool.acquire() as conn:
                    res = await conn.fetch("SELECT * FROM userbot_accounts ORDER BY id ASC")
                    accounts = [dict(r) for r in res]
            except Exception as e:
                logger.error(f"PostgreSQL async_get_userbot_accounts error: {e}")

        if not accounts:
            try:
                async with aiosqlite.connect(DB_PATH) as db:
                    db.row_factory = aiosqlite.Row
                    cur = await db.execute("SELECT * FROM userbot_accounts ORDER BY id ASC")
                    res = await cur.fetchall()
                    accounts = [dict(r) for r in res]
            except Exception as e:
                logger.error(f"SQLite async_get_userbot_accounts error: {e}")

        if not accounts:
            accounts = db_get_userbot_accounts()

        if accounts:
            _CACHE_USERBOT_ACCS["data"] = [dict(a) for a in accounts]
            _CACHE_USERBOT_ACCS["ts"] = now

    for acc in accounts:
        acc["active"] = bool(acc.get("active", 1))

    if is_admin:
        return accounts

    if active_only:
        accounts = [acc for acc in accounts if acc.get("active", True)]

    if user_tg_id:
        return [acc for acc in accounts if not acc.get("owner_tg_id") or acc.get("owner_tg_id") == user_tg_id]

    return [acc for acc in accounts if not acc.get("owner_tg_id")]

async def get_userbot_by_id_or_hash(identifier) -> dict:
    """Finds a userbot account by integer ID, obfuscated hashed ID, or owner_tg_id."""
    accounts = await async_get_userbot_accounts(active_only=False, is_admin=True)
    str_id = str(identifier)
    for acc in accounts:
        if str(acc.get("id")) == str_id or hash_userbot_id(acc.get("id")) == str_id:
            return acc
    for acc in accounts:
        if acc.get("owner_tg_id") and str(acc.get("owner_tg_id")) == str_id:
            return acc
    return accounts[0] if accounts else None

def db_get_userbot_accounts() -> list:
    """Synchronous read of userbots directly from PostgreSQL or SQLite database."""
    if IS_POSTGRES and DATABASE_URL:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            pg_url = DATABASE_URL.replace("postgres://", "postgresql://")
            conn = psycopg2.connect(pg_url)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM userbot_accounts ORDER BY id ASC")
            rows = cur.fetchall()
            conn.close()
            accounts = []
            for r in rows:
                acc = dict(r)
                acc["active"] = bool(acc.get("active", 1))
                accounts.append(acc)
            if accounts:
                return accounts
        except Exception as e:
            logger.error(f"PostgreSQL db_get_userbot_accounts failed: {e}")

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM userbot_accounts ORDER BY id ASC")
        rows = cur.fetchall()
        accounts = []
        for r in rows:
            acc = dict(r)
            acc["active"] = bool(acc.get("active", 1))
            accounts.append(acc)
        conn.close()
        return accounts
    except Exception as e:
        logger.error(f"db_get_userbot_accounts failed: {e}")
        return []


def db_save_userbot_accounts(accounts: list) -> bool:
    """Synchronous fallback to save userbots directly into PostgreSQL or SQLite database."""
    if IS_POSTGRES and DATABASE_URL:
        try:
            import psycopg2
            pg_url = DATABASE_URL.replace("postgres://", "postgresql://")
            conn = psycopg2.connect(pg_url)
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS userbot_accounts (id INTEGER PRIMARY KEY, session TEXT, phone TEXT, session_string TEXT, api_id INTEGER, api_hash TEXT, first_name TEXT, last_name TEXT, username TEXT, bio TEXT, photo TEXT, active INTEGER DEFAULT 1, owner_tg_id BIGINT, stars_balance INTEGER DEFAULT 0)")
            try: cur.execute("ALTER TABLE userbot_accounts ADD COLUMN owner_tg_id BIGINT")
            except Exception: pass
            try: cur.execute("ALTER TABLE userbot_accounts ADD COLUMN stars_balance INTEGER DEFAULT 0")
            except Exception: pass
            cur.execute("DELETE FROM userbot_accounts")
            for a in accounts:
                cur.execute(
                    "INSERT INTO userbot_accounts (id, session, phone, session_string, api_id, api_hash, first_name, last_name, username, bio, photo, active, owner_tg_id, stars_balance) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        a.get("id"), a.get("session",""), a.get("phone",""), a.get("session_string",""),
                        a.get("api_id", 0), a.get("api_hash",""), a.get("first_name",""), a.get("last_name",""),
                        a.get("username",""), a.get("bio",""), a.get("photo",""), 1 if a.get("active", True) else 0,
                        a.get("owner_tg_id"), a.get("stars_balance", 0)
                    )
                )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"PostgreSQL db_save_userbot_accounts failed: {e}")

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS userbot_accounts (id INTEGER PRIMARY KEY, session TEXT, phone TEXT, session_string TEXT, api_id INTEGER, api_hash TEXT, first_name TEXT, last_name TEXT, username TEXT, bio TEXT, photo TEXT, active INTEGER DEFAULT 1, owner_tg_id INTEGER, stars_balance INTEGER DEFAULT 0)")
        try: cur.execute("ALTER TABLE userbot_accounts ADD COLUMN owner_tg_id INTEGER")
        except Exception: pass
        try: cur.execute("ALTER TABLE userbot_accounts ADD COLUMN stars_balance INTEGER DEFAULT 0")
        except Exception: pass
        cur.execute("DELETE FROM userbot_accounts")
        for a in accounts:
            cur.execute(
                "INSERT INTO userbot_accounts (id, session, phone, session_string, api_id, api_hash, first_name, last_name, username, bio, photo, active, owner_tg_id, stars_balance) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    a.get("id"), a.get("session",""), a.get("phone",""), a.get("session_string",""),
                    a.get("api_id", 0), a.get("api_hash",""), a.get("first_name",""), a.get("last_name",""),
                    a.get("username",""), a.get("bio",""), a.get("photo",""), 1 if a.get("active", True) else 0,
                    a.get("owner_tg_id"), a.get("stars_balance", 0)
                )
            )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"db_save_userbot_accounts failed: {e}")
        return False


async def set_userbot_active_status(account_id: int, active: bool) -> bool:
    """Updates active status (1 for active, 0 for disabled) in PostgreSQL and SQLite database."""
    act_val = 1 if active else 0
    if IS_POSTGRES and pool:
        try:
            async with pool.acquire() as conn:
                await conn.execute("UPDATE userbot_accounts SET active=$1 WHERE id=$2", act_val, account_id)
        except Exception as e:
            logger.error(f"PostgreSQL set_userbot_active_status error: {e}")

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE userbot_accounts SET active=? WHERE id=?", (act_val, account_id))
            await db.commit()
    except Exception as e:
        logger.error(f"SQLite set_userbot_active_status error: {e}")

    return True


async def update_userbot_account_db(account_id: int, **fields) -> bool:
    """Updates specific fields of a userbot account in PostgreSQL and SQLite database."""
    if not fields:
        return True
    
    allowed = {"session", "phone", "session_string", "api_id", "api_hash", "first_name", "last_name", "username", "bio", "photo", "active", "owner_tg_id", "stars_balance"}
    valid_fields = {k: v for k, v in fields.items() if k in allowed}
    if not valid_fields:
        return True

    # Map boolean active to int/bool as appropriate
    if "active" in valid_fields:
        valid_fields["active"] = 1 if valid_fields["active"] else 0

    if IS_POSTGRES and pool:
        try:
            sets = ", ".join(f"{k}=${i+1}" for i, k in enumerate(valid_fields.keys()))
            vals = list(valid_fields.values())
            vals.append(account_id)
            async with pool.acquire() as conn:
                await conn.execute(f"UPDATE userbot_accounts SET {sets} WHERE id=${len(vals)}", *vals)
        except Exception as e:
            logger.error(f"PostgreSQL update_userbot_account_db error: {e}")

    try:
        sets = ", ".join(f"{k}=?" for k in valid_fields.keys())
        vals = list(valid_fields.values())
        vals.append(account_id)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(f"UPDATE userbot_accounts SET {sets} WHERE id=?", vals)
            await db.commit()
    except Exception as e:
        logger.error(f"SQLite update_userbot_account_db error: {e}")

    return True



_CACHE_PRICING = {"data": None, "ts": 0}
_CACHE_MANAGED_BOTS = {"data": None, "ts": 0}

async def get_pricing_settings() -> dict:
    """Returns dynamic pricing settings for Bot, Userbot, and My Account senders."""
    now = time.time()
    if _CACHE_PRICING["data"] is not None and (now - _CACHE_PRICING["ts"]) < 5.0:
        return dict(_CACHE_PRICING["data"])

    defaults = {"bot_stars": 3, "userbot_stars": 5, "myaccount_stars": 0}
    try:
        if IS_POSTGRES and pool:
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT key, value FROM settings WHERE key LIKE '%_stars'")
                for r in rows:
                    if r["key"] in defaults:
                        try:
                            val = float(r["value"])
                            if val >= 30:
                                val = val - 50
                            defaults[r["key"]] = max(0.0, val)
                        except ValueError: pass
        else:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                cur = await db.execute("SELECT key, value FROM settings WHERE key LIKE '%_stars'")
                rows = await cur.fetchall()
                for r in rows:
                    if r["key"] in defaults:
                        try:
                            val = float(r["value"])
                            if val >= 30:
                                val = val - 50
                            defaults[r["key"]] = max(0.0, val)
                        except ValueError: pass
        _CACHE_PRICING["data"] = dict(defaults)
        _CACHE_PRICING["ts"] = now
    except Exception as e:
        logger.error(f"get_pricing_settings error: {e}")
    return defaults


async def get_setting(key: str, default: str = "") -> str:
    """Get setting value from database by key."""
    try:
        if IS_POSTGRES and pool:
            async with pool.acquire() as conn:
                val = await conn.fetchval("SELECT value FROM settings WHERE key=$1", str(key))
                return str(val) if val is not None else default
        else:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT value FROM settings WHERE key=?", (str(key),)) as cursor:
                    row = await cursor.fetchone()
                    return str(row[0]) if row and row[0] is not None else default
    except Exception as e:
        logger.error(f"get_setting error for key '{key}': {e}")
        return default


async def set_setting(key: str, value: str) -> bool:
    """Set setting key-value pair in database."""
    try:
        if IS_POSTGRES and pool:
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value=$2",
                    str(key), str(value)
                )
        else:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=?",
                    (str(key), str(value), str(value))
                )
                await db.commit()
        return True
    except Exception as e:
        logger.error(f"set_setting error for key '{key}': {e}")
        return False


# ── Managed Bots CRUD ───────────────────────────────────────────────

async def get_all_managed_bots():
    now = time.time()
    if _CACHE_MANAGED_BOTS["data"] is not None and (now - _CACHE_MANAGED_BOTS["ts"]) < 5.0:
        return [dict(b) for b in _CACHE_MANAGED_BOTS["data"]]

    res = []
    if IS_POSTGRES and pool:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM managed_bots ORDER BY id ASC")
            res = [dict(r) for r in rows]
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM managed_bots ORDER BY id ASC") as cursor:
                rows = await cursor.fetchall()
                res = [dict(r) for r in rows]

    if res:
        _CACHE_MANAGED_BOTS["data"] = res
        _CACHE_MANAGED_BOTS["ts"] = now
    return res

async def add_managed_bot(token: str, bot_username: str, bot_name: str, bot_id: int):
    if IS_POSTGRES and pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO managed_bots (token, bot_username, bot_name, bot_id, active)
                   VALUES ($1, $2, $3, $4, 1)
                   ON CONFLICT (token) DO UPDATE SET bot_username=$2, bot_name=$3, bot_id=$4, active=1
                   RETURNING *""",
                token, bot_username, bot_name, bot_id
            )
            return dict(row)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute(
                """INSERT OR REPLACE INTO managed_bots (token, bot_username, bot_name, bot_id, active)
                   VALUES (?, ?, ?, ?, 1)""",
                (token, bot_username, bot_name, bot_id)
            )
            await db.commit()
            async with db.execute("SELECT * FROM managed_bots WHERE token=?", (token,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

async def toggle_managed_bot_status(bot_id: int, active: int):
    if IS_POSTGRES and pool:
        async with pool.acquire() as conn:
            await conn.execute("UPDATE managed_bots SET active=$1 WHERE id=$2", active, bot_id)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE managed_bots SET active=? WHERE id=?", (active, bot_id))
            await db.commit()

async def delete_managed_bot(bot_id: int):
    if IS_POSTGRES and pool:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM managed_bots WHERE id=$1", bot_id)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM managed_bots WHERE id=?", (bot_id,))
            await db.commit()

async def update_managed_bot_commands(bot_id: int, commands_json: str, scripts_json: str):
    if IS_POSTGRES and pool:
        async with pool.acquire() as conn:
            await conn.execute("UPDATE managed_bots SET commands_json=$1, scripts_json=$2 WHERE id=$3", commands_json, scripts_json, bot_id)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE managed_bots SET commands_json=?, scripts_json=? WHERE id=?", (commands_json, scripts_json, bot_id))
            await db.commit()

async def get_managed_bot_by_id(bot_id: int):
    if IS_POSTGRES and pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM managed_bots WHERE id=$1", bot_id)
            return dict(row) if row else None
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM managed_bots WHERE id=?", (bot_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

# ── Bot User Messages CRUD ───────────────────────────────────────────────

async def save_bot_user_message(bot_token: str, user_id: int, user_username: str, user_first_name: str, message_id: int, text: str, out: int = 0, date_str: str = "", media_type: str = None, media_data: str = None, file_name: str = None):
    if IS_POSTGRES and pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO bot_user_messages (bot_token, user_id, user_username, user_first_name, message_id, text, out, date, media_type, media_data, file_name)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                   RETURNING *""",
                bot_token, user_id, user_username, user_first_name, message_id, text, out, date_str, media_type, media_data, file_name
            )
            return dict(row)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """INSERT INTO bot_user_messages (bot_token, user_id, user_username, user_first_name, message_id, text, out, date, media_type, media_data, file_name)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (bot_token, user_id, user_username, user_first_name, message_id, text, out, date_str, media_type, media_data, file_name)
            )
            await db.commit()
            last_id = cursor.lastrowid
            async with db.execute("SELECT * FROM bot_user_messages WHERE id=?", (last_id,)) as c:
                row = await c.fetchone()
                return dict(row) if row else None

async def save_bot_user_profile(bot_token: str, user_id: int, username: str, first_name: str, photo: str = None, info: str = None):
    if IS_POSTGRES and pool:
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO bot_users (bot_token, user_id, username, first_name, photo, info)
                   VALUES ($1, $2, $3, $4, $5, $6)
                   ON CONFLICT (bot_token, user_id) 
                   DO UPDATE SET username = EXCLUDED.username, first_name = EXCLUDED.first_name, 
                                 photo = COALESCE(EXCLUDED.photo, bot_users.photo), 
                                 info = COALESCE(EXCLUDED.info, bot_users.info)""",
                bot_token, user_id, username, first_name, photo, info
            )
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO bot_users (bot_token, user_id, username, first_name, photo, info)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT (bot_token, user_id) 
                   DO UPDATE SET username = excluded.username, first_name = excluded.first_name,
                                 photo = CASE WHEN excluded.photo IS NOT NULL THEN excluded.photo ELSE bot_users.photo END,
                                 info = CASE WHEN excluded.info IS NOT NULL THEN excluded.info ELSE bot_users.info END""",
                (bot_token, user_id, username, first_name, photo, info)
            )
            await db.commit()

async def get_bot_user_chat_history(bot_token: str, user_id: int):
    if IS_POSTGRES and pool:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM bot_user_messages WHERE bot_token=$1 AND user_id=$2 ORDER BY id ASC", bot_token, user_id)
            return [dict(r) for r in rows]
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM bot_user_messages WHERE bot_token=? AND user_id=? ORDER BY id ASC", (bot_token, user_id)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

async def get_bot_chat_contacts(bot_token: str):
    if IS_POSTGRES and pool:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT m.user_id, m.user_username, m.user_first_name, m.text as last_msg, m.date as last_time, m.out as last_out,
                          m.media_type as last_media_type, m.media_data as last_media_data, m.file_name as last_file_name,
                          u.photo as user_photo, u.info as user_info
                   FROM bot_user_messages m
                   LEFT JOIN bot_users u ON m.bot_token = u.bot_token AND m.user_id = u.user_id
                   WHERE m.bot_token=$1 ORDER BY m.id DESC""", bot_token
            )
            seen = set()
            contacts = []
            for r in rows:
                uid = r["user_id"]
                if uid not in seen:
                    seen.add(uid)
                    contacts.append(dict(r))
            return contacts
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT m.user_id, m.user_username, m.user_first_name, m.text as last_msg, m.date as last_time, m.out as last_out,
                          m.media_type as last_media_type, m.media_data as last_media_data, m.file_name as last_file_name,
                          u.photo as user_photo, u.info as user_info
                   FROM bot_user_messages m
                   LEFT JOIN bot_users u ON m.bot_token = u.bot_token AND m.user_id = u.user_id
                   WHERE m.bot_token=? ORDER BY m.id DESC""", (bot_token,)
            ) as cursor:
                rows = await cursor.fetchall()
                seen = set()
                contacts = []
                for r in rows:
                    uid = r["user_id"]
                    if uid not in seen:
                        seen.add(uid)
                        contacts.append(dict(r))
                return contacts

async def get_managed_bot_user_count(bot_token: str) -> int:
    """Returns the count of distinct users who messaged this bot."""
    if IS_POSTGRES and pool:
        async with pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(DISTINCT user_id) FROM bot_user_messages WHERE bot_token=$1", bot_token)
            return count or 0
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(DISTINCT user_id) FROM bot_user_messages WHERE bot_token=?", (bot_token,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

async def get_managed_bot_users_with_info(bot_token: str) -> list:
    """Returns user directory for a bot: user_id, username, first_name, message_count, last_message, last_active."""
    sql_pg = """
        SELECT b1.user_id, 
               MAX(b1.user_username) as user_username,
               MAX(b1.user_first_name) as user_first_name,
               COUNT(*) as message_count,
               (SELECT text FROM bot_user_messages b2 WHERE b2.bot_token=$1 AND b2.user_id=b1.user_id ORDER BY b2.id DESC LIMIT 1) as last_message,
               (SELECT media_type FROM bot_user_messages b2 WHERE b2.bot_token=$1 AND b2.user_id=b1.user_id ORDER BY b2.id DESC LIMIT 1) as last_media_type,
               MAX(b1.date) as last_active,
               MAX(u.photo) as user_photo,
               MAX(u.info) as user_info
        FROM bot_user_messages b1
        LEFT JOIN bot_users u ON b1.bot_token = u.bot_token AND b1.user_id = u.user_id
        WHERE b1.bot_token=$1
        GROUP BY b1.user_id
        ORDER BY MAX(b1.id) DESC
    """
    sql_sqlite = """
        SELECT b1.user_id, 
               MAX(b1.user_username) as user_username,
               MAX(b1.user_first_name) as user_first_name,
               COUNT(*) as message_count,
               (SELECT text FROM bot_user_messages b2 WHERE b2.bot_token=b1.bot_token AND b2.user_id=b1.user_id ORDER BY b2.id DESC LIMIT 1) as last_message,
               (SELECT media_type FROM bot_user_messages b2 WHERE b2.bot_token=b1.bot_token AND b2.user_id=b1.user_id ORDER BY b2.id DESC LIMIT 1) as last_media_type,
               MAX(b1.date) as last_active,
               MAX(u.photo) as user_photo,
               MAX(u.info) as user_info
        FROM bot_user_messages b1
        LEFT JOIN bot_users u ON b1.bot_token = u.bot_token AND b1.user_id = u.user_id
        WHERE b1.bot_token=?
        GROUP BY b1.user_id
        ORDER BY MAX(b1.id) DESC
    """
    if IS_POSTGRES and pool:
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql_pg, bot_token)
            return [dict(r) for r in rows]
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql_sqlite, (bot_token,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]


async def get_all_managed_bot_user_counts() -> dict:
    """Returns {bot_token: user_count} for all managed bots."""
    if IS_POSTGRES and pool:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT bot_token, COUNT(DISTINCT user_id) as cnt FROM bot_user_messages GROUP BY bot_token")
            return {r["bot_token"]: r["cnt"] for r in rows}
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT bot_token, COUNT(DISTINCT user_id) as cnt FROM bot_user_messages GROUP BY bot_token") as cursor:
                rows = await cursor.fetchall()
                return {r["bot_token"]: r["cnt"] for r in rows}


async def get_allowed_admins() -> list:
    """Returns list of allowed admin user IDs."""
    return [6588631008]


async def set_allowed_admins(admin_ids: list) -> bool:
    """Saves list of allowed admin user IDs."""
    try:
        val_str = json.dumps(admin_ids)
        if IS_POSTGRES and pool:
            async with pool.acquire() as conn:
                await conn.execute("INSERT INTO settings (key, value) VALUES ('allowed_admins', $1) ON CONFLICT (key) DO UPDATE SET value=$1", val_str)
        else:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("INSERT INTO settings (key, value) VALUES ('allowed_admins', ?) ON CONFLICT(key) DO UPDATE SET value=?", (val_str, val_str))
                await db.commit()
        return True
    except Exception as e:
        logger.error(f"set_allowed_admins error: {e}")
        return False


