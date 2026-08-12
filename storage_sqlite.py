"""
MissYou 数据存储层 — SQLite 实现
单文件数据库，零外部依赖，WAL 模式支持并发
"""
import sqlite3
import threading
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Callable


# ============================================================
# 数据类型
# ============================================================

@dataclass
class AccountState:
    balance: float = 0
    daily_decay: float = 0
    last_update: str = ""
    start_date: str = ""


@dataclass
class ScoreResult:
    success: bool
    message: str
    balance_after: int | None = None
    score: int = 0


# ============================================================
# 数据库路径
# ============================================================

def _db_path() -> str:
    """数据库文件与 app.py 同目录"""
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "missyou.db")


# ============================================================
# 存储后端
# ============================================================

class MissYouStore:
    """SQLite 存储后端 — 线程安全，懒初始化"""

    def __init__(self):
        self._conn: sqlite3.Connection | None = None
        self._init_lock = threading.Lock()

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接，自动建表"""
        if self._conn is None:
            with self._init_lock:
                if self._conn is None:
                    conn = sqlite3.connect(_db_path(), check_same_thread=False)
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA foreign_keys=ON")
                    self._conn = conn
                    self._create_tables(conn)
        return self._conn

    # ── 建表 ──────────────────────────────────────

    def _create_tables(self, conn: sqlite3.Connection):
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS account (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                balance REAL NOT NULL DEFAULT 0,
                daily_decay REAL NOT NULL DEFAULT 0,
                last_update TEXT NOT NULL DEFAULT '',
                start_date TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL,
                op_type TEXT NOT NULL,
                change TEXT NOT NULL,
                balance_after REAL NOT NULL,
                note TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS game_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL,
                game_type TEXT NOT NULL,
                qid TEXT NOT NULL,
                question_data TEXT NOT NULL DEFAULT '',
                user_answer TEXT NOT NULL DEFAULT '',
                score INTEGER NOT NULL DEFAULT 0,
                balance_after REAL NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_game_qid
                ON game_records(game_type, qid, time);
        """)
        conn.commit()

    # ── 账户状态 ──────────────────────────────────

    def get_account(self) -> AccountState:
        """读取账户状态"""
        conn = self._get_conn()
        row = conn.execute("SELECT balance, daily_decay, last_update, start_date FROM account WHERE id = 1").fetchone()
        if row is None:
            return AccountState()
        return AccountState(
            balance=row[0],
            daily_decay=row[1],
            last_update=row[2],
            start_date=row[3],
        )

    def set_balance(
        self, balance: float, daily_decay: float,
        last_update: str, start_date: str,
    ):
        """覆写账户状态（单行 upsert）"""
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO account (id, balance, daily_decay, last_update, start_date)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                balance = excluded.balance,
                daily_decay = excluded.daily_decay,
                last_update = excluded.last_update,
                start_date = excluded.start_date
        """, (balance, daily_decay, last_update, start_date))
        conn.commit()

    # ── 操作日志 ──────────────────────────────────

    def add_log(
        self, op_type: str, change: str,
        balance_after: float, note: str = "",
    ):
        """追加操作日志"""
        conn = self._get_conn()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn.execute(
            "INSERT INTO logs (time, op_type, change, balance_after, note) VALUES (?, ?, ?, ?, ?)",
            (timestamp, op_type, change, balance_after, note),
        )
        conn.commit()

    def get_logs(self, limit: int = 20) -> list[dict]:
        """读取最近 N 条操作日志（倒序）"""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT time, op_type, change, balance_after, note FROM logs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "time": r[0],
                "op_type": r[1],
                "change": r[2],
                "balance_after": r[3],
                "note": r[4],
            }
            for r in rows
        ]

    # ── 游戏记录 ──────────────────────────────────

    def is_question_recent(self, game_type: str, qid: str) -> bool:
        """检查该题目 7 天内是否已经答对过"""
        conn = self._get_conn()
        cutoff = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
        row = conn.execute(
            "SELECT 1 FROM game_records WHERE game_type = ? AND qid = ? AND time >= ? LIMIT 1",
            (game_type, qid, cutoff),
        ).fetchone()
        return row is not None

    def _record_game(
        self, game_type: str, qid: str, question_data: dict,
        user_answer, score: int, balance_after: float,
    ):
        """写游戏记录（去重 + 审计用）"""
        import json
        conn = self._get_conn()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        q_snapshot = ", ".join(f"{k}:{v}" for k, v in question_data.items())
        answer_str = (
            json.dumps(user_answer, ensure_ascii=False)
            if isinstance(user_answer, dict)
            else str(user_answer)
        )
        conn.execute(
            "INSERT INTO game_records (time, game_type, qid, question_data, user_answer, score, balance_after) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (timestamp, game_type, qid, q_snapshot, answer_str, score, int(balance_after)),
        )
        conn.commit()

    # ── 统一加分流程 ──────────────────────────────

    def submit_game_score(
        self, game, question_data: dict, user_answer,
        calc_score_fn: Callable | None = None,
    ) -> ScoreResult:
        """
        统一加分入口 — 事务包裹：去重 → 验证 → 计分 → 写账户 → 写日志 → 写游戏记录
        """
        import traceback as _traceback

        try:
            # 1. 生成题目 ID
            qid = game.question_id(question_data)

            # 2. 7 天去重检查
            if self.is_question_recent(game.game_id, qid):
                return ScoreResult(
                    False, "⏳ 这道题 7 天内已经答过了，换一题吧～"
                )

            # 3. 服务端验证答案
            if not game.validate(question_data, user_answer):
                return ScoreResult(False, "❌ 答案不对，再想想哦～")

            # 4. 计算实际得分
            score = calc_score_fn(game, question_data, user_answer) if calc_score_fn else game.score

            # 5. 读取当前余额
            account = self.get_account()
            new_balance = account.balance + score

            # 6-9. 事务写入
            conn = self._get_conn()
            conn.execute("BEGIN IMMEDIATE")
            try:
                self.set_balance(
                    new_balance, account.daily_decay,
                    date.today().strftime("%Y-%m-%d"), account.start_date,
                )
                self.add_log(
                    f"游戏奖励-{game.name}",
                    f"+{score}",
                    new_balance,
                    f"题目#{qid}",
                )
                self._record_game(
                    game.game_id, qid, question_data, user_answer, score, new_balance,
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

            return ScoreResult(
                True,
                f"🎉 答对了！+{score} 思念值 ✨",
                int(new_balance),
                score=score,
            )
        except Exception as e:
            _traceback.print_exc()
            return ScoreResult(
                False,
                f"❌ 数据存储异常，请稍后重试（{e}）",
            )


# ============================================================
# 模块级单例
# ============================================================

_store: MissYouStore | None = None


def init_store():
    """初始化全局存储实例（SQLite 无需外部凭据）"""
    global _store
    _store = MissYouStore()


def get_store() -> MissYouStore:
    """获取全局存储实例"""
    if _store is None:
        raise RuntimeError("MissYouStore 未初始化，请先调用 storage_sqlite.init_store()")
    return _store
