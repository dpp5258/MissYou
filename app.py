"""
MissYou — 思念量化系统
星空夜幕主题 | Google Sheets 数据 | Streamlit 部署
"""
import html

import streamlit as st
from datetime import datetime, date

import storage

# ============================================================
# Streamlit 页面配置 (必须是第一个 Streamlit 调用)
# ============================================================
st.set_page_config(page_title="MissYou", page_icon="🌙", layout="centered")

# ============================================================
# 配置区
# ============================================================
USER_PWD = st.secrets["USER_PWD"]
ADMIN_PWD = st.secrets["ADMIN_PWD"]
SHEET_ID = st.secrets["SHEET_ID"]

# ============================================================
# 存储初始化（app.py 启动时调用一次）
# ============================================================

def _init_storage():
    """初始化 Google Sheets 存储连接"""
    try:
        storage.init_store(
            dict(st.secrets["GOOGLE_CREDENTIALS"]),
            st.secrets["SHEET_ID"],
        )
        return True
    except Exception as e:
        st.error(f"无法连接数据库：{e}")
        st.stop()


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
    """渲染密码门页面 — 星空夜幕主题"""
    # ---------- 星空背景 + 全局样式 ----------
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&display=swap');

    * {
        font-family: 'Georgia', 'Noto Serif SC', 'Songti SC', serif;
    }

    .stApp {
        background: linear-gradient(180deg, #0a0a2e 0%, #1a0a3e 40%, #0d1b3e 100%);
    }

    /* ── 星星闪烁动画 ── */
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

    /* ── 标题：呼吸光晕 ── */
    .title-missyou {
        text-align: center;
        font-size: 3rem;
        font-weight: bold;
        color: #e8d5f5;
        animation: moonGlow 3s ease-in-out infinite alternate;
        margin-top: 1.5rem;
    }
    @keyframes moonGlow {
        0%   { text-shadow: 0 0 20px rgba(180,130,220,0.6); }
        100% { text-shadow: 0 0 40px rgba(200,160,240,0.9),
                            0 0 80px rgba(160,120,220,0.5); }
    }
    .subtitle {
        text-align: center;
        color: #b8a9d0;
        font-size: 1.1rem;
        margin-bottom: 2.5rem;
    }

    /* ── 密码卡片：毛玻璃 ── */
    .password-box {
        background: rgba(20,15,45,0.7);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border-radius: 20px;
        padding: 2.5rem 2rem;
        border: 1px solid rgba(180,130,220,0.35);
        box-shadow: 0 8px 32px rgba(0,0,0,0.4),
                    inset 0 1px 0 rgba(255,255,255,0.03);
        max-width: 400px;
        margin: 0 auto;
    }

    /* ── 输入框 ── */
    div[data-testid="stTextInput"] input {
        background: rgba(255,255,255,0.07) !important;
        border: 1px solid rgba(180,140,220,0.4) !important;
        border-radius: 10px !important;
        color: #e8d5f5 !important;
        font-size: 1.05rem !important;
        padding: 10px 14px !important;
    }
    div[data-testid="stTextInput"] input::placeholder {
        color: #6a5a8a !important;
    }
    div[data-testid="stTextInput"] label {
        color: #c0b0d8 !important;
        font-size: 0.95rem !important;
    }

    /* ── 按钮 ── */
    div[data-testid="stButton"] button {
        background: linear-gradient(135deg, rgba(140,100,200,0.5),
                                             rgba(100,60,180,0.5)) !important;
        border: 1px solid rgba(180,140,220,0.5) !important;
        border-radius: 12px !important;
        color: #f0e0ff !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 8px 0 !important;
        transition: all 0.2s !important;
    }
    div[data-testid="stButton"] button:hover {
        background: linear-gradient(135deg, rgba(160,120,220,0.6),
                                             rgba(120,80,200,0.6)) !important;
        box-shadow: 0 0 20px rgba(150,100,220,0.4) !important;
        transform: scale(1.02);
    }

    /* ── 管理员入口 ── */
    .admin-hint {
        text-align: center;
        color: #605080;
        font-size: 0.78rem;
        margin-top: 2.5rem;
        letter-spacing: 2px;
        transition: color 0.3s;
    }
    .admin-hint:hover {
        color: #9080b0;
    }
    </style>
    """, unsafe_allow_html=True)

    # ---------- 星星装饰 ----------
    star_positions = [
        ('✦', 'star1', '10%', '8%'),
        ('✧', 'star2', '88%', '6%'),
        ('⋆', 'star3', '5%', '32%'),
        ('✦', 'star1', '82%', '28%'),
        ('✧', 'star3', '20%', '55%'),
        ('✦', 'star2', '75%', '50%'),
    ]
    stars_html = '<div class="stars">'
    for star, anim_class, left, top in star_positions:
        stars_html += f'<span class="{anim_class}" style="position:absolute;left:{left};top:{top};">{star}</span>'
    stars_html += '</div>'
    st.markdown(stars_html, unsafe_allow_html=True)

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
        '<p class="admin-hint">管理员入口 ▼</p>',
        unsafe_allow_html=True
    )


def render_user_page():
    """渲染用户页 — 星空主题、余额卡片、记忆翻牌游戏"""
    # ---------- 获取数据 ----------
    store = storage.get_store()
    account = store.get_account()
    balance = account.balance
    daily_decay = account.daily_decay
    last_update = account.last_update
    start_date = account.start_date

    # 先应用衰减
    if last_update and daily_decay > 0:
        new_balance, days_passed = calc_decay(balance, daily_decay, last_update)
        if days_passed > 0:
            store.set_balance(
                new_balance, daily_decay,
                date.today().strftime("%Y-%m-%d"), start_date,
            )
            store.add_log(
                "自动衰减",
                f"-{daily_decay * days_passed}",
                new_balance,
                f"自动扣减 {days_passed} 天 × {daily_decay}/天",
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
    store = storage.get_store()
    account = store.get_account()
    balance = account.balance
    daily_decay = account.daily_decay
    last_update = account.last_update
    start_date = account.start_date

    # 应用衰减
    if last_update and daily_decay > 0:
        new_balance, days_passed = calc_decay(balance, daily_decay, last_update)
        if days_passed > 0:
            store.set_balance(
                new_balance, daily_decay,
                date.today().strftime("%Y-%m-%d"), start_date,
            )
            store.add_log(
                "自动衰减",
                f"-{daily_decay * days_passed}",
                new_balance,
                f"自动扣减 {days_passed} 天",
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
                store.set_balance(
                    new_bal, daily_decay,
                    date.today().strftime("%Y-%m-%d"), start_date,
                )
                store.add_log("手动增加", f"+{add_amount}", new_bal, add_note)
                st.success(f"已增加 {add_amount}，当前余额 {int(new_bal):,}")
                st.rerun()

        # 扣除
        with st.expander("➖ 手动扣除思念值", expanded=False):
            sub_amount = st.number_input("扣除数量", min_value=1, value=100, step=1, key="sub_amt")
            sub_note = st.text_input("备注", value="管理员手动调整", key="sub_note")
            if st.button("✅ 确认扣除", key="sub_btn"):
                new_bal = max(0, balance - sub_amount)
                store.set_balance(
                    new_bal, daily_decay,
                    date.today().strftime("%Y-%m-%d"), start_date,
                )
                store.add_log("手动扣除", f"-{sub_amount}", new_bal, sub_note)
                st.success(f"已扣除 {sub_amount}，当前余额 {int(new_bal):,}")
                st.rerun()

        # 调整衰减
        with st.expander("⚡ 调整每日衰减速度", expanded=False):
            new_decay = st.number_input(
                "每日衰减量", min_value=0, value=int(daily_decay), step=1, key="new_decay"
            )
            if st.button("✅ 确认调整", key="decay_btn"):
                store.set_balance(
                    balance, new_decay,
                    date.today().strftime("%Y-%m-%d"), start_date,
                )
                store.add_log(
                    "调整衰减",
                    f"{int(daily_decay)}->{new_decay}",
                    balance,
                    f"衰减速度从 {int(daily_decay)} 调整为 {new_decay}",
                )
                st.success(f"每日衰减已调整为 {new_decay}")
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # ---------- 操作记录 ----------
    with st.container():
        st.markdown('<div class="admin-section">', unsafe_allow_html=True)
        st.markdown("### 📋 近期操作记录")

        logs = store.get_logs(limit=20)

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
    _init_storage()

    if st.session_state.role is None:
        render_password_gate()
    elif st.session_state.role == "user":
        render_user_page()
    elif st.session_state.role == "admin":
        render_admin_page()


if __name__ == "__main__":
    main()
