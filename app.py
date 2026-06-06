"""
MissYou — 思念量化系统
星空夜幕主题 | Google Sheets 数据 | Streamlit 部署
"""
import html

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date

# ============================================================
# Streamlit 页面配置 (必须是第一个 Streamlit 调用)
# ============================================================
st.set_page_config(page_title="MissYou", page_icon="🌙", layout="centered")

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
        creds_dict = dict(st.secrets["GOOGLE_CREDENTIALS"])
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
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
    """渲染用户思念展示页 — 星空主题、余额卡片、统计信息"""
    # ---------- 获取数据 ----------
    sheet = get_gsheet()
    state = read_account_state(sheet)
    balance = state["balance"]
    daily_decay = state["daily_decay"]
    last_update = state["last_update"]
    start_date = state["start_date"]

    # 先应用衰减
    if last_update and daily_decay > 0:
        new_balance, days_passed = calc_decay(balance, daily_decay, last_update)
        if days_passed > 0:
            write_account_state(
                sheet, new_balance, daily_decay,
                date.today().strftime("%Y-%m-%d"), start_date
            )
            append_operation_log(
                sheet, "自动衰减",
                f"-{daily_decay * days_passed}",
                new_balance,
                f"自动扣减 {days_passed} 天 × {daily_decay}/天"
            )
            balance = new_balance

    # Prevent negative balance display
    if balance < 0:
        balance = 0

    # 计算展示数据
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        total_days = (date.today() - start_dt.date()).days
    else:
        total_days = 0
    total_decayed = daily_decay * total_days if daily_decay > 0 else 0

    # ---------- CSS 星空主题 ----------
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(180deg, #0a0a2e 0%, #1a0a3e 40%, #0d1b3e 100%);
        animation: skyPulse 6s ease-in-out infinite alternate;
    }
    @keyframes skyPulse {
        0% { background: linear-gradient(180deg, #0a0a2e 0%, #1a0a3e 40%, #0d1b3e 100%); }
        100% { background: linear-gradient(180deg, #0f0f3e 0%, #200f4e 40%, #121f4e 100%); }
    }
    /* 星星闪烁 */
    @keyframes twinkle1 {
        0%,100% { opacity: 0.3; }
        50% { opacity: 1; }
    }
    @keyframes twinkle2 {
        0%,100% { opacity: 0.6; }
        33% { opacity: 0.1; }
        66% { opacity: 0.9; }
    }
    @keyframes twinkle3 {
        0%,100% { opacity: 0.8; }
        50% { opacity: 0.2; }
    }
    .stars {
        position: fixed;
        top: 0; left: 0;
        width: 100%; height: 100%;
        pointer-events: none;
        z-index: -1;
        font-size: 1.5rem;
        color: #ffd;
    }
    .star1 { animation: twinkle1 3s infinite; }
    .star2 { animation: twinkle2 4s infinite 0.5s; }
    .star3 { animation: twinkle3 3.5s infinite 1s; }
    .miss-days {
        text-align: center;
        color: #c8b8e8;
        font-size: 1.2rem;
        margin-top: 1rem;
    }
    .balance-card {
        background: rgba(20,15,50,0.6);
        border: 1px solid rgba(180,140,220,0.4);
        border-radius: 24px;
        padding: 2rem 1.5rem;
        text-align: center;
        margin: 1.5rem 0;
        box-shadow: 0 0 40px rgba(120,80,200,0.15);
    }
    .balance-number {
        font-size: 4.5rem;
        font-weight: bold;
        color: #f0e0ff;
        text-shadow: 0 0 30px rgba(200,150,255,0.7), 0 0 60px rgba(150,100,255,0.4);
        font-family: 'Georgia', serif;
        letter-spacing: 2px;
    }
    .balance-label {
        color: #b8a9d0;
        font-size: 0.95rem;
        margin-top: 0.3rem;
    }
    .stat-row {
        display: flex;
        justify-content: space-around;
        padding: 0.8rem 0;
        color: #c8c0e0;
    }
    .stat-item {
        text-align: center;
        flex: 1;
    }
    .stat-value {
        font-size: 1.2rem;
        font-weight: bold;
        color: #e0d5f0;
    }
    .stat-label {
        font-size: 0.75rem;
        color: #9080b0;
    }
    .theme-quote {
        text-align: center;
        color: #9070c0;
        font-style: italic;
        font-size: 1rem;
        margin-top: 1.5rem;
        padding: 1rem;
        border-top: 1px solid rgba(150,120,200,0.3);
        border-bottom: 1px solid rgba(150,120,200,0.3);
    }
    </style>
    """, unsafe_allow_html=True)

    # ---------- 星星装饰 ----------
    star_positions = [
        ('✦', 'star1', '10%', '8%'),
        ('✧', 'star2', '85%', '5%'),
        ('⋆', 'star1', '5%', '30%'),
        ('✦', 'star3', '90%', '25%'),
        ('✧', 'star2', '15%', '50%'),
        ('⋆', 'star3', '80%', '45%'),
        ('✦', 'star1', '25%', '70%'),
        ('✧', 'star3', '70%', '65%'),
        ('⋆', 'star2', '45%', '20%'),
        ('✦', 'star1', '55%', '55%'),
    ]
    stars_html = '<div class="stars">'
    for star, anim_class, left, top in star_positions:
        stars_html += f'<span class="{anim_class}" style="position:absolute;left:{left};top:{top};">{star}</span>'
    stars_html += '</div>'
    st.markdown(stars_html, unsafe_allow_html=True)

    # ---------- 内容区 ----------
    st.markdown(f'<p class="miss-days">💫 你被思念着的第 {total_days} 天</p>', unsafe_allow_html=True)

    # 思念值卡片
    if int(balance) <= 0:
        st.markdown(f'''
        <div class="balance-card">
            <p style="color:#b0a0d0;font-size:1rem;margin:0;">✨ 当前思念值</p>
            <p class="balance-number" style="font-size:2rem;">思念已耗尽</p>
            <p class="balance-label">思念如风，已散于时光</p>
        </div>
        ''', unsafe_allow_html=True)
    else:
        st.markdown(f'''
        <div class="balance-card">
            <p style="color:#b0a0d0;font-size:1rem;margin:0;">✨ 当前思念值</p>
            <p class="balance-number">{int(balance):,}</p>
            <p class="balance-label">思念如沙，随时间流逝</p>
        </div>
        ''', unsafe_allow_html=True)

    # 统计行
    st.markdown(f'''
    <div class="stat-row">
        <div class="stat-item">
            <div class="stat-value">📊 {int(daily_decay)}</div>
            <div class="stat-label">每日流逝</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">📅 {int(total_decayed):,}</div>
            <div class="stat-label">累计消散</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">🕐 {start_date}</div>
            <div class="stat-label">起始之日</div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    # 主题文案
    st.markdown(
        '<p class="theme-quote">🌙 "时光流转，思念不减"</p>',
        unsafe_allow_html=True
    )

    # 退出链接
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("🚪 退出", use_container_width=True, key="user_logout"):
            st.session_state.role = None
            st.rerun()


def render_admin_page():
    """渲染管理员后台 — 操作区、衰减调整、操作记录"""
    st.markdown("""
    <style>
    .admin-header {
        background: rgba(0,0,0,0.3);
        padding: 1rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 1rem;
    }
    .admin-section {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 1.2rem;
        margin: 1rem 0;
    }
    .log-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.8rem;
        color: #d0d0d0;
    }
    .log-table th {
        background: rgba(255,255,255,0.08);
        padding: 6px 8px;
        text-align: left;
        font-weight: bold;
        color: #c0b0e0;
    }
    .log-table td {
        padding: 5px 8px;
        border-bottom: 1px solid rgba(255,255,255,0.05);
    }
    .log-table tr:hover td {
        background: rgba(255,255,255,0.03);
    }
    </style>
    """, unsafe_allow_html=True)

    # ---------- 获取数据 ----------
    sheet = get_gsheet()
    state = read_account_state(sheet)
    balance = state["balance"]
    daily_decay = state["daily_decay"]
    last_update = state["last_update"]
    start_date = state["start_date"]

    # 应用衰减
    if last_update and daily_decay > 0:
        new_balance, days_passed = calc_decay(balance, daily_decay, last_update)
        if days_passed > 0:
            write_account_state(
                sheet, new_balance, daily_decay,
                date.today().strftime("%Y-%m-%d"), start_date
            )
            append_operation_log(
                sheet, "自动衰减",
                f"-{daily_decay * days_passed}",
                new_balance,
                f"自动扣减 {days_passed} 天"
            )
            balance = new_balance

    # 防止负余额
    if balance < 0:
        balance = 0

    # ---------- 页面标题 ----------
    st.markdown('<div class="admin-header">', unsafe_allow_html=True)
    st.markdown("## ⚙️ 管理员后台")
    st.markdown(f"当前余额：**{int(balance):,}** | 日衰减：**{int(daily_decay)}**")
    st.markdown('</div>', unsafe_allow_html=True)

    # ---------- 操作区 ----------
    with st.container():
        st.markdown('<div class="admin-section">', unsafe_allow_html=True)
        st.markdown("### 🎛️ 操作区")

        # 增加
        with st.expander("➕ 手动增加思念值", expanded=False):
            add_amount = st.number_input("增加数量", min_value=1, value=100, step=1, key="add_amt")
            add_note = st.text_input("备注", value="用户线下购买", key="add_note")
            if st.button("✅ 确认增加", key="add_btn"):
                new_bal = balance + add_amount
                write_account_state(
                    sheet, new_bal, daily_decay,
                    date.today().strftime("%Y-%m-%d"), start_date
                )
                append_operation_log(sheet, "手动增加", f"+{add_amount}", new_bal, add_note)
                st.success(f"已增加 {add_amount}，当前余额 {int(new_bal):,}")
                st.rerun()

        # 扣除
        with st.expander("➖ 手动扣除思念值", expanded=False):
            sub_amount = st.number_input("扣除数量", min_value=1, value=100, step=1, key="sub_amt")
            sub_note = st.text_input("备注", value="管理员手动调整", key="sub_note")
            if st.button("✅ 确认扣除", key="sub_btn"):
                new_bal = max(0, balance - sub_amount)
                write_account_state(
                    sheet, new_bal, daily_decay,
                    date.today().strftime("%Y-%m-%d"), start_date
                )
                append_operation_log(sheet, "手动扣除", f"-{sub_amount}", new_bal, sub_note)
                st.success(f"已扣除 {sub_amount}，当前余额 {int(new_bal):,}")
                st.rerun()

        # 调整衰减
        with st.expander("⚡ 调整每日衰减速度", expanded=False):
            new_decay = st.number_input(
                "每日衰减量", min_value=0, value=int(daily_decay), step=1, key="new_decay"
            )
            if st.button("✅ 确认调整", key="decay_btn"):
                write_account_state(
                    sheet, balance, new_decay,
                    date.today().strftime("%Y-%m-%d"), start_date
                )
                append_operation_log(
                    sheet, "调整衰减",
                    f"{int(daily_decay)}->{new_decay}",
                    balance,
                    f"衰减速度从 {int(daily_decay)} 调整为 {new_decay}"
                )
                st.success(f"每日衰减已调整为 {new_decay}")
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # ---------- 操作记录 ----------
    with st.container():
        st.markdown('<div class="admin-section">', unsafe_allow_html=True)
        st.markdown("### 📋 近期操作记录")

        logs = read_operation_logs(sheet, limit=20)

        if logs:
            table_html = """
            <table class="log-table">
            <tr><th>时间</th><th>类型</th><th>变化</th><th>余额</th><th>备注</th></tr>
            """
            for log in logs:
                table_html += (
                    f'<tr>'
                    f'<td>{html.escape(str(log["time"]))}</td>'
                    f'<td>{html.escape(str(log["op_type"]))}</td>'
                    f'<td>{html.escape(str(log["change"]))}</td>'
                    f'<td>{html.escape(str(log["balance_after"]))}</td>'
                    f'<td>{html.escape(str(log["note"]))}</td>'
                    f'</tr>'
                )
            table_html += "</table>"
            st.markdown(table_html, unsafe_allow_html=True)
        else:
            st.info("暂无操作记录")

        st.markdown('</div>', unsafe_allow_html=True)

    # ---------- 注销 ----------
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("🔒 注销登录", use_container_width=True, key="admin_logout"):
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
