import sqlite3
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List

logger = logging.getLogger("BiasDatabase")
DB_PATH = os.getenv("DATABASE_PATH", "/data/bias_data.db")


class BiasDatabase:
    def __init__(self):
        dirname = os.path.dirname(DB_PATH)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        self.init_db()

    def get_conn(self):
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def init_db(self):
        try:
            conn = self.get_conn()
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS bias_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coin TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    event TEXT NOT NULL,
                    bias TEXT NOT NULL,
                    entry REAL,
                    target REAL,
                    invalidation REAL,
                    win_rate REAL,
                    wins INTEGER,
                    losses INTEGER,
                    total INTEGER,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    resolved INTEGER DEFAULT 0,
                    result TEXT DEFAULT NULL,
                    resolved_at TEXT DEFAULT NULL,
                    profit_pct REAL DEFAULT NULL
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS active_biases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coin TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    bias TEXT NOT NULL,
                    entry REAL,
                    target REAL,
                    invalidation REAL,
                    win_rate REAL,
                    wins INTEGER,
                    losses INTEGER,
                    total INTEGER,
                    timestamp TEXT NOT NULL,
                    signal_id INTEGER,
                    UNIQUE(coin, timeframe)
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS subscribers (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    subscribed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            conn.commit()
            conn.close()
            logger.info("✅ Database schema verified.")
        except Exception as e:
            logger.error(f"❌ DB init error: {e}")

    def add_signal(self, data: dict) -> int:
        conn = self.get_conn()
        c = conn.cursor()

        c.execute('''
            INSERT INTO bias_signals
            (coin, timeframe, event, bias, entry, target,
             invalidation, win_rate, wins, losses, total, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['coin'], data['timeframe'], data['event'],
            data['bias'], data.get('entry'), data.get('target'),
            data.get('invalidation'), data.get('win_rate'),
            data.get('wins'), data.get('losses'),
            data.get('total'), data['timestamp']
        ))
        signal_id = c.lastrowid

        if data['event'] == 'NEW_BIAS':
            c.execute('''
                INSERT OR REPLACE INTO active_biases
                (coin, timeframe, bias, entry, target, invalidation,
                 win_rate, wins, losses, total, timestamp, signal_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['coin'], data['timeframe'], data['bias'],
                data.get('entry'), data.get('target'),
                data.get('invalidation'), data.get('win_rate'),
                data.get('wins'), data.get('losses'),
                data.get('total'), data['timestamp'], signal_id
            ))

        elif data['event'] in ('TARGET_HIT', 'INVALIDATION'):
            result = 'WIN' if data['event'] == 'TARGET_HIT' else 'LOSS'
            profit = None
            entry_val = float(data.get('entry') or 0)
            target_val = float(data.get('target') or 0)
            inval_val = float(data.get('invalidation') or 0)

            if entry_val > 0:
                if data['event'] == 'TARGET_HIT':
                    profit = abs((target_val - entry_val) / entry_val * 100)
                else:
                    profit = -abs((inval_val - entry_val) / entry_val * 100)

            # Standard SQL-compliant nested subquery update
            c.execute('''
                UPDATE bias_signals
                SET resolved = 1, result = ?, resolved_at = ?, profit_pct = ?
                WHERE id = (
                    SELECT id FROM bias_signals
                    WHERE coin = ? AND timeframe = ?
                    AND event = 'NEW_BIAS' AND resolved = 0
                    ORDER BY id DESC LIMIT 1
                )
            ''', (result, data['timestamp'], profit,
                  data['coin'], data['timeframe']))

            c.execute('''
                UPDATE bias_signals
                SET resolved = 1, result = ?, profit_pct = ?
                WHERE id = ?
            ''', (result, profit, signal_id))

            c.execute(
                'DELETE FROM active_biases WHERE coin = ? AND timeframe = ?',
                (data['coin'], data['timeframe'])
            )

        conn.commit()
        conn.close()
        return signal_id

    def get_active_biases(self, coin: str = None,
                          timeframe: str = None) -> List[dict]:
        conn = self.get_conn()
        c = conn.cursor()
        query = "SELECT * FROM active_biases WHERE 1=1"
        params = []
        if coin:
            query += " AND coin = ?"
            params.append(coin)
        if timeframe:
            query += " AND timeframe = ?"
            params.append(timeframe)
        query += " ORDER BY timestamp DESC"
        c.execute(query, params)
        results = [dict(r) for r in c.fetchall()]
        conn.close()
        return results

    def get_stats(self, coin: str = None, timeframe: str = None,
                  days: int = 30) -> List[dict]:
        conn = self.get_conn()
        c = conn.cursor()
        # ✅ Match ISO-8601 UTC format from webhook processor
        since = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')
        query = '''
            SELECT coin, timeframe, COUNT(*) as total,
                SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result='LOSS' THEN 1 ELSE 0 END) as losses,
                ROUND(AVG(CASE WHEN result='WIN'
                    THEN 1.0 ELSE 0.0 END)*100, 1) as win_rate,
                ROUND(AVG(profit_pct), 2) as avg_profit,
                ROUND(SUM(profit_pct), 2) as total_profit
            FROM bias_signals
            WHERE event IN ('TARGET_HIT','INVALIDATION')
            AND timestamp >= ?
        '''
        params = [since]
        if coin:
            query += " AND coin = ?"
            params.append(coin)
        if timeframe:
            query += " AND timeframe = ?"
            params.append(timeframe)
        query += " GROUP BY coin, timeframe ORDER BY win_rate DESC"
        c.execute(query, params)
        results = [dict(r) for r in c.fetchall()]
        conn.close()
        return results

    def get_overall_stats(self, days: int = 30) -> dict:
        conn = self.get_conn()
        c = conn.cursor()
        since = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')
        c.execute('''
            SELECT COUNT(*) as total,
                SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result='LOSS' THEN 1 ELSE 0 END) as losses,
                ROUND(AVG(CASE WHEN result='WIN'
                    THEN 1.0 ELSE 0.0 END)*100, 1) as win_rate,
                ROUND(AVG(profit_pct), 2) as avg_profit,
                ROUND(SUM(profit_pct), 2) as total_profit,
                COUNT(DISTINCT coin) as coins_tracked
            FROM bias_signals
            WHERE event IN ('TARGET_HIT','INVALIDATION')
            AND timestamp >= ?
        ''', (since,))
        row = c.fetchone()
        result = dict(row) if row else {}
        conn.close()
        return result

    def get_signals_by_date(self, date: str,
                            coin: str = None) -> List[dict]:
        conn = self.get_conn()
        c = conn.cursor()
        query = "SELECT * FROM bias_signals WHERE DATE(timestamp) = ?"
        params = [date]
        if coin:
            query += " AND coin = ?"
            params.append(coin)
        query += " ORDER BY timestamp ASC"
        c.execute(query, params)
        results = [dict(r) for r in c.fetchall()]
        conn.close()
        return results

    def get_coin_history(self, coin: str,
                         limit: int = 20) -> List[dict]:
        conn = self.get_conn()
        c = conn.cursor()
        c.execute(
            'SELECT * FROM bias_signals WHERE coin = ? '
            'ORDER BY timestamp DESC LIMIT ?',
            (coin, limit)
        )
        results = [dict(r) for r in c.fetchall()]
        conn.close()
        return results

    def get_all_coins(self) -> List[str]:
        conn = self.get_conn()
        c = conn.cursor()
        c.execute('SELECT DISTINCT coin FROM bias_signals ORDER BY coin')
        results = [r['coin'] for r in c.fetchall()]
        conn.close()
        return results

    def get_best_performers(self, days: int = 30,
                            limit: int = 5) -> List[dict]:
        conn = self.get_conn()
        c = conn.cursor()
        since = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')
        c.execute('''
            SELECT coin, timeframe, COUNT(*) as total,
                SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) as wins,
                ROUND(AVG(CASE WHEN result='WIN'
                    THEN 1.0 ELSE 0.0 END)*100, 1) as win_rate,
                ROUND(SUM(profit_pct), 2) as total_profit
            FROM bias_signals
            WHERE event IN ('TARGET_HIT','INVALIDATION')
            AND timestamp >= ?
            GROUP BY coin, timeframe HAVING total >= 3
            ORDER BY win_rate DESC LIMIT ?
        ''', (since, limit))
        results = [dict(r) for r in c.fetchall()]
        conn.close()
        return results

    def get_worst_performers(self, days: int = 30,
                             limit: int = 5) -> List[dict]:
        conn = self.get_conn()
        c = conn.cursor()
        since = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')
        c.execute('''
            SELECT coin, timeframe, COUNT(*) as total,
                SUM(CASE WHEN result='LOSS' THEN 1 ELSE 0 END) as losses,
                ROUND(AVG(CASE WHEN result='WIN'
                    THEN 1.0 ELSE 0.0 END)*100, 1) as win_rate,
                ROUND(SUM(profit_pct), 2) as total_profit
            FROM bias_signals
            WHERE event IN ('TARGET_HIT','INVALIDATION')
            AND timestamp >= ?
            GROUP BY coin, timeframe HAVING total >= 3
            ORDER BY win_rate ASC LIMIT ?
        ''', (since, limit))
        results = [dict(r) for r in c.fetchall()]
        conn.close()
        return results

    def get_streak(self, coin: str = None):
        conn = self.get_conn()
        c = conn.cursor()
        query = (
            "SELECT result FROM bias_signals "
            "WHERE event IN ('TARGET_HIT','INVALIDATION')"
        )
        params = []
        if coin:
            query += " AND coin = ?"
            params.append(coin)
        query += " ORDER BY timestamp DESC LIMIT 50"
        c.execute(query, params)
        results = [r['result'] for r in c.fetchall()]
        conn.close()
        if not results:
            return 0, "NONE"
        streak_type = results[0]
        count = 0
        for r in results:
            if r == streak_type:
                count += 1
            else:
                break
        return count, streak_type

    def add_subscriber(self, user_id: int, username: str = None):
        conn = self.get_conn()
        c = conn.cursor()
        c.execute(
            'INSERT OR REPLACE INTO subscribers '
            '(user_id, username, is_active) VALUES (?, ?, 1)',
            (user_id, username)
        )
        conn.commit()
        conn.close()

    def remove_subscriber(self, user_id: int):
        conn = self.get_conn()
        c = conn.cursor()
        c.execute(
            'UPDATE subscribers SET is_active=0 WHERE user_id=?',
            (user_id,)
        )
        conn.commit()
        conn.close()

    def get_active_subscribers(self) -> List[int]:
        conn = self.get_conn()
        c = conn.cursor()
        c.execute('SELECT user_id FROM subscribers WHERE is_active=1')
        results = [r['user_id'] for r in c.fetchall()]
        conn.close()
        return results
