import sqlite3
import os
from datetime import datetime, date
from config import DATABASE_PATH, ACHIEVEMENTS


def get_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT NOT NULL,
            coins       INTEGER DEFAULT 0,
            total_coins INTEGER DEFAULT 0,
            points      INTEGER DEFAULT 0,
            streak      INTEGER DEFAULT 0,
            last_daily  TEXT,
            last_active TEXT,
            joined_at   TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS predictions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            match_id        INTEGER NOT NULL,
            home_team       TEXT NOT NULL,
            away_team       TEXT NOT NULL,
            predicted_winner TEXT NOT NULL,
            predicted_home  INTEGER,
            predicted_away  INTEGER,
            actual_winner   TEXT,
            points_awarded  INTEGER DEFAULT 0,
            resolved        INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, match_id)
        );

        CREATE TABLE IF NOT EXISTS achievements (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            achievement TEXT NOT NULL,
            earned_at   TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, achievement)
        );

        CREATE TABLE IF NOT EXISTS trivia_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            correct     INTEGER NOT NULL,
            coins_earned INTEGER DEFAULT 0,
            played_at   TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS giveaways (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id  INTEGER NOT NULL,
            message_id  INTEGER,
            prize       TEXT NOT NULL,
            end_time    TEXT NOT NULL,
            active      INTEGER DEFAULT 1,
            winner_id   INTEGER,
            created_by  INTEGER NOT NULL,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS giveaway_entries (
            giveaway_id INTEGER NOT NULL,
            user_id     INTEGER NOT NULL,
            entries     INTEGER DEFAULT 1,
            PRIMARY KEY (giveaway_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS server_config (
            guild_id            INTEGER PRIMARY KEY,
            live_channel_id     INTEGER,
            leaderboard_channel_id INTEGER,
            stats_channel_id    INTEGER,
            bracket_channel_id  INTEGER,
            notify_channel_id   INTEGER,
            log_channel_id      INTEGER,
            live_message_id     INTEGER,
            leaderboard_message_id INTEGER,
            stats_message_id    INTEGER,
            bracket_message_id  INTEGER,
            updated_at          TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS hype_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id    INTEGER NOT NULL,
            channel_id  INTEGER NOT NULL,
            message_id  INTEGER,
            event_type  TEXT NOT NULL,
            prize_coins INTEGER DEFAULT 50,
            active      INTEGER DEFAULT 1,
            end_time    TEXT NOT NULL,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS hype_participants (
            event_id    INTEGER NOT NULL,
            user_id     INTEGER NOT NULL,
            PRIMARY KEY (event_id, user_id)
        );
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized.")


def ensure_user(user_id: int, username: str):
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
        (user_id, username)
    )
    conn.execute(
        "UPDATE users SET username=?, last_active=? WHERE user_id=?",
        (username, datetime.utcnow().isoformat(), user_id)
    )
    conn.commit()
    conn.close()


def get_user(user_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_coins(user_id: int, amount: int):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET coins=MAX(0,coins+?), total_coins=total_coins+MAX(0,?) WHERE user_id=?",
        (amount, amount, user_id)
    )
    conn.commit()
    conn.close()


def update_points(user_id: int, amount: int):
    conn = get_connection()
    conn.execute("UPDATE users SET points=points+? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()


def claim_daily(user_id: int, coins: int) -> bool:
    today = date.today().isoformat()
    conn = get_connection()
    user = conn.execute("SELECT last_daily, streak FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return False
    last = user["last_daily"]
    streak = user["streak"] or 0

    if last == today:
        conn.close()
        return False

    yesterday = (date.today().toordinal() - 1)
    prev_date = date.fromordinal(yesterday).isoformat() if yesterday > 0 else None
    new_streak = streak + 1 if last == prev_date else 1

    conn.execute(
        "UPDATE users SET coins=coins+?, total_coins=total_coins+?, last_daily=?, streak=? WHERE user_id=?",
        (coins, coins, today, new_streak, user_id)
    )
    conn.commit()
    conn.close()
    return True


def get_leaderboard(limit=10):
    conn = get_connection()
    rows = conn.execute(
        "SELECT user_id, username, points, coins FROM users ORDER BY points DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_coin_leaderboard(limit=10):
    conn = get_connection()
    rows = conn.execute(
        "SELECT user_id, username, coins, total_coins FROM users ORDER BY coins DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_prediction(user_id: int, match_id: int, home: str, away: str, winner: str, home_score: int = None, away_score: int = None) -> bool:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO predictions (user_id, match_id, home_team, away_team, predicted_winner, predicted_home, predicted_away) VALUES (?,?,?,?,?,?,?)",
            (user_id, match_id, home, away, winner, home_score, away_score)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def get_user_predictions(user_id: int):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM predictions WHERE user_id=? ORDER BY created_at DESC LIMIT 20",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_unresolved_predictions(match_id: int):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM predictions WHERE match_id=? AND resolved=0",
        (match_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def resolve_prediction(pred_id: int, actual_winner: str, points: int):
    conn = get_connection()
    conn.execute(
        "UPDATE predictions SET actual_winner=?, points_awarded=?, resolved=1 WHERE id=?",
        (actual_winner, points, pred_id)
    )
    conn.commit()
    conn.close()


def grant_achievement(user_id: int, key: str) -> bool:
    if key not in ACHIEVEMENTS:
        return False
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO achievements (user_id, achievement) VALUES (?,?)",
            (user_id, key)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def get_user_achievements(user_id: int):
    conn = get_connection()
    rows = conn.execute("SELECT achievement FROM achievements WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    return [r["achievement"] for r in rows]


def log_trivia(user_id: int, correct: bool, coins: int):
    conn = get_connection()
    conn.execute(
        "INSERT INTO trivia_history (user_id, correct, coins_earned) VALUES (?,?,?)",
        (user_id, 1 if correct else 0, coins)
    )
    conn.commit()
    conn.close()


def get_server_config(guild_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM server_config WHERE guild_id=?", (guild_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def set_server_config(guild_id: int, **kwargs):
    conn = get_connection()
    existing = conn.execute("SELECT guild_id FROM server_config WHERE guild_id=?", (guild_id,)).fetchone()
    kwargs["updated_at"] = datetime.utcnow().isoformat()
    if existing:
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [guild_id]
        conn.execute(f"UPDATE server_config SET {sets} WHERE guild_id=?", vals)
    else:
        kwargs["guild_id"] = guild_id
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" for _ in kwargs)
        conn.execute(f"INSERT INTO server_config ({cols}) VALUES ({placeholders})", list(kwargs.values()))
    conn.commit()
    conn.close()


def get_server_stats():
    conn = get_connection()
    total_predictions = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_coins = conn.execute("SELECT SUM(total_coins) FROM users").fetchone()[0] or 0
    today = date.today().isoformat()
    active_today = conn.execute(
        "SELECT COUNT(*) FROM users WHERE last_active LIKE ?", (today + "%",)
    ).fetchone()[0]
    resolved = conn.execute("SELECT COUNT(*) FROM predictions WHERE resolved=1").fetchone()[0]
    completion = round((resolved / total_predictions * 100) if total_predictions > 0 else 0, 1)
    conn.close()
    return {
        "total_predictions": total_predictions,
        "total_users": total_users,
        "total_coins": total_coins,
        "active_today": active_today,
        "completion_rate": completion,
    }
