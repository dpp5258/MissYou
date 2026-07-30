"""
数字拼接运算挑战 — MissYou 游戏模块
每局 4 个随机数字 + 1 个目标数，用 +−×÷() 拼出算式
每个数字恰好使用一次，运算结果等于目标数即通关

交互模式：前端 HTML/JS 处理所有点击（零延迟），仅提交和新题走后端
"""
import json
import random
import re
import hashlib
from itertools import permutations, product

import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# 题目生成（后端）
# ============================================================

def make_question_id(question_data: dict) -> str:
    """生成题目 ID — 同数字组合 + 同目标 → 同 ID（7 天去重用）"""
    nums = question_data.get("nums", [])
    target = question_data.get("target", 0)
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
    """枚举 4 个数字所有可达的正整数结果"""
    ops = ['+', '-', '*', '/']
    seen = set()
    solutions = []

    for a, b, c, d in permutations(nums):
        for op1, op2, op3 in product(ops, repeat=3):
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
                    pretty = expr.replace('*', '×').replace('/', '÷')
                    solutions.append((val, pretty))

    return solutions


def generate_question() -> dict:
    """生成一道题目，保证有解"""
    for _ in range(200):
        nums = [random.randint(1, 13) for _ in range(4)]
        all_solutions = find_solutions(nums)
        if all_solutions:
            target, _answer = random.choice(all_solutions)
            target_solutions = [s for v, s in all_solutions if v == target]
            return {"nums": nums, "target": target, "solutions": target_solutions}
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

    if not re.match(r'^[\d\+\-\*\/\(\)\.\s×÷−]+$', formula):
        return False

    formula_nums = [int(n) for n in re.findall(r'\d+', formula)]
    if sorted(formula_nums) != sorted(nums):
        return False

    py_expr = formula.replace('×', '*').replace('÷', '/').replace('−', '-').replace(' ', '')

    if not re.match(r'^[\d\+\-\*\/\(\)\.]+$', py_expr):
        return False

    val = _eval_expr(py_expr)
    return val == target


# ============================================================
# 前端 HTML 模板
# ============================================================

def _build_html(initial_data: dict) -> str:
    """构建包含完整游戏的 HTML 页面"""
    init_json = json.dumps(initial_data, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
    background: transparent;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    color: #e0d5f0;
    padding: 8px 4px;
    user-select: none;
    -webkit-user-select: none;
}}
.target-area {{ text-align:center; margin:0 0 10px 0; }}
.target-label {{ color:#b0a0d0; font-size:0.8rem; }}
.target-number {{
    font-size:3.2rem; font-weight:bold; color:#ff9944;
    text-shadow:0 0 20px rgba(255,153,68,0.4); line-height:1.15;
}}
.section-label {{ color:#9080b0; font-size:0.7rem; margin:8px 0 4px 0; }}
.btn-row {{ display:flex; gap:6px; margin:4px 0; }}
.btn {{
    flex:1; padding:10px 0; border:none; border-radius:10px;
    font-size:1.1rem; font-weight:600; cursor:pointer;
    transition: transform 0.1s, opacity 0.2s;
}}
.btn:active {{ transform:scale(0.93); }}
.btn-num {{
    background:rgba(255,255,255,0.1);
    color:#f0e0ff;
    border:1px solid rgba(180,140,220,0.4);
}}
.btn-num:active:not(:disabled) {{ background:rgba(180,140,220,0.35); }}
.btn-num:disabled {{ opacity:0.25; cursor:default; }}
.btn-op {{
    background:rgba(120,100,200,0.2);
    color:#d0c0f0;
    border:1px solid rgba(150,130,210,0.35);
    font-family:'Courier New',monospace;
}}
.btn-op:active {{ background:rgba(150,130,210,0.4); }}
.formula-box {{
    background:rgba(15,10,35,0.7);
    border:1px solid rgba(180,140,220,0.35);
    border-radius:12px; padding:12px; text-align:center;
    margin:8px 0; min-height:50px;
    display:flex; align-items:center; justify-content:center;
    word-break:break-all;
}}
.formula-text {{
    font-size:1.3rem; color:#e0d5f0;
    font-family:'Courier New',monospace; letter-spacing:2px;
}}
.formula-placeholder {{ color:#555; font-size:0.9rem; letter-spacing:0; }}
.btn-action {{
    flex:1; padding:9px 0; border:none; border-radius:10px;
    font-size:0.85rem; cursor:pointer;
    transition: transform 0.1s;
}}
.btn-action:active {{ transform:scale(0.93); }}
.btn-action:disabled {{ opacity:0.35; cursor:default; }}
.btn-bs {{ background:rgba(255,255,255,0.06); color:#c0b0d0; border:1px solid rgba(255,255,255,0.15); }}
.btn-reset {{ background:rgba(255,255,255,0.06); color:#c0b0d0; border:1px solid rgba(255,255,255,0.15); }}
.btn-new {{ background:rgba(255,200,100,0.12); color:#e0c080; border:1px solid rgba(255,200,100,0.3); }}
.btn-submit {{
    background:rgba(120,200,100,0.25); color:#a0e0a0;
    border:1px solid rgba(120,200,100,0.4); font-weight:700;
}}
.btn-submit:disabled {{ background:rgba(120,200,100,0.08); border-color:rgba(120,200,100,0.15); }}
.feedback {{ text-align:center; margin:6px 0; font-size:0.85rem; padding:6px; border-radius:8px; }}
.feedback-success {{ color:#a0e0a0; background:rgba(100,200,100,0.12); }}
.feedback-error {{ color:#e09090; background:rgba(200,100,100,0.12); }}
.hint-area {{ margin-top:8px; text-align:center; }}
.btn-hint {{ background:none; border:1px solid rgba(180,140,220,0.25); color:#9080b0; border-radius:8px; padding:6px 16px; font-size:0.8rem; cursor:pointer; }}
.hint-text {{ display:none; margin-top:6px; font-size:0.85rem; color:#c0a0d0; }}
</style>
</head>
<body>
<div id="app"></div>
<script>
// ── 状态 ──
let nums = [], target = 0, solutions = [];
let tokens = [], used = [false,false,false,false];

// ── 操作符映射 ──
const OP_LABELS = ['+', '−', '×', '÷', '(', ')'];

// ── 从 Streamlit 接收数据 ──
function onData(data) {{
    if (!data) return;
    nums = data.nums || [];
    target = data.target || 0;
    solutions = data.solutions || [];

    if (data.saved_tokens && data.saved_tokens.length > 0) {{
        tokens = data.saved_tokens;
        used = data.saved_used || new Array(4).fill(false);
    }} else if (data.reset !== false) {{
        tokens = [];
        used = [false,false,false,false];
    }}

    render();
    if (data.feedback) {{
        showFeedback(data.feedback[0], data.feedback[1]);
    }}
}}

// ── 渲染 ──
function render() {{
    const usedCount = used.filter(u => u).length;
    const hasTokens = tokens.length > 0;
    const formulaDisplay = tokens.length > 0
        ? tokens.map(t => t.display).join('')
        : '<span class="formula-placeholder">点击数字和运算符开始拼算式</span>';

    document.getElementById('app').innerHTML = `
        <div class="target-area">
            <div class="target-label">🎯 目标数</div>
            <div class="target-number">${{target}}</div>
        </div>

        <div class="section-label">🔢 可用数字 — 每个只能用一次</div>
        <div class="btn-row">
            ${{nums.map((n,i) => `
                <button class="btn btn-num" id="num${{i}}"
                    ${{used[i] ? 'disabled' : ''}}
                    onclick="clickNumber(${{i}})">
                    ${{used[i] ? '·' : n}}
                </button>`).join('')}}
        </div>

        <div class="section-label">➕ 运算符</div>
        <div class="btn-row">
            ${{OP_LABELS.map((op,i) => `
                <button class="btn btn-op" onclick="clickOp('${{op}}')">${{op}}</button>`).join('')}}
        </div>

        <div class="formula-box">
            <span class="formula-text">${{formulaDisplay}}</span>
        </div>

        <div id="feedback"></div>

        <div class="btn-row">
            <button class="btn-action btn-bs" ${{hasTokens ? '' : 'disabled'}}
                onclick="backspace()">⌫ 退格</button>
            <button class="btn-action btn-reset" ${{hasTokens ? '' : 'disabled'}}
                onclick="resetAll()">🔄 重置</button>
            <button class="btn-action btn-new"
                onclick="newQuestion()">🎲 换一题</button>
            <button class="btn-action btn-submit" ${{hasTokens && usedCount===4 ? '' : 'disabled'}}
                onclick="submitAnswer()">✅ 提交</button>
        </div>

        <div class="hint-area">
            <button class="btn-hint" onclick="toggleHint()">💡 不会做？</button>
            <div class="hint-text" id="hint">${{solutions.length > 0 ? '试试这个：' + solutions[0] : ''}}</div>
        </div>
    `;
}}

// ── 交互 ──
function clickNumber(i) {{
    if (used[i]) return;
    tokens.push({{type:'num', display:String(nums[i]), index:i}});
    used[i] = true;
    render();
}}

function clickOp(op) {{
    tokens.push({{type:'op', display:op, index:-1}});
    render();
}}

function backspace() {{
    if (tokens.length === 0) return;
    const last = tokens.pop();
    if (last.type === 'num') used[last.index] = false;
    render();
}}

function resetAll() {{
    tokens = [];
    used = [false,false,false,false];
    render();
}}

function submitAnswer() {{
    const formula = tokens.map(t => t.display).join('');
    const data = {{
        action: 'submit',
        formula: formula,
        nums: nums,
        target: target,
        tokens: tokens,
        used: used
    }};
    window.parent.postMessage({{isStreamlitMessage: true, type: 'streamlit:setComponentValue', data: data}}, '*');
}}

function newQuestion() {{
    window.parent.postMessage({{isStreamlitMessage: true, type: 'streamlit:setComponentValue', data: {{action:'new_question'}}}}, '*');
}}

function showFeedback(type, text) {{
    const fb = document.getElementById('feedback');
    if (fb) {{
        fb.className = 'feedback feedback-' + type;
        fb.textContent = text;
    }}
}}

function toggleHint() {{
    const h = document.getElementById('hint');
    if (h) h.style.display = h.style.display === 'block' ? 'none' : 'block';
}}

// ── 启动 ──
const DATA = {init_json};
onData(DATA);
</script>
</body>
</html>"""


# ============================================================
# Session State 与渲染
# ============================================================

def _init_session():
    """初始化数字拼接游戏的 session state"""
    if "np_question" not in st.session_state:
        st.session_state.np_question = None
    if "np_tokens" not in st.session_state:
        st.session_state.np_tokens = []
    if "np_used" not in st.session_state:
        st.session_state.np_used = [False, False, False, False]
    if "np_msg" not in st.session_state:
        st.session_state.np_msg = None  # ("success"|"error", text)


def _new_question():
    """生成新题，重置状态"""
    st.session_state.np_question = generate_question()
    st.session_state.np_tokens = []
    st.session_state.np_used = [False, False, False, False]
    st.session_state.np_msg = None


def render_game(game_def):
    """渲染数字拼接游戏 — 前端 HTML 处理交互，仅提交时走后端"""
    _init_session()

    if st.session_state.np_question is None:
        _new_question()

    q = st.session_state.np_question

    # 构建传给前端的初始数据
    initial_data = {
        "nums": q["nums"],
        "target": q["target"],
        "solutions": q["solutions"],
        "feedback": st.session_state.np_msg,
        "saved_tokens": st.session_state.np_tokens,
        "saved_used": st.session_state.np_used,
        "reset": False,
    }

    # 渲染嵌入式组件
    result = components.html(_build_html(initial_data), height=460, scrolling=False)

    # 处理前端回传（防御：确保 result 是 dict 类型）
    if result and isinstance(result, dict):
        action = result.get("action")

        if action == "submit":
            formula = result.get("formula", "")
            # 保存前端状态（提交失败时可以恢复）
            st.session_state.np_tokens = result.get("tokens", [])
            st.session_state.np_used = result.get("used", [False]*4)

            from storage import get_store
            store = get_store()
            result_obj = store.submit_game_score(game_def, q, formula)

            if result_obj.success:
                st.session_state.np_msg = ("success", result_obj.message)
                _new_question()
            else:
                st.session_state.np_msg = ("error", result_obj.message)

        elif action == "new_question":
            _new_question()

        st.rerun()
