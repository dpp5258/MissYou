"""
MissYou 数据存储层 — Google Sheets 实现
所有表格读写封装在 MissYouStore 中，通过模块级单例访问
"""
from dataclasses import dataclass
from datetime import datetime

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
