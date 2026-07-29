"""
数字拼接运算挑战 — MissYou 游戏模块
每局 4 个随机数字 + 1 个目标数，用 +−×÷() 拼出算式
每个数字恰好使用一次，运算结果等于目标数即通关
"""
import random
import re
import hashlib
from itertools import permutations, product

import streamlit as st

# ============================================================
# 题目生成
# ============================================================

def make_question_id(nums: list[int], target: int) -> str:
    """生成题目 ID — 同数字组合 + 同目标 → 同 ID（7 天去重用）"""
    key = f"{'-'.join(map(str, sorted(nums)))}-{target}"
    return hashlib.md5(key.encode()).hexdigest()[:8]


def _eval_expr(expr: str):
    """安全求值算术表达式，返回数值或 None"""
    try:
        val = eval(expr, {"__builtins__": {}}, {})
        if isinstance(val, (int, float)) and abs(val - round(val)) < 1e-9:
            return round(val)
        return None
    except Exception:
        return None


def find_solutions(nums: list[int]) -> list[tuple[int, str]]:
    """
    枚举 4 个数字所有可达的正整数结果。
    返回 [(结果, 算式), ...]，去重（同一结果只保留一个算式作为标准答案）。
    """
    ops = ['+', '-', '*', '/']
    seen = set()
    solutions = []

    for a, b, c, d in permutations(nums):
        for op1, op2, op3 in product(ops, repeat=3):
            # 5 种括号结构，* / 用真实符号
            exprs = [
                f"(({a}{op1}{b}){op2}{c}){op3}{d}",
                f"({a}{op1}({b}{op2}{c})){op3}{d}",
                f"({a}{op1}{b}){op2}({c}{op3}{d})",
                f"{a}{op1}(({b}{op2}{c}){op3}{d})",
                f"{a}{op1}({b}{op2}({c}{op3}{d}))",
            ]
            for expr in exprs:
                val = _eval_expr(expr)
                if val is not None and val > 0 and val <= 100 and val not in seen:
                    seen.add(val)
                    # 转成用户友好显示（× ÷ 替代 * /）
                    pretty = expr.replace('*', '×').replace('/', '÷')
                    solutions.append((val, pretty))

    return solutions


def generate_question() -> dict:
    """
    生成一道题目。
    返回 {"nums": [4 ints], "target": int, "solutions": [str, ...]}
    """
    for _ in range(200):  # 最多尝试 200 次
        nums = [random.randint(1, 13) for _ in range(4)]
        all_solutions = find_solutions(nums)
        if all_solutions:
            # 随机选一个结果作为目标
            target, answer = random.choice(all_solutions)
            # 收集所有能算出该目标的算式
            target_solutions = [s for v, s in all_solutions if v == target]
            return {
                "nums": nums,
                "target": target,
                "solutions": target_solutions,
            }
    # 极端情况兜底：返回一道已知有解的题
    return {
        "nums": [3, 8, 3, 8],
        "target": 24,
        "solutions": ["8÷(3−8÷3)"],
    }


# ============================================================
# 答案验证（服务端安全执行）
# ============================================================

def validate_answer(question_data: dict, user_answer: str) -> bool:
    """
    验证用户答案。
    - 公式只能含数字/运算符/括号/空格
    - 数字必须与题目完全匹配（多集比较）
    - 计算结果必须等于目标数
    """
    nums = question_data.get("nums", [])
    target = question_data.get("target", 0)
    formula = user_answer.strip()

    if not formula:
        return False

    # 1. 安全过滤：只允许数字、四则符号、括号、小数点、空格
    #    − = 显示用的减号，× = ×，÷ = ÷
    if not re.match(r'^[\d\+\-\*\/\(\)\.\s×÷−]+$', formula):
        return False

    # 2. 提取所有整数（用于数字去重检查）
    formula_nums = [int(n) for n in re.findall(r'\d+', formula)]
    if sorted(formula_nums) != sorted(nums):
        return False

    # 3. 转成 Python 可执行的表达式
    py_expr = formula.replace('×', '*').replace('÷', '/').replace('−', '-').replace(' ', '')

    # 二次确认：转换后只含安全字符
    if not re.match(r'^[\d\+\-\*\/\(\)\.]+$', py_expr):
        return False

    # 4. 安全求值
    val = _eval_expr(py_expr)
    return val == target


# ============================================================
# Streamlit 渲染
# ============================================================

def _init_session():
    """初始化数字拼接游戏的 session state"""
    if "np_question" not in st.session_state:
        st.session_state.np_question = None
    if "np_tokens" not in st.session_state:
        st.session_state.np_tokens = []        # [(type, display, num_index)]
    if "np_used" not in st.session_state:
        st.session_state.np_used = [False, False, False, False]
    if "np_msg" not in st.session_state:
        st.session_state.np_msg = None         # ("success"|"error", text)


def _new_question():
    """生成新题，重置状态"""
    st.session_state.np_question = generate_question()
    st.session_state.np_tokens = []
    st.session_state.np_used = [False, False, False, False]
    st.session_state.np_msg = None


def _formula_display() -> str:
    """当前公式的展示字符串"""
    tokens = st.session_state.np_tokens
    if not tokens:
        return '<span style="color:#666;">点击数字和运算符开始拼算式</span>'
    return ''.join(t[1] for t in tokens)


def _formula_raw() -> str:
    """当前公式的实际字符串（用于验证提交）"""
    tokens = st.session_state.np_tokens
    return ''.join(t[1] for t in tokens)


def render_game(game_def, sheet):
    """渲染数字拼接游戏 UI"""
    _init_session()

    # 没有题目则生成
    if st.session_state.np_question is None:
        _new_question()

    q = st.session_state.np_question
    nums = q["nums"]
    target = q["target"]

    # ======== 目标数 ========
    st.markdown(f"""
    <div style="text-align:center;margin:0.5rem 0 1rem 0;">
        <span style="color:#b0a0d0;font-size:0.85rem;">🎯 目标数</span><br>
        <span style="font-size:3.5rem;font-weight:bold;color:#ff9944;
            text-shadow:0 0 20px rgba(255,153,68,0.4);line-height:1.2;">
            {target}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ======== 数字按钮 ========
    st.caption("🔢 可用数字 — 每个只能用一次")
    num_cols = st.columns(4)
    for i, n in enumerate(nums):
        with num_cols[i]:
            used = st.session_state.np_used[i]
            if st.button(
                str(n) if not used else "·",
                key=f"np_n{i}",
                disabled=used,
                use_container_width=True,
            ):
                st.session_state.np_tokens.append(("num", str(n), i))
                st.session_state.np_used[i] = True
                st.session_state.np_msg = None
                st.rerun()

    # ======== 运算符按钮 ========
    st.caption("➕ 运算符")
    op_labels = ['+', '−', '×', '÷', '(', ')']
    op_cols = st.columns(6)
    for i, label in enumerate(op_labels):
        with op_cols[i]:
            if st.button(label, key=f"np_op{i}", use_container_width=True):
                st.session_state.np_tokens.append(("op", label, -1))
                st.session_state.np_msg = None
                st.rerun()

    # ======== 公式展示区 ========
    st.markdown(f"""
    <div style="background:rgba(15,10,35,0.7);border:1px solid rgba(180,140,220,0.35);
        border-radius:12px;padding:1rem 0.8rem;text-align:center;margin:0.6rem 0;
        min-height:3.5rem;display:flex;align-items:center;justify-content:center;">
        <span style="font-size:1.4rem;color:#e0d5f0;font-family:'Courier New',monospace;
            letter-spacing:2px;word-break:break-all;">
            {_formula_display()}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ======== 反馈信息 ========
    if st.session_state.np_msg:
        mtype, mtext = st.session_state.np_msg
        if mtype == "success":
            st.success(mtext)
            st.balloons()
        else:
            st.error(mtext)

    # ======== 操作按钮行 ========
    btn_cols = st.columns([1, 1, 1, 1.3])
    with btn_cols[0]:
        if st.button("⌫ 退格", key="np_bs", use_container_width=True,
                     disabled=len(st.session_state.np_tokens) == 0):
            if st.session_state.np_tokens:
                last = st.session_state.np_tokens.pop()
                if last[0] == "num":
                    st.session_state.np_used[last[2]] = False
            st.session_state.np_msg = None
            st.rerun()

    with btn_cols[1]:
        if st.button("🔄 重置", key="np_reset", use_container_width=True,
                     disabled=len(st.session_state.np_tokens) == 0):
            st.session_state.np_tokens = []
            st.session_state.np_used = [False, False, False, False]
            st.session_state.np_msg = None
            st.rerun()

    with btn_cols[2]:
        if st.button("🎲 换一题", key="np_new", use_container_width=True):
            _new_question()
            st.rerun()

    with btn_cols[3]:
        if st.button("✅ 提交答案", key="np_submit", use_container_width=True,
                     type="primary",
                     disabled=len(st.session_state.np_tokens) == 0):
            raw = _formula_raw()
            # 懒加载避免循环导入
            from app import submit_game_score
            ok, msg, _ = submit_game_score(sheet, game_def, q, raw)
            if ok:
                st.session_state.np_msg = ("success", msg)
                _new_question()  # 答对自动换题
            else:
                st.session_state.np_msg = ("error", msg)
            st.rerun()

    # ======== 提示（折叠） ========
    with st.expander("💡 不会做？"):
        sols = q.get("solutions", [])
        if sols:
            st.info(f"试试这个：{sols[0]}")
            if len(sols) > 1:
                st.caption(f"(还有 {len(sols)-1} 种解法…)")
        else:
            st.caption("暂无提示")
