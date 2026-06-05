"""
MissYou — 思念量化系统
星空夜幕主题 | Google Sheets 数据 | Streamlit 部署
"""
import json

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date

# ============================================================
# 配置区
# ============================================================
USER_PWD = st.secrets["USER_PWD"]
ADMIN_PWD = st.secrets["ADMIN_PWD"]
SHEET_NAME = st.secrets["SHEET_NAME"]

# ============================================================
# Google Sheets 数据层
# ============================================================

def get_gsheet():
    """使用 Streamlit Secrets 中的凭证连接 Google Sheet"""
    try:
        creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open(st.secrets["SHEET_NAME"])
    except Exception as e:
        st.error(f"无法连接数据库：{e}")
        st.stop()

def read_account_state(sheet):
    """读取账户状态工作表的唯一一行数据，返回 dict"""
    ws = sheet.worksheet("账户状态")
    # 数据在第 2 行（第 1 行是表头）
    row = ws.row_values(2)
    if not row or len(row) < 4:
        return {"balance": 0, "daily_decay": 0, "last_update": "", "start_date": ""}
    return {
        "balance": float(row[0]),
        "daily_decay": float(row[1]),
        "last_update": row[2],
        "start_date": row[3],
    }

def write_account_state(sheet, balance, daily_decay, last_update, start_date):
    """覆写账户状态工作表的第 2 行"""
    ws = sheet.worksheet("账户状态")
    ws.update("A2:D2", [[balance, daily_decay, last_update, start_date]])

def append_operation_log(sheet, op_type, change, balance_after, note=""):
    """在操作记录工作表末尾追加一行"""
    ws = sheet.worksheet("操作记录")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    ws.append_row([timestamp, op_type, change, balance_after, note])

def read_operation_logs(sheet, limit=20):
    """读取操作记录工作表最近 N 条，返回 list[dict]"""
    ws = sheet.worksheet("操作记录")
    all_rows = ws.get_all_values()
    # 跳过表头，取最后 limit 行，倒序
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
# 衰减逻辑（纯函数）
# ============================================================

def calc_decay(balance, daily_decay, last_update_date):
    """
    计算从上次更新到今天，衰减后的余额。
    参数:
        balance: 当前余额
        daily_decay: 每日衰减量
        last_update_date: 上次更新日期 (date 对象)
    返回:
        (new_balance, days_passed)
    """
    today = date.today()
    if isinstance(last_update_date, str):
        last_update_date = datetime.strptime(last_update_date, "%Y-%m-%d").date()
    delta = today - last_update_date
    days_passed = max(0, delta.days)
    new_balance = balance - daily_decay * days_passed
    return new_balance, days_passed

# ============================================================
# Streamlit 页面配置
# ============================================================
st.set_page_config(page_title="MissYou", page_icon="🌙", layout="centered")
