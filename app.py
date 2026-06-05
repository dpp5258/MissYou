"""
MissYou — 思念量化系统
星空夜幕主题 | Google Sheets 数据 | Streamlit 部署
"""
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
    """连接并返回 Google Sheet"""
    pass

def read_account_state(sheet):
    """读取账户状态，返回 dict"""
    pass

def write_account_state(sheet, balance, daily_decay, last_update, start_date):
    """覆写账户状态工作表"""
    pass

def append_operation_log(sheet, op_type, change, balance_after, note=""):
    """追加一条操作记录"""
    pass

def read_operation_logs(sheet, limit=20):
    """读取最近 N 条操作记录，返回 list[dict]"""
    pass

# ============================================================
# 衰减逻辑（纯函数）
# ============================================================

def calc_decay(balance, daily_decay, last_update_date):
    """计算衰减后的余额和天数，返回 (new_balance, days_passed)"""
    pass

# ============================================================
# Streamlit 页面配置
# ============================================================
st.set_page_config(page_title="MissYou", page_icon="🌙", layout="centered")
