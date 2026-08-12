"""
MissYou — 思念量化系统
Google Sheets 数据 | Streamlit 部署
"""
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
# CSS 样式注入（全局 + 各页面样式）
# ============================================================

def inject_css():
    """注入所有自定义 CSS 样式 — 纯 CSS 方案，零额外依赖"""
    st.markdown("""
    <style>
    /* ================================================================
       全局：页面背景
       ================================================================ */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }

    /* 隐藏 Streamlit 默认页脚和 deploy 按钮 */
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    .appview-container .main .block-container {
        padding-top: 1.5rem;
    }

    /* 自定义滚动条 */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb {
        background: rgba(255,255,255,0.12);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }

    /* 链接 */
    a {
        color: #e2a654 !important;
        text-decoration: none;
        transition: color 0.2s ease;
    }
    a:hover { color: #f0d78c !important; }

    /* ================================================================
       全局：毛玻璃内容卡片
       ================================================================ */
    .main .block-container {
        background: rgba(255,255,255,0.06);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 20px;
        padding: 2.5rem 2rem !important;
        margin-top: 2rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        animation: fadeIn 0.6s ease;
    }

    /* ================================================================
       全局：标题 h1 — 渐变发光文字
       ================================================================ */
    h1 {
        font-size: 2.6rem !important;
        font-weight: 700 !important;
        text-align: center !important;
        background: linear-gradient(90deg, #e2a654, #f0d78c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: titleGlow 3s ease-in-out infinite;
    }

    @keyframes titleGlow {
        0%, 100% { filter: drop-shadow(0 0 6px rgba(226,166,84,0.4)); }
        50% { filter: drop-shadow(0 0 14px rgba(240,200,120,0.7)); }
    }

    /* ================================================================
       全局：副标题
       ================================================================ */
    .stCaption {
        text-align: center !important;
        color: #b0b0c8 !important;
        font-size: 1rem !important;
        animation: fadeInUp 1s ease 0.2s both;
    }

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    /* ================================================================
       全局：文本输入框
       ================================================================ */
    .stTextInput input {
        background: rgba(255,255,255,0.08) !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        border-radius: 12px !important;
        color: #e8e8e8 !important;
        padding: 0.7rem 1rem !important;
        font-size: 1rem !important;
        transition: all 0.3s ease;
    }
    .stTextInput input:focus {
        border-color: rgba(226,166,84,0.6) !important;
        box-shadow: 0 0 12px rgba(226,166,84,0.25) !important;
        outline: none !important;
    }
    .stTextInput label {
        color: #a0a0b8 !important;
        font-size: 0.85rem !important;
    }

    /* 数字输入框复用同样式 */
    .stNumberInput input {
        background: rgba(255,255,255,0.08) !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        border-radius: 12px !important;
        color: #e8e8e8 !important;
    }
    .stNumberInput label { color: #a0a0b8 !important; }

    /* ================================================================
       全局：主按钮（金色渐变）
       ================================================================ */
    .stButton > button {
        background: linear-gradient(135deg, #e2a654, #c8853c) !important;
        color: #1a1a2e !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.6rem 2rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(226,166,84,0.4) !important;
    }
    .stButton > button:active {
        transform: translateY(0);
    }

    /* 次要按钮（透明边框，用于退出/注销）*/
    button[kind="secondary"] {
        background: transparent !important;
        color: #a0a0b8 !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        box-shadow: none !important;
        width: 100% !important;
    }
    button[kind="secondary"]:hover {
        background: rgba(255,255,255,0.06) !important;
        color: #e8e8e8 !important;
        border-color: rgba(248,113,113,0.4) !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
    }

    /* ================================================================
       全局：Alert 消息
       ================================================================ */
    .stAlert {
        border-radius: 10px !important;
        animation: shake 0.4s ease;
    }

    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-6px); }
        75% { transform: translateX(6px); }
    }

    /* ================================================================
       全局：Expander 卡片化
       ================================================================ */
    .stExpander {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 14px !important;
        margin-bottom: 0.8rem !important;
        overflow: hidden;
        transition: all 0.3s ease;
    }
    .stExpander:hover {
        border-color: rgba(255,255,255,0.2) !important;
        background: rgba(255,255,255,0.06) !important;
    }
    .stExpander summary {
        font-weight: 600 !important;
        color: #d0d0e0 !important;
        padding: 0.5rem 0 !important;
    }

    /* ================================================================
       全局：Subheader
       ================================================================ */
    .stSubheader {
        color: #d0d0e0 !important;
        font-weight: 600 !important;
    }

    /* ================================================================
       登录页：管理员入口提示
       ================================================================ */
    .admin-hint {
        text-align: center;
        color: #6a6a8a;
        font-size: 0.8rem;
        margin-top: 1.5rem;
        transition: color 0.3s ease;
        cursor: default;
    }
    .admin-hint:hover { color: #a0a0c0; }

    /* ================================================================
       用户面板：思念天数横幅
       ================================================================ */
    .days-banner {
        text-align: center;
        padding: 0.8rem 0;
        animation: fadeInUp 0.8s ease;
    }
    .days-emoji { font-size: 1.8rem; vertical-align: middle; }
    .days-text { font-size: 1.1rem; color: #b0b0c8; vertical-align: middle; }
    .days-number {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(180deg, #f0d78c, #e2a654);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0 0.3rem;
        vertical-align: middle;
    }

    /* ================================================================
       用户面板：思念值大卡片
       ================================================================ */
    .balance-card {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(226,166,84,0.25);
        border-radius: 20px;
        padding: 1.5rem;
        text-align: center;
        margin: 1rem 0;
        backdrop-filter: blur(8px);
        position: relative;
    }
    .balance-card::before {
        content: "";
        position: absolute;
        inset: -1px;
        border-radius: 20px;
        padding: 1px;
        background: linear-gradient(135deg, rgba(226,166,84,0.3), transparent);
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask-composite: exclude;
    }
    .balance-label {
        font-size: 0.9rem;
        color: #a0a0b8;
        margin-bottom: 0.4rem;
        position: relative;
    }
    .balance-number {
        font-size: 3.2rem;
        font-weight: 800;
        background: linear-gradient(180deg, #f8e0a0, #e2a654);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: numberGlow 2.5s ease-in-out infinite;
        position: relative;
    }
    .balance-unit {
        font-size: 0.8rem;
        color: #6a6a8a;
        margin-top: 0.3rem;
        position: relative;
    }
    /* 耗尽状态 */
    .balance-card.depleted .balance-number {
        font-size: 1.6rem;
        background: linear-gradient(180deg, #a0a0b8, #6a6a8a);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: none;
    }
    .balance-hint {
        font-size: 0.85rem;
        color: #6a6a8a;
        margin-top: 0.5rem;
        position: relative;
    }

    @keyframes numberGlow {
        0%, 100% { filter: drop-shadow(0 0 4px rgba(226,166,84,0.3)); }
        50% { filter: drop-shadow(0 0 10px rgba(240,200,120,0.5)); }
    }

    /* ================================================================
       用户面板：统计小卡片
       ================================================================ */
    .stat-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 14px;
        padding: 1rem 0.5rem;
        text-align: center;
        transition: all 0.3s ease;
    }
    .stat-card:hover {
        background: rgba(255,255,255,0.09);
        transform: translateY(-3px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.2);
    }
    .stat-emoji { font-size: 1.5rem; margin-bottom: 0.3rem; }
    .stat-value {
        font-size: 1.3rem;
        font-weight: 700;
        color: #e8e8e8;
    }
    .stat-label {
        font-size: 0.75rem;
        color: #6a6a8a;
        margin-top: 0.2rem;
    }

    /* ================================================================
       用户面板：进度条
       ================================================================ */
    .progress-section { margin: 1rem 0; }
    .progress-header {
        display: flex;
        justify-content: space-between;
        color: #a0a0b8;
        font-size: 0.85rem;
        margin-bottom: 0.4rem;
    }
    .progress-bar {
        height: 8px;
        background: rgba(255,255,255,0.08);
        border-radius: 4px;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #e2a654, #f0d78c);
        border-radius: 4px;
        transition: width 0.8s ease;
    }

    /* ================================================================
       用户面板：引文
       ================================================================ */
    .quote-line {
        text-align: center;
        font-family: Georgia, "Times New Roman", serif;
        font-style: italic;
        color: #8070a0;
        font-size: 1rem;
        padding: 0.5rem 0;
        animation: fadeInUp 1s ease 0.5s both;
    }

    /* ================================================================
       管理后台：状态概览卡片
       ================================================================ */
    .admin-stat-card {
        background: rgba(255,255,255,0.05);
        border-left: 3px solid rgba(226,166,84,0.5);
        border-radius: 0 10px 10px 0;
        padding: 0.8rem 1rem;
        margin: 0.3rem 0;
    }
    .admin-stat-value {
        font-size: 1.4rem;
        font-weight: 700;
        color: #e8e8e8;
    }
    .admin-stat-label {
        font-size: 0.75rem;
        color: #6a6a8a;
        margin-top: 0.2rem;
    }

    /* ================================================================
       管理后台：操作日志表格
       ================================================================ */
    .log-table-wrap {
        max-height: 400px;
        overflow-y: auto;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.08);
    }
    .log-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
    }
    .log-table thead {
        position: sticky;
        top: 0;
        z-index: 1;
    }
    .log-table th {
        background: rgba(255,255,255,0.08);
        color: #a0a0b8;
        padding: 0.6rem 0.8rem;
        text-align: left;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .log-table td {
        padding: 0.55rem 0.8rem;
        color: #c8c8d8;
        border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    .log-table tbody tr { transition: background 0.2s ease; }
    .log-table tbody tr:hover { background: rgba(255,255,255,0.04); }
    .log-table tbody tr:nth-child(even) { background: rgba(255,255,255,0.02); }
    .log-table tbody tr:nth-child(even):hover { background: rgba(255,255,255,0.05); }

    /* 操作类型彩色标签 */
    .op-badge {
        display: inline-block;
        padding: 0.15rem 0.5rem;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 500;
    }
    .change-col { font-weight: 600; }
    .note-col {
        color: #8a8a9a;
        font-size: 0.8rem;
        max-width: 200px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    </style>
    """, unsafe_allow_html=True)


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
    返回: (new_balance, days_passed)
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
# Session State
# ============================================================

def init_session():
    """初始化 session_state 默认值"""
    defaults = {"role": None, "login_error": False}
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ============================================================
# 登录门
# ============================================================

def render_password_gate():
    st.title("🌙 MissYou")
    st.caption("每一份思念都值得被看见")

    pwd = st.text_input("请输入查询密码", type="password", key="pwd_input")

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

    st.markdown(
        '<p class="admin-hint">🔑 管理员请在此输入管理密码</p>',
        unsafe_allow_html=True,
    )


# ============================================================
# 用户面板
# ============================================================

def render_user_page():
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
                f"自动扣减 {days_passed} 天 × {daily_decay}/天",
            )
            balance = new_balance

    if balance < 0:
        balance = 0

    # 计算展示数据
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        total_days = (date.today() - start_dt.date()).days
    else:
        total_days = 0
    total_decayed = daily_decay * total_days if daily_decay > 0 else 0

    # ── 思念天数横幅 ──
    st.markdown(f"""
    <div class="days-banner">
        <span class="days-emoji">💫</span>
        <span class="days-text">你被思念着的第</span>
        <span class="days-number">{total_days}</span>
        <span class="days-text">天</span>
    </div>
    """, unsafe_allow_html=True)

    # ── 思念值大卡片 ──
    if int(balance) <= 0:
        st.markdown("""
        <div class="balance-card depleted">
            <div class="balance-label">✨ 当前思念值</div>
            <div class="balance-number">思念已耗尽</div>
            <div class="balance-hint">去创造新的思念吧</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="balance-card">
            <div class="balance-label">✨ 当前思念值</div>
            <div class="balance-number">{int(balance):,}</div>
            <div class="balance-unit">points</div>
        </div>
        """, unsafe_allow_html=True)

    # ── 统计三卡片 ──
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-emoji">📊</div>
            <div class="stat-value">{int(daily_decay)}</div>
            <div class="stat-label">每日流逝</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-emoji">📅</div>
            <div class="stat-value">{int(total_decayed):,}</div>
            <div class="stat-label">累计消散</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-emoji">🕐</div>
            <div class="stat-value">{start_date}</div>
            <div class="stat-label">起始之日</div>
        </div>
        """, unsafe_allow_html=True)

    # ── 思念剩余进度条 ──
    if total_decayed + balance > 0:
        remaining_pct = max(0, min(100, balance / (balance + total_decayed) * 100))
    else:
        remaining_pct = 0

    st.markdown(f"""
    <div class="progress-section">
        <div class="progress-header">
            <span>💖 思念剩余</span>
            <span>{remaining_pct:.0f}%</span>
        </div>
        <div class="progress-bar">
            <div class="progress-fill" style="width:{remaining_pct}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── 引文 ──
    st.markdown(
        '<p class="quote-line">" 时光流转，思念不减 "</p>',
        unsafe_allow_html=True,
    )

    # ── 退出 ──
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("🚪 退出", type="secondary", use_container_width=True, key="user_logout"):
            st.session_state.role = None
            st.rerun()


# ============================================================
# 管理后台 — 辅助函数
# ============================================================

def _op_type_badge(op_type: str) -> str:
    """根据操作类型返回彩色标签 HTML"""
    color_map = {
        "手动增加": "#4ade80",
        "手动扣除": "#f87171",
        "自动衰减": "#fbbf24",
        "调整衰减": "#60a5fa",
    }
    color = color_map.get(op_type, "#a0a0b8")
    return (
        f'<span class="op-badge"'
        f' style="background:{color}20;color:{color};border:1px solid {color}40;">'
        f'{op_type}</span>'
    )


# ============================================================
# 管理后台
# ============================================================

def render_admin_page():
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

    if balance < 0:
        balance = 0

    # ── 页面标题 ──
    st.title("⚙️ 管理员后台")

    # 状态概览三卡片
    all_logs = store.get_logs(limit=1000)
    total_ops = len(all_logs)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown(f"""
        <div class="admin-stat-card">
            <div class="admin-stat-value">{int(balance):,}</div>
            <div class="admin-stat-label">💰 当前余额</div>
        </div>
        """, unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""
        <div class="admin-stat-card">
            <div class="admin-stat-value">{int(daily_decay)}</div>
            <div class="admin-stat-label">📉 每日衰减</div>
        </div>
        """, unsafe_allow_html=True)
    with col_c:
        st.markdown(f"""
        <div class="admin-stat-card">
            <div class="admin-stat-value">{total_ops}</div>
            <div class="admin-stat-label">📋 累计操作</div>
        </div>
        """, unsafe_allow_html=True)

    # ── 操作区 ──
    st.subheader("🎛️ 操作区")

    with st.expander("➕ 手动增加思念值"):
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

    with st.expander("➖ 手动扣除思念值"):
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

    with st.expander("⚡ 调整每日衰减速度"):
        new_decay = st.number_input(
            "每日衰减量", min_value=0, value=int(daily_decay), step=1, key="new_decay"
        )
        if st.button("✅ 确认调整", key="decay_btn"):
            store.set_balance(
                balance, new_decay,
                date.today().strftime("%Y-%m-%d"), start_date,
            )
            store.add_log(
                "调整衰减", f"{int(daily_decay)}->{new_decay}",
                balance, f"衰减速度从 {int(daily_decay)} 调整为 {new_decay}",
            )
            st.success(f"每日衰减已调整为 {new_decay}")
            st.rerun()

    # ── 操作记录 ──
    st.subheader("📋 近期操作记录")
    display_logs = all_logs[:20]

    if display_logs:
        rows_html = ""
        for log in display_logs:
            badge = _op_type_badge(log["op_type"])
            rows_html += (
                "<tr>"
                f"<td>{log['time']}</td>"
                f"<td>{badge}</td>"
                f"<td class=\"change-col\">{log['change']}</td>"
                f"<td>{log['balance_after']}</td>"
                f"<td class=\"note-col\">{log['note']}</td>"
                "</tr>"
            )

        st.html(
            "<div class=\"log-table-wrap\">"
            "<table class=\"log-table\">"
            "<thead>"
            "<tr>"
            "<th>时间</th><th>类型</th><th>变化</th><th>余额</th><th>备注</th>"
            "</tr>"
            "</thead>"
            "<tbody>"
            + rows_html +
            "</tbody>"
            "</table>"
            "</div>"
        )
    else:
        st.info("暂无操作记录")

    # ── 注销 ──
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("🔒 注销登录", type="secondary", use_container_width=True, key="admin_logout"):
            st.session_state.role = None
            st.rerun()


# ============================================================
# 主入口
# ============================================================

def main():
    init_session()
    inject_css()
    _init_storage()

    if st.session_state.role is None:
        render_password_gate()
    elif st.session_state.role == "user":
        render_user_page()
    elif st.session_state.role == "admin":
        render_admin_page()


if __name__ == "__main__":
    main()
