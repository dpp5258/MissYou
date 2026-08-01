"""
MissYou 数据存储层 — Google Sheets 实现
所有表格读写封装在 MissYouStore 中，通过模块级单例访问
"""
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Callable

import gspread
from google.oauth2.service_account import Credentials


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
# 存储后端
# ============================================================

class MissYouStore:
    """Google Sheets 存储后端 — 连接复用，方法封装"""

    def __init__(self, creds_dict: dict, sheet_id: str):
        self._creds_dict = creds_dict
        self._sheet_id = sheet_id
        self._sheet = None

    @property
    def sheet(self):
        """懒加载 Google Sheet 连接，同进程内复用"""
        if self._sheet is None:
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_info(
                self._creds_dict, scopes=scopes
            )
            client = gspread.authorize(creds)
            self._sheet = client.open_by_key(self._sheet_id)
        return self._sheet

    # ── 账户状态 ──────────────────────────────────

    def get_account(self) -> AccountState:
        """读取账户状态工作表"""
        ws = self.sheet.worksheet("账户状态")
        row = ws.row_values(2)
        if not row or len(row) < 4:
            return AccountState()
        return AccountState(
            balance=float(row[0]),
            daily_decay=float(row[1]),
            last_update=row[2],
            start_date=row[3],
        )

    def set_balance(
        self, balance: float, daily_decay: float,
        last_update: str, start_date: str,
    ):
        """覆写账户状态"""
        ws = self.sheet.worksheet("账户状态")
        ws.update("A2:D2", [[balance, daily_decay, last_update, start_date]])

    # ── 操作日志 ──────────────────────────────────

    def add_log(
        self, op_type: str, change: str,
        balance_after: float, note: str = "",
    ):
        """追加操作日志"""
        ws = self.sheet.worksheet("操作记录")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        ws.append_row([timestamp, op_type, change, balance_after, note])

    def get_logs(self, limit: int = 20) -> list[dict]:
        """读取最近 N 条操作日志（倒序）"""
        ws = self.sheet.worksheet("操作记录")
        all_rows = ws.get_all_values()
        data_rows = all_rows[1:] if len(all_rows) > 1 else []
        recent = data_rows[-limit:] if len(data_rows) > limit else data_rows
        recent.reverse()
        logs = []
        for row in recent:
            if len(row) >= 5:
                logs.append({
                    "time": row[0],
                    "op_type": row[1],
                    "change": row[2],
                    "balance_after": row[3],
                    "note": row[4],
                })
        return logs

    # ── 游戏记录 ──────────────────────────────────

    def _ensure_game_sheet(self):
        """确保"游戏记录"工作表存在"""
        try:
            self.sheet.worksheet("游戏记录")
        except gspread.exceptions.WorksheetNotFound:
            ws = self.sheet.add_worksheet("游戏记录", rows=1000, cols=7)
            ws.append_row([
                "时间", "游戏类型", "题目ID", "题目数据",
                "用户答案", "得分", "操作后余额",
            ])

    def is_question_recent(self, game_type: str, qid: str) -> bool:
        """检查该题目 7 天内是否已经答对过"""
        try:
            ws = self.sheet.worksheet("游戏记录")
        except gspread.exceptions.WorksheetNotFound:
            return False

        cutoff = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
        all_rows = ws.get_all_values()

        for row in all_rows[1:]:
            if len(row) < 3:
                continue
            if (
                row[1] == game_type
                and row[2] == qid
                and row[0][:10] >= cutoff
            ):
                return True
        return False

    def _record_game(
        self, game_type: str, qid: str, question_data: dict,
        user_answer, score: int, balance_after: float,
    ):
        """写游戏记录（去重 + 审计用）"""
        ws = self.sheet.worksheet("游戏记录")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        q_snapshot = ", ".join(
            f"{k}:{v}" for k, v in question_data.items()
        )
        answer_str = (
            json.dumps(user_answer, ensure_ascii=False)
            if isinstance(user_answer, dict)
            else str(user_answer)
        )
        ws.append_row([
            timestamp, game_type, qid, q_snapshot,
            answer_str, score, int(balance_after),
        ])

    # ── 统一加分流程 ──────────────────────────────

    def submit_game_score(
        self, game, question_data: dict, user_answer,
        calc_score_fn: Callable | None = None,
    ) -> ScoreResult:
        """
        统一加分入口 — 所有游戏共用。
        流程：去重 → 验证 → 计分 → 写账户 → 写日志 → 写游戏记录

        calc_score_fn: (game, question_data, user_answer) -> int
            部分游戏根据表现动态调整得分。为 None 则使用 game.score 固定分。
        """
        import traceback as _traceback

        try:
            # 1. 生成题目 ID
            qid = game.question_id(question_data)

            # 2. 确保工作表存在
            self._ensure_game_sheet()

            # 3. 7 天去重检查
            if self.is_question_recent(game.game_id, qid):
                return ScoreResult(
                    False, "⏳ 这道题 7 天内已经答过了，换一题吧～"
                )

            # 4. 服务端验证答案
            if not game.validate(question_data, user_answer):
                return ScoreResult(False, "❌ 答案不对，再想想哦～")

            # 5. 计算实际得分
            score = calc_score_fn(game, question_data, user_answer) if calc_score_fn else game.score

            # 6. 读取当前余额
            account = self.get_account()
            new_balance = account.balance + score

            # 7. 写账户状态
            self.set_balance(
                new_balance, account.daily_decay,
                date.today().strftime("%Y-%m-%d"), account.start_date,
            )

            # 8. 写操作日志
            self.add_log(
                f"游戏奖励-{game.name}",
                f"+{score}",
                new_balance,
                f"题目#{qid}",
            )

            # 9. 写游戏记录（去重用）
            self._record_game(
                game.game_id, qid, question_data, user_answer, score, new_balance,
            )

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


def init_store(creds_dict: dict, sheet_id: str):
    """初始化全局存储实例（app.py 启动时调用一次）"""
    global _store
    _store = MissYouStore(creds_dict, sheet_id)


def get_store() -> MissYouStore:
    """获取全局存储实例"""
    if _store is None:
        raise RuntimeError(
            "MissYouStore 未初始化，请先调用 storage.init_store()"
        )
    return _store
