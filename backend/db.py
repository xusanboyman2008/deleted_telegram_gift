import os
import logging
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
    ("🧸", "Bunny Basket",  "03/08/26", "5866352046986232958", 50, DEFAULT_COMMISSION, "bunny_bear.json"),
    ("🧸", "Balloon Bear",  "03/17/26", "5893356958802511476", 50, DEFAULT_COMMISSION, "joker_bear.json"),
    ("🧸", "Rose Bear",     "02/14/26", "5801108895304779062", 50, DEFAULT_COMMISSION, "pink_bear.json"),
    ("🧸", "Worker Bear",   "04/01/26", "5935895822435615975", 50, DEFAULT_COMMISSION, "plumber_bear.json"),
    ("🧸", "Football Bear", "05/01/26", "6026193266406327981", 50, DEFAULT_COMMISSION, "football_bear.json"),
    ("🧸", "Santa Teddy",   "12/25/25", "5922558454332916696", 50, DEFAULT_COMMISSION, "santa_bear.json"),
    ("🧸", "Gnome Bear",    "07/20/26", "5974210632977745012", 50, DEFAULT_COMMISSION, "gnome_bear.json"),
    ("💖", "I Love U",      "02/14/26", "5800655655995968839", 50, DEFAULT_COMMISSION, "hear.json"),
    ("🎄", "Christmas Tree","12/31/25", "5956217000635139069", 50, DEFAULT_COMMISSION, "green_tree.json"),
    ("🧸", "Hug Bear",      "05/10/26", "5800655655995968830", 50, DEFAULT_COMMISSION, "hug_bear.json"),
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

pool = None


async def init_db():
    global pool, IS_POSTGRES, DATABASE_URL
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    IS_POSTGRES = DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")

    if IS_POSTGRES:
        pg_url = DATABASE_URL.replace("postgres://", "postgresql://")
        pool = await asyncpg.create_pool(pg_url)
        async with pool.acquire() as conn:
            await conn.execute(CREATE_GIFTS_POSTGRES)
            await conn.execute(CREATE_ORDERS_POSTGRES)
            try: await conn.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS gift_text TEXT")
            except Exception: pass
            try: await conn.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS sender_type TEXT DEFAULT 'bot'")
            except Exception: pass
            try: await conn.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS userbot_id INTEGER")
            except Exception: pass
            
            # Legacy cleanup: fix Hug Bear gift_tg_id mapping and remove duplicate rows
            try:
                await conn.execute("UPDATE gifts SET display_name='Hug Bear', emoji='🧸', animation='hug_bear.json' WHERE gift_tg_id='5800655655995968830'")
                await conn.execute("DELETE FROM gifts WHERE id IN (SELECT id FROM (SELECT id, ROW_NUMBER() OVER(PARTITION BY gift_tg_id ORDER BY id) as row_num FROM gifts) t WHERE t.row_num > 1)")
            except Exception: pass

            for g in GIFTS_SEED:
                await conn.execute(
                    """INSERT INTO gifts (emoji, display_name, date_label, gift_tg_id, base_stars, commission, animation)
                       VALUES ($1, $2, $3, $4, $5, $6, $7)
                       ON CONFLICT (gift_tg_id) DO NOTHING""",
                    g[0], g[1], g[2], g[3], g[4], g[5], g[6]
                )
        print(f"[DB] PostgreSQL database initialized with {len(GIFTS_SEED)} gifts.")
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(CREATE_GIFTS_SQLITE)
            await db.execute(CREATE_ORDERS_SQLITE)
            try: await db.execute("ALTER TABLE orders ADD COLUMN gift_text TEXT")
            except Exception: pass
            try: await db.execute("ALTER TABLE orders ADD COLUMN sender_type TEXT DEFAULT 'bot'")
            except Exception: pass
            try: await db.execute("ALTER TABLE orders ADD COLUMN userbot_id INTEGER")
            except Exception: pass
            
            # Legacy cleanup: fix Hug Bear gift_tg_id mapping and remove duplicate rows
            try:
                await db.execute("UPDATE gifts SET display_name='Hug Bear', emoji='🧸', animation='hug_bear.json' WHERE gift_tg_id='5800655655995968830'")
                await db.execute("DELETE FROM gifts WHERE id NOT IN (SELECT MIN(id) FROM gifts GROUP BY gift_tg_id)")
                await db.commit()
            except Exception: pass

            await db.executemany(
                "INSERT OR IGNORE INTO gifts (emoji, display_name, date_label, gift_tg_id, base_stars, commission, animation) VALUES (?,?,?,?,?,?,?)",
                GIFTS_SEED,
            )
            await db.commit()
            print(f"[DB] SQLite database initialized with {len(GIFTS_SEED)} gifts.")


# ── Gift CRUD ──────────────────────────────────────────────────────────────

async def get_all_gifts(active_only: bool = True):
    if IS_POSTGRES:
        async with pool.acquire() as conn:
            q = "SELECT * FROM gifts"
            if active_only:
                q += " WHERE active=1"
            q += " ORDER BY id"
            rows = await conn.fetch(q)
            return [dict(r) for r in rows]
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            q = "SELECT * FROM gifts"
            if active_only:
                q += " WHERE active=1"
            q += " ORDER BY id"
            cur = await db.execute(q)
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_gift(gift_id: int):
    if IS_POSTGRES:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM gifts WHERE id=$1", gift_id)
            return dict(row) if row else None
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM gifts WHERE id=?", (gift_id,))
            row = await cur.fetchone()
            return dict(row) if row else None


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


async def get_orders_by_user(buyer_tg_id: int):
    if IS_POSTGRES:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT o.*, g.emoji, g.date_label, g.display_name, g.animation FROM orders o
                   LEFT JOIN gifts g ON g.id=o.gift_id
                   WHERE o.buyer_tg_id=$1
                   ORDER BY o.id DESC""",
                int(buyer_tg_id)
            )
            return [dict(r) for r in rows]
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                """SELECT o.*, g.emoji, g.date_label, g.display_name, g.animation FROM orders o
                   LEFT JOIN gifts g ON g.id=o.gift_id
                   WHERE o.buyer_tg_id=?
                   ORDER BY o.id DESC""",
                (buyer_tg_id,)
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]
