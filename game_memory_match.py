"""
记忆翻牌游戏 — MissYou 游戏模块
翻开卡牌找到配对，全部配对成功即通关

交互模式：前端 HTML/JS 处理所有点击、翻牌动画、计时
换一题：预生成题目池，JS 本地切换
提交：完成时 JS 通过父窗口 URL 参数传递数据，Python 服务端验证
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
    """构建完整的记忆翻牌 HTML/JS — DOM 操作模式，CSS 动画正常"""
    init_json = json.dumps(initial_data, ensure_ascii=False)

    return """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body {
    background: transparent;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    color: #e0d5f0;
    padding: 8px 4px;
    user-select: none;
    -webkit-user-select: none;
}
.stats-bar {
    display:flex; justify-content:center; gap:24px;
    margin-bottom:10px; font-size:0.9rem; color:#b0a0d0;
}
.stats-bar span { color:#e0c080; font-weight:bold; }
.card-grid {
    display:grid; gap:8px; margin:0 auto;
    max-width:360px;
}
.card {
    aspect-ratio:1;
    perspective:600px;
    cursor:pointer;
    -webkit-tap-highlight-color:transparent;
}
.card-inner {
    position:relative; width:100%; height:100%;
    transition:transform 0.4s ease;
    transform-style:preserve-3d;
}
.card.flipped .card-inner,
.card.matched .card-inner {
    transform:rotateY(180deg);
}
.card-face {
    position:absolute; width:100%; height:100%;
    backface-visibility:hidden;
    border-radius:10px;
    display:flex; align-items:center; justify-content:center;
}
.card-front {
    background:rgba(255,255,255,0.08);
    border:1px solid rgba(180,140,220,0.4);
    color:#9080b0; font-size:1.4rem; font-weight:bold;
}
.card-front:hover { background:rgba(255,255,255,0.14); }
.card-back {
    transform:rotateY(180deg);
    background:rgba(120,100,200,0.2);
    border:1px solid rgba(150,130,210,0.5);
    font-size:1.8rem;
}
.card.matched .card-back {
    background:rgba(100,200,100,0.18);
    border-color:rgba(100,200,100,0.5);
}
.card.matched { cursor:default; }
.btn-row { display:flex; gap:8px; margin:12px 0 0 0; }
.btn {
    flex:1; padding:9px 0; border:none; border-radius:10px;
    font-size:0.85rem; cursor:pointer;
    transition:transform 0.1s;
    background:rgba(255,255,255,0.06);
    color:#c0b0d0;
    border:1px solid rgba(255,255,255,0.15);
}
.btn:active { transform:scale(0.93); }
.btn-new {
    background:rgba(255,200,100,0.12);
    color:#e0c080;
    border:1px solid rgba(255,200,100,0.3);
}
.feedback {
    text-align:center; margin:6px 0; font-size:0.85rem; padding:6px; border-radius:8px;
}
.feedback-success { color:#a0e0a0; background:rgba(100,200,100,0.12); }
.feedback-error { color:#e09090; background:rgba(200,100,100,0.12); }
</style>
</head>
<body>
<div id="app"></div>
<script>
// ── 题目池 ──
var questionPool = [];
var currentQIndex = 0;
var cards = [], cols = 4, rows = 3, pairCount = 0;
var flipped = [], matched = new Set();
var flipCount = 0, timerStart = null, timerInterval = null;
var locked = false, gameOver = false;

// ── 加载指定题目 ──
function loadQuestion(idx) {
    if (idx < 0 || idx >= questionPool.length) return;
    currentQIndex = idx;
    var q = questionPool[idx];
    cards = q.cards || [];
    cols = q.cols || 4;
    rows = q.rows || 3;
    pairCount = q.pair_count || (cards.length / 2);

    flipped = [];
    matched = new Set();
    flipCount = 0;
    timerStart = null;
    locked = false;
    gameOver = false;
    if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }

    buildBoard();
}

// ── 一次性创建棋盘 ──
function buildBoard() {
    var gridStyle = 'grid-template-columns:repeat(' + cols + ',1fr);';
    var cardsHtml = '';
    for (var i = 0; i < cards.length; i++) {
        cardsHtml += '<div class="card" data-idx="' + i + '">' +
            '<div class="card-inner">' +
            '<div class="card-face card-front">?</div>' +
            '<div class="card-face card-back">' + cards[i] + '</div>' +
            '</div></div>';
    }
    document.getElementById('app').innerHTML =
        '<div class="stats-bar">' +
        '<div>翻牌 <span id="flip-count">0</span> 次</div>' +
        '<div>⏱ <span id="time-display">00:00</span></div>' +
        '<div>配对 <span id="match-count">0</span>/<span id="pair-total">' + pairCount + '</span></div>' +
        '</div>' +
        '<div class="card-grid" id="card-grid" style="' + gridStyle + '">' + cardsHtml + '</div>' +
        '<div id="feedback"></div>' +
        '<div class="btn-row">' +
        '<button class="btn" id="btn-reset">🔄 重来本局</button>' +
        '<button class="btn btn-new" id="btn-new">🎲 换一题</button>' +
        '</div>';

    // 绑定卡牌点击事件
    var grid = document.getElementById('card-grid');
    var children = grid.children;
    for (var i = 0; i < children.length; i++) {
        children[i].addEventListener('click', (function(idx) {
            return function() { flipCard(idx); };
        })(i));
    }

    // 绑定按钮事件
    document.getElementById('btn-reset').addEventListener('click', resetGame);
    document.getElementById('btn-new').addEventListener('click', newQuestion);
}

// ── 刷新 UI ──
function refreshUI() {
    var grid = document.getElementById('card-grid');
    if (!grid) return;
    var children = grid.children;
    for (var i = 0; i < children.length; i++) {
        var card = children[i];
        card.className = 'card';
        if (matched.has(i)) {
            card.classList.add('matched');
        } else if (flipped.indexOf(i) !== -1) {
            card.classList.add('flipped');
        }
    }
    var fc = document.getElementById('flip-count');
    if (fc) fc.textContent = flipCount;
    var td = document.getElementById('time-display');
    if (td) td.textContent = fmtTime(elapsed());
    var mc = document.getElementById('match-count');
    if (mc) mc.textContent = matched.size;
}

// ── 接收 Streamlit 数据 ──
function onData(data) {
    if (!data) return;
    questionPool = data.questions || [];
    currentQIndex = data.current_index || 0;

    loadQuestion(currentQIndex);

    if (data.feedback) {
        showFeedback(data.feedback[0], data.feedback[1]);
    }
}

// ── 计时器 ──
function startTimer() {
    if (timerStart) return;
    timerStart = Date.now();
    timerInterval = setInterval(function() {
        var td = document.getElementById('time-display');
        if (td) td.textContent = fmtTime(elapsed());
    }, 300);
}

function stopTimer() {
    if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }
}

function elapsed() {
    if (!timerStart) return 0;
    return Math.floor((Date.now() - timerStart) / 1000);
}

function fmtTime(s) {
    var m = Math.floor(s / 60);
    var sec = s % 60;
    return String(m).padStart(2,'0') + ':' + String(sec).padStart(2,'0');
}

// ── 翻牌逻辑 ──
function flipCard(i) {
    if (locked || gameOver || flipped.indexOf(i) !== -1 || matched.has(i)) return;
    if (flipped.length >= 2) return;

    startTimer();
    flipped.push(i);
    flipCount++;
    refreshUI();

    if (flipped.length === 2) {
        var a = flipped[0], b = flipped[1];
        if (cards[a] === cards[b]) {
            matched.add(a);
            matched.add(b);
            flipped = [];
            refreshUI();
            if (matched.size === cards.length) {
                gameOver = true;
                stopTimer();
                setTimeout(function() { submitResult(); }, 600);
            }
        } else {
            locked = true;
            setTimeout(function() {
                flipped = [];
                locked = false;
                refreshUI();
            }, 800);
        }
    }
}

// ── 换一题：题目池本地循环 ──
function newQuestion() {
    stopTimer();
    currentQIndex = (currentQIndex + 1) % questionPool.length;
    loadQuestion(currentQIndex);
}

function resetGame() {
    stopTimer();
    flipped = [];
    matched = new Set();
    flipCount = 0;
    timerStart = null;
    locked = false;
    gameOver = false;
    if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }
    refreshUI();
}

// ── 提交：通过父窗口 URL 参数传递数据 ──
function submitResult() {
    var q = questionPool[currentQIndex];
    var data = {
        action: 'submit',
        game: 'mm',
        total_flips: flipCount,
        time_seconds: elapsed(),
        q_index: currentQIndex,
        nonce: Math.random().toString(36).substr(2, 8)
    };
    var encoded = encodeURIComponent(JSON.stringify(data));
    window.parent.location.href = window.parent.location.href.split('?')[0] + '?ma=' + encoded;
}

function showFeedback(type, text) {
    var fb = document.getElementById('feedback');
    if (fb) {
        fb.className = 'feedback feedback-' + type;
        fb.textContent = text;
    }
}

// ── 启动 ──
var DATA = __INIT_JSON__;
onData(DATA);
</script>
</body>
</html>""".replace('__INIT_JSON__', init_json)


# ============================================================
# Session State 与渲染
# ============================================================

POOL_SIZE = 10  # 预生成题目数量


def _init_session():
    """初始化记忆翻牌的 session state"""
    if "mm_pool" not in st.session_state:
        st.session_state.mm_pool = []
    if "mm_pool_idx" not in st.session_state:
        st.session_state.mm_pool_idx = 0
    if "mm_msg" not in st.session_state:
        st.session_state.mm_msg = None
    if "mm_processed_nonce" not in st.session_state:
        st.session_state.mm_processed_nonce = set()


def _ensure_pool():
    """确保题目池有题"""
    if not st.session_state.mm_pool or st.session_state.mm_pool_idx >= len(st.session_state.mm_pool):
        st.session_state.mm_pool = [generate_question() for _ in range(POOL_SIZE)]
        st.session_state.mm_pool_idx = 0


def _new_question():
    """换一题：移动到池中下一题"""
    st.session_state.mm_pool_idx += 1


def render_game(game_def):
    """渲染记忆翻牌游戏"""
    _init_session()

    # ── 处理 URL Query Param 提交 ──
    if "ma" in st.query_params:
        try:
            raw = st.query_params["ma"]
            data = json.loads(raw)
            if data.get("game") == "mm" and data.get("action") == "submit":
                nonce = data.get("nonce", "")
                if nonce and nonce not in st.session_state.mm_processed_nonce:
                    st.session_state.mm_processed_nonce.add(nonce)
                    if len(st.session_state.mm_processed_nonce) > 20:
                        st.session_state.mm_processed_nonce = set(
                            list(st.session_state.mm_processed_nonce)[-20:]
                        )

                    user_answer = {
                        "total_flips": data.get("total_flips", 0),
                        "time_seconds": data.get("time_seconds", 0),
                    }

                    # 从池中获取当前题目的数据用于验证
                    _ensure_pool()
                    pool = st.session_state.mm_pool
                    idx = data.get("q_index", st.session_state.mm_pool_idx)
                    if idx < len(pool):
                        q = pool[idx]
                    else:
                        q = pool[st.session_state.mm_pool_idx]

                    from storage import get_store
                    from game_engine import calc_game_score
                    store = get_store()
                    result_obj = store.submit_game_score(
                        game_def, q, user_answer, calc_game_score,
                    )

                    if result_obj.success:
                        _new_question()
                        st.session_state.mm_msg = ("success", result_obj.message)
                    else:
                        st.session_state.mm_msg = ("error", result_obj.message)
        except Exception:
            pass
        try:
            del st.query_params["ma"]
        except Exception:
            pass

    # ── 确保题目池有题 ──
    _ensure_pool()

    pool = st.session_state.mm_pool
    idx = st.session_state.mm_pool_idx
    q = pool[idx]

    # ── 构建前端数据 ──
    initial_data = {
        "questions": pool,
        "current_index": idx,
        "feedback": st.session_state.mm_msg,
    }

    # ── 渲染组件 ──
    components.html(_build_html(initial_data), height=520, scrolling=False)
