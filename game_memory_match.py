"""
记忆翻牌游戏 — MissYou 游戏模块
翻开卡牌找到配对，全部配对成功即通关

交互模式：前端 HTML/JS 处理所有点击、翻牌动画、计时，
仅完成时自动提交走后端验证加分
"""
import json
import random
import hashlib

import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# 题目生成（后端）
# ============================================================

def make_question_id(question_data: dict) -> str:
    """同 seed + 同布局 → 同 ID（7 天去重用）"""
    seed = question_data.get("seed", 0)
    cols = question_data.get("cols", 0)
    rows = question_data.get("rows", 0)
    key = f"mm-{seed}-{cols}x{rows}"
    return hashlib.md5(key.encode()).hexdigest()[:8]


EMOJIS = [
    "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼",
    "🐨", "🐯", "🦁", "🐮", "🐷", "🐸", "🐵", "🐔",
    "🍎", "🍊", "🍋", "🍇", "🌟", "⭐", "🌈", "❤️",
    "🎵", "🎸", "🚀", "⚽", "🏀", "🎯", "🔥", "💎",
]


def generate_question() -> dict:
    """随机生成卡牌布局：保证有偶数张、随机排列"""
    # 简单 4×3=12张(6对) / 困难 4×4=16张(8对)
    layouts = [(4, 3), (4, 4)]
    cols, rows = random.choice(layouts)
    pair_count = (cols * rows) // 2

    chosen = random.sample(EMOJIS, pair_count)
    cards = chosen * 2
    random.shuffle(cards)

    return {
        "cards": cards,
        "cols": cols,
        "rows": rows,
        "pair_count": pair_count,
        "seed": random.randint(0, 10**9),
    }


def validate_answer(question_data: dict, user_answer) -> bool:
    """
    验证完成合理性（防篡改）：
    - 翻牌次数在合理范围（最少 pair_count*2，最多 pair_count*10）
    - 用时在合理范围（1s ~ 10min）
    """
    if not isinstance(user_answer, dict):
        return False

    pair_count = question_data.get("pair_count", 0)
    total_flips = user_answer.get("total_flips", 0)
    time_seconds = user_answer.get("time_seconds", 0)

    if total_flips < pair_count * 2 or total_flips > pair_count * 10:
        return False
    if time_seconds < 1 or time_seconds > 600:
        return False

    return True


# ============================================================
# 前端 HTML 模板
# ============================================================

def _build_html(initial_data: dict) -> str:
    """构建完整的记忆翻牌 HTML/JS"""
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
.stats-bar {{
    display:flex; justify-content:center; gap:24px;
    margin-bottom:10px; font-size:0.9rem; color:#b0a0d0;
}}
.stats-bar span {{ color:#e0c080; font-weight:bold; }}
.card-grid {{
    display:grid; gap:8px; margin:0 auto;
    max-width:360px;
}}
.card {{
    aspect-ratio:1;
    perspective:600px;
    cursor:pointer;
    -webkit-tap-highlight-color:transparent;
}}
.card-inner {{
    position:relative; width:100%; height:100%;
    transition:transform 0.4s ease;
    transform-style:preserve-3d;
}}
.card.flipped .card-inner,
.card.matched .card-inner {{
    transform:rotateY(180deg);
}}
.card-face {{
    position:absolute; width:100%; height:100%;
    backface-visibility:hidden;
    border-radius:10px;
    display:flex; align-items:center; justify-content:center;
}}
.card-front {{
    background:rgba(255,255,255,0.08);
    border:1px solid rgba(180,140,220,0.4);
    color:#9080b0; font-size:1.4rem; font-weight:bold;
}}
.card-front:hover {{ background:rgba(255,255,255,0.14); }}
.card-back {{
    transform:rotateY(180deg);
    background:rgba(120,100,200,0.2);
    border:1px solid rgba(150,130,210,0.5);
    font-size:1.8rem;
}}
.card.matched .card-back {{
    background:rgba(100,200,100,0.18);
    border-color:rgba(100,200,100,0.5);
}}
.card.matched {{ cursor:default; }}
.btn-row {{ display:flex; gap:8px; margin:12px 0 0 0; }}
.btn {{
    flex:1; padding:9px 0; border:none; border-radius:10px;
    font-size:0.85rem; cursor:pointer;
    transition:transform 0.1s;
    background:rgba(255,255,255,0.06);
    color:#c0b0d0;
    border:1px solid rgba(255,255,255,0.15);
}}
.btn:active {{ transform:scale(0.93); }}
.btn-new {{
    background:rgba(255,200,100,0.12);
    color:#e0c080;
    border:1px solid rgba(255,200,100,0.3);
}}
.feedback {{
    text-align:center; margin:6px 0; font-size:0.85rem; padding:6px; border-radius:8px;
}}
.feedback-success {{ color:#a0e0a0; background:rgba(100,200,100,0.12); }}
.feedback-error {{ color:#e09090; background:rgba(200,100,100,0.12); }}
</style>
</head>
<body>
<div id="app"></div>
<script>
// ── 状态 ──
let cards = [], cols = 4, rows = 3, pairCount = 0;
let flipped = [], matched = new Set();
let flipCount = 0, timerStart = null, timerInterval = null;
let locked = false, gameOver = false;

// ── 接收 Streamlit 数据 ──
function onData(data) {{
    if (!data) return;
    cards = data.cards || [];
    cols = data.cols || 4;
    rows = data.rows || 3;
    pairCount = data.pair_count || (cards.length / 2);

    flipped = [];
    matched = new Set();
    flipCount = 0;
    timerStart = null;
    locked = false;
    gameOver = false;
    if (timerInterval) {{ clearInterval(timerInterval); timerInterval = null; }}

    render();
    if (data.feedback) {{
        showFeedback(data.feedback[0], data.feedback[1]);
    }}
}}

// ── 计时器 ──
function startTimer() {{
    if (timerStart) return;
    timerStart = Date.now();
    timerInterval = setInterval(() => {{
        renderStats();
    }}, 300);
}}

function stopTimer() {{
    if (timerInterval) {{ clearInterval(timerInterval); timerInterval = null; }}
}}

function elapsed() {{
    if (!timerStart) return 0;
    return Math.floor((Date.now() - timerStart) / 1000);
}}

function fmtTime(s) {{
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return String(m).padStart(2,'0') + ':' + String(sec).padStart(2,'0');
}}

// ── 渲染 ──
function renderStats() {{
    document.getElementById('flip-count').textContent = flipCount;
    document.getElementById('time-display').textContent = fmtTime(elapsed());
}}

function render() {{
    const total = cards.length;
    const matchedCount = matched.size;

    let gridStyle = 'grid-template-columns:repeat(' + cols + ',1fr);';
    let cardsHtml = '';
    for (let i = 0; i < total; i++) {{
        let stateClass = '';
        if (matched.has(i)) {{
            stateClass = 'matched';
        }} else if (flipped.includes(i)) {{
            stateClass = 'flipped';
        }}
        let faceContent = (stateClass === '' ? '?' : cards[i]);
        let clickable = (stateClass === '' && !locked && !gameOver) ? 'onclick="flipCard(' + i + ')"' : '';
        cardsHtml += `
            <div class="card ${{stateClass}}" ${{clickable}}>
                <div class="card-inner">
                    <div class="card-face card-front">?</div>
                    <div class="card-face card-back">${{cards[i]}}</div>
                </div>
            </div>`;
    }}

    document.getElementById('app').innerHTML = `
        <div class="stats-bar">
            <div>翻牌 <span id="flip-count">0</span> 次</div>
            <div>⏱ <span id="time-display">00:00</span></div>
            <div>配对 <span id="match-count">${{matchedCount}}</span>/${{pairCount}}</div>
        </div>
        <div class="card-grid" style="${{gridStyle}}">${{cardsHtml}}</div>
        <div id="feedback"></div>
        <div class="btn-row">
            <button class="btn" onclick="resetGame()">🔄 重来本局</button>
            <button class="btn btn-new" onclick="newQuestion()">🎲 换一题</button>
        </div>
    `;

    if (data.feedback) {{
        showFeedback(data.feedback[0], data.feedback[1]);
    }}
}}

// ── 翻牌逻辑 ──
function flipCard(i) {{
    if (locked || gameOver || flipped.includes(i) || matched.has(i)) return;
    if (flipped.length >= 2) return;

    startTimer();
    flipped.push(i);
    flipCount++;
    render();

    if (flipped.length === 2) {{
        const [a, b] = flipped;
        if (cards[a] === cards[b]) {{
            // 配对成功
            matched.add(a);
            matched.add(b);
            flipped = [];
            render();
            // 检查是否全部完成
            if (matched.size === cards.length) {{
                gameOver = true;
                stopTimer();
                setTimeout(() => submitResult(), 600);
            }}
        }} else {{
            // 配对失败，延迟翻回
            locked = true;
            setTimeout(() => {{
                flipped = [];
                locked = false;
                render();
            }}, 800);
        }}
    }}
}}

// ── 提交结果 ──
function submitResult() {{
    window.parent.postMessage({{
        isStreamlitMessage: true,
        type: 'streamlit:setComponentValue',
        data: {{
            action: 'submit',
            total_flips: flipCount,
            time_seconds: elapsed()
        }}
    }}, '*');
}}

function newQuestion() {{
    stopTimer();
    window.parent.postMessage({{
        isStreamlitMessage: true,
        type: 'streamlit:setComponentValue',
        data: {{ action: 'new_question' }}
    }}, '*');
}}

function resetGame() {{
    stopTimer();
    flipped = [];
    matched = new Set();
    flipCount = 0;
    timerStart = null;
    locked = false;
    gameOver = false;
    if (timerInterval) {{ clearInterval(timerInterval); timerInterval = null; }}
    render();
}}

function showFeedback(type, text) {{
    const fb = document.getElementById('feedback');
    if (fb) {{
        fb.className = 'feedback feedback-' + type;
        fb.textContent = text;
    }}
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
    """初始化记忆翻牌的 session state"""
    if "mm_question" not in st.session_state:
        st.session_state.mm_question = None
    if "mm_msg" not in st.session_state:
        st.session_state.mm_msg = None


def _new_question():
    """生成新题，重置状态"""
    st.session_state.mm_question = generate_question()
    st.session_state.mm_msg = None


def render_game(game_def, sheet):
    """渲染记忆翻牌游戏 — 前端 HTML 处理交互，完成时自动提交"""
    _init_session()

    if st.session_state.mm_question is None:
        _new_question()

    q = st.session_state.mm_question

    initial_data = {
        "cards": q["cards"],
        "cols": q["cols"],
        "rows": q["rows"],
        "pair_count": q["pair_count"],
        "feedback": st.session_state.mm_msg,
    }

    result = components.html(_build_html(initial_data), height=520, scrolling=False)

    if result and isinstance(result, dict):
        action = result.get("action")

        if action == "submit":
            user_answer = {
                "total_flips": result.get("total_flips", 0),
                "time_seconds": result.get("time_seconds", 0),
            }

            from app import submit_game_score
            ok, msg, _ = submit_game_score(sheet, game_def, q, user_answer)

            st.session_state.mm_msg = ("success" if ok else "error", msg)
            _new_question()
            st.rerun()

        elif action == "new_question":
            _new_question()
            st.rerun()
