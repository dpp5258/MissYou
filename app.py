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

    st.caption("管理员入口 ▼")


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

    # ── 内容区 ──
    st.markdown(f"💫 你被思念着的第 **{total_days}** 天")

    # 思念值
    if int(balance) <= 0:
        st.metric("✨ 当前思念值", "思念已耗尽")
    else:
        st.metric("✨ 当前思念值", f"{int(balance):,}")

    # 统计行
    c1, c2, c3 = st.columns(3)
    c1.metric("📊 每日流逝", f"{int(daily_decay)}")
    c2.metric("📅 累计消散", f"{int(total_decayed):,}")
    c3.metric("🕐 起始之日", start_date)

    st.divider()
    st.caption('"时光流转，思念不减"')

    # 退出
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("🚪 退出", use_container_width=True, key="user_logout"):
            st.session_state.role = None
            st.rerun()


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
    st.markdown(f"当前余额：**{int(balance):,}**　|　日衰减：**{int(daily_decay)}**")

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
    logs = store.get_logs(limit=20)

    if logs:
        table_data = []
        for log in logs:
            table_data.append({
                "时间": log["time"],
                "类型": log["op_type"],
                "变化": log["change"],
                "余额": log["balance_after"],
                "备注": log["note"],
            })
        st.dataframe(table_data, use_container_width=True, hide_index=True)
    else:
        st.info("暂无操作记录")

    # ── 注销 ──
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("🔒 注销登录", use_container_width=True, key="admin_logout"):
            st.session_state.role = None
            st.rerun()


# ============================================================
# 主入口
# ============================================================

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
