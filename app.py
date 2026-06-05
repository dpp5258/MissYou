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
# 密码验证（纯函数）
# ============================================================

def check_password(input_pwd, user_pwd, admin_pwd):
    """验证输入密码，返回 'user' / 'admin' / None"""
    if not input_pwd:
        return None
    if input_pwd == admin_pwd:
        return "admin"
    if input_pwd == user_pwd:
        return "user"
    return None


# ============================================================
# Streamlit 页面配置
# ============================================================
st.set_page_config(page_title="MissYou", page_icon="🌙", layout="centered")


# ============================================================
# Session State 与页面渲染
# ============================================================

def init_session():
    """初始化 session_state 默认值"""
    defaults = {
        "role": None,          # None=未登录, 'user'=用户, 'admin'=管理员
        "login_error": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def render_password_gate():
    """渲染密码门页面"""
    # ---------- 星空背景 CSS ----------
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(180deg, #0a0a2e 0%, #1a0a3e 40%, #0d1b3e 100%);
    }
    .title-missyou {
        text-align: center;
        font-size: 3rem;
        font-weight: bold;
        color: #e8d5f5;
        text-shadow: 0 0 20px rgba(180, 130, 220, 0.6);
    }
    .subtitle {
        text-align: center;
        color: #b8a9d0;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .password-box {
        background: rgba(255,255,255,0.05);
        border-radius: 16px;
        padding: 2rem;
        border: 1px solid rgba(180,130,220,0.3);
        max-width: 400px;
        margin: 0 auto;
    }
    </style>
    """, unsafe_allow_html=True)

    # ---------- 标题 ----------
    st.markdown('<p class="title-missyou">🌙 MissYou</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">每一份思念都值得被看见</p>', unsafe_allow_html=True)

    # ---------- 密码输入 ----------
    with st.container():
        st.markdown('<div class="password-box">', unsafe_allow_html=True)
        pwd = st.text_input("🔒 请输入查询密码", type="password", key="pwd_input")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            btn = st.button("确认查询", use_container_width=True)

        if btn:
            role = check_password(pwd, USER_PWD, ADMIN_PWD)
            if role:
                st.session_state.role = role
                st.session_state.login_error = False
                st.rerun()
            else:
                st.session_state.login_error = True

        if st.session_state.login_error:
            st.error("密码错误，无法查看")
        st.markdown('</div>', unsafe_allow_html=True)

    # 管理员入口提示
    st.markdown(
        '<p style="text-align:center;color:#555;font-size:0.75rem;margin-top:2rem;">'
        '管理员入口 ▼</p>',
        unsafe_allow_html=True
    )


def render_user_page():
    """用户思念展示页（占位）"""
    st.write("用户页面（待实现）")
    if st.button("退出"):
        st.session_state.role = None
        st.rerun()


def render_admin_page():
    """管理员后台（占位）"""
    st.write("管理员后台（待实现）")
    if st.button("注销登录"):
        st.session_state.role = None
        st.rerun()


def main():
    init_session()

    if st.session_state.role is None:
        render_password_gate()
    elif st.session_state.role == "user":
        render_user_page()
    elif st.session_state.role == "admin":
        render_admin_page()


if __name__ == "__main__":
    main()
