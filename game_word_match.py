"""
英语单词匹配游戏 — MissYou 游戏模块
左侧英文单词，右侧中文释义，点击配对，全部匹配成功即通关

交互模式：前端 HTML/JS 处理所有点击和匹配判断，
仅完成时自动提交走后端验证加分
"""
import json
import random
import hashlib

import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# 词库
# ============================================================

WORD_BANK = {
    "easy": [
        ("apple", "苹果"), ("book", "书"), ("cat", "猫"),
        ("dog", "狗"), ("egg", "鸡蛋"), ("fish", "鱼"),
        ("girl", "女孩"), ("house", "房子"), ("ice", "冰"),
        ("jump", "跳"), ("king", "国王"), ("love", "爱"),
        ("moon", "月亮"), ("night", "夜晚"), ("orange", "橙子"),
        ("pen", "笔"), ("queen", "女王"), ("rain", "雨"),
        ("sun", "太阳"), ("tree", "树"), ("umbrella", "雨伞"),
        ("water", "水"), ("box", "盒子"), ("star", "星星"),
        ("bird", "鸟"), ("cake", "蛋糕"), ("door", "门"),
        ("eye", "眼睛"), ("fire", "火"), ("grass", "草"),
        ("hat", "帽子"), ("island", "岛"),
    ],
    "hard": [
        ("adventure", "冒险"), ("brilliant", "杰出的"),
        ("curious", "好奇的"), ("demonstrate", "展示"),
        ("enormous", "巨大的"), ("frequent", "频繁的"),
        ("generous", "慷慨的"), ("hesitate", "犹豫"),
        ("imagine", "想象"), ("journey", "旅程"),
        ("knowledge", "知识"), ("landscape", "风景"),
        ("mysterious", "神秘的"), ("necessary", "必要的"),
        ("opportunity", "机会"), ("patient", "耐心的"),
        ("quality", "质量"), ("recognize", "识别"),
        ("scientific", "科学的"), ("temperature", "温度"),
        ("universe", "宇宙"), ("volunteer", "志愿者"),
        ("weather", "天气"), ("ancient", "古老的"),
        ("benefit", "利益"), ("challenge", "挑战"),
        ("discover", "发现"), ("evidence", "证据"),
        ("familiar", "熟悉的"), ("harmony", "和谐"),
        ("influence", "影响"), ("strategy", "策略"),
    ],
}


# ============================================================
# 题目生成（后端）
# ============================================================

def make_question_id(question_data: dict) -> str:
    """同词对集合 → 同 ID（7 天去重用）"""
    pairs = question_data.get("pairs", [])
    flat = sorted(f"{en}|{zh}" for en, zh in pairs)
    key = "|".join(flat)
    return hashlib.md5(key.encode()).hexdigest()[:8]


def generate_question() -> dict:
    """从词库随机抽 8-12 对，打乱显示顺序"""
    difficulty = random.choice(["easy", "hard"])
    pool = WORD_BANK[difficulty]
    count = random.randint(8, min(12, len(pool)))
    pairs = random.sample(pool, count)

    # 打乱英文和中文的显示顺序（独立打乱）
    en_display = [p[0] for p in pairs]
    zh_display = [p[1] for p in pairs]
    random.shuffle(en_display)
    random.shuffle(zh_display)

    return {
        "pairs": pairs,
        "en_display": en_display,
        "zh_display": zh_display,
        "difficulty": difficulty,
        "count": count,
    }


def validate_answer(question_data: dict, user_answer) -> bool:
    """
    验证所有匹配都正确 — 前端已做匹配判断，后端二次核对防篡改
    """
    if not isinstance(user_answer, dict):
        return False

    expected = set((en, zh) for en, zh in question_data.get("pairs", []))
    user_matches = user_answer.get("matches", [])
    if not isinstance(user_matches, list) or len(user_matches) != len(expected):
        return False

    actual = set()
    for m in user_matches:
        if isinstance(m, (list, tuple)) and len(m) == 2:
            actual.add((m[0], m[1]))

    return expected == actual


# ============================================================
# 前端 HTML 模板
# ============================================================

def _build_html(initial_data: dict) -> str:
    """构建完整的单词匹配 HTML/JS — DOM 操作模式，按钮状态实时响应"""
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
    margin-bottom:10px; font-size:0.85rem; color:#b0a0d0;
}
.stats-bar .good { color:#a0e0a0; font-weight:bold; }
.stats-bar .bad { color:#e09090; font-weight:bold; }
.diff-badge {
    display:inline-block; padding:2px 10px; border-radius:10px;
    font-size:0.7rem; font-weight:bold;
}
.diff-easy { background:rgba(100,200,100,0.2); color:#a0e0a0; }
.diff-hard { background:rgba(200,150,100,0.2); color:#e0c080; }
.columns {
    display:flex; gap:10px; margin:0 0 10px 0;
}
.col {
    flex:1;
    display:flex; flex-direction:column; gap:5px;
}
.col-label {
    text-align:center; font-size:0.75rem; color:#9080b0;
    margin-bottom:2px;
}
.word-btn {
    width:100%; padding:9px 8px; border:none; border-radius:8px;
    font-size:0.9rem; cursor:pointer; text-align:center;
    transition:transform 0.1s, opacity 0.2s, background 0.15s, box-shadow 0.15s;
    background:rgba(255,255,255,0.08);
    color:#d0c0e0;
    border:1px solid rgba(180,140,220,0.3);
}
.word-btn:active { transform:scale(0.95); }
.word-btn.selected {
    background:rgba(180,140,220,0.3);
    border-color:rgba(200,160,240,0.7);
    box-shadow:0 0 8px rgba(180,140,220,0.3);
    color:#fff;
}
.word-btn.matched {
    opacity:0.25;
    pointer-events:none;
    text-decoration:line-through;
}
.word-btn:disabled { pointer-events:none; }
.btn-row { display:flex; gap:8px; }
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
// ── 状态 ──
var pairs = [];
var enDisplay = [];
var zhDisplay = [];
var difficulty = '';
var matchedEn = new Set();
var matchedZh = new Set();
var selectedEn = null;
var errorCount = 0;
var gameOver = false;

// ── 一次性创建棋盘 ──
function buildBoard() {
    var diffCls = difficulty === 'easy' ? 'diff-easy' : 'diff-hard';
    var diffLabel = difficulty === 'easy' ? '初级' : '中级';

    var enBtnsHtml = '';
    for (var i = 0; i < enDisplay.length; i++) {
        var w = enDisplay[i];
        enBtnsHtml += '<button class="word-btn" data-en="' + w.replace(/"/g, '&quot;') + '">' + w + '</button>';
    }

    var zhBtnsHtml = '';
    for (var i = 0; i < zhDisplay.length; i++) {
        var w = zhDisplay[i];
        zhBtnsHtml += '<button class="word-btn" data-zh="' + w.replace(/"/g, '&quot;') + '">' + w + '</button>';
    }

    document.getElementById('app').innerHTML =
        '<div class="stats-bar">' +
        '<span>📚 <span class="' + diffCls + '" style="display:inline-block;padding:2px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">' + diffLabel + '</span></span>' +
        '<div>✅ <span class="good" id="match-count">0</span>/<span id="total-count">' + pairs.length + '</span></div>' +
        '<div>❌ <span class="bad" id="error-count">0</span> 次错误</div>' +
        '</div>' +
        '<div class="columns">' +
        '<div class="col"><div class="col-label">🔤 English</div><div id="en-col">' + enBtnsHtml + '</div></div>' +
        '<div class="col"><div class="col-label">🀄 中文</div><div id="zh-col">' + zhBtnsHtml + '</div></div>' +
        '</div>' +
        '<div id="feedback"></div>' +
        '<div class="btn-row">' +
        '<button class="btn" id="btn-reset">🔄 重来本局</button>' +
        '<button class="btn btn-new" id="btn-new">🎲 换一题</button>' +
        '</div>';

    // 绑定英文按钮
    var enBtns = document.querySelectorAll('#en-col .word-btn');
    for (var i = 0; i < enBtns.length; i++) {
        (function(btn) {
            btn.addEventListener('click', function() {
                if (gameOver) return;
                var w = btn.getAttribute('data-en');
                if (w && !matchedEn.has(w)) clickEn(w);
            });
        })(enBtns[i]);
    }

    // 绑定中文按钮
    var zhBtns = document.querySelectorAll('#zh-col .word-btn');
    for (var i = 0; i < zhBtns.length; i++) {
        (function(btn) {
            btn.addEventListener('click', function() {
                if (gameOver || !selectedEn) return;
                var w = btn.getAttribute('data-zh');
                if (w && !matchedZh.has(w)) clickZh(w);
            });
        })(zhBtns[i]);
    }

    // 绑定操作按钮
    document.getElementById('btn-reset').addEventListener('click', resetGame);
    document.getElementById('btn-new').addEventListener('click', newQuestion);
}

// ── 刷新 UI（只改 class，保留 DOM → CSS transition 正常）──
function refreshUI() {
    // 统计
    var mc = document.getElementById('match-count');
    if (mc) mc.textContent = matchedEn.size;
    var ec = document.getElementById('error-count');
    if (ec) ec.textContent = errorCount;

    // 英文按钮
    var enBtns = document.querySelectorAll('#en-col .word-btn');
    for (var i = 0; i < enBtns.length; i++) {
        var btn = enBtns[i];
        var w = btn.getAttribute('data-en');
        btn.className = 'word-btn';
        if (matchedEn.has(w)) {
            btn.classList.add('matched');
            btn.disabled = true;
        } else if (selectedEn === w) {
            btn.classList.add('selected');
            btn.disabled = false;
        } else if (gameOver) {
            btn.disabled = true;
        } else {
            btn.disabled = false;
        }
    }

    // 中文按钮
    var zhBtns = document.querySelectorAll('#zh-col .word-btn');
    for (var i = 0; i < zhBtns.length; i++) {
        var btn = zhBtns[i];
        var w = btn.getAttribute('data-zh');
        btn.className = 'word-btn';
        if (matchedZh.has(w)) {
            btn.classList.add('matched');
            btn.disabled = true;
        } else if (!selectedEn || gameOver) {
            btn.disabled = true;
        } else {
            btn.disabled = false;
        }
    }
}

// ── 接收 Streamlit 数据 ──
function onData(data) {
    if (!data) return;
    pairs = data.pairs || [];
    enDisplay = data.en_display || [];
    zhDisplay = data.zh_display || [];
    difficulty = data.difficulty || 'easy';

    matchedEn = new Set();
    matchedZh = new Set();
    selectedEn = null;
    errorCount = 0;
    gameOver = false;

    buildBoard();
    if (data.feedback) {
        showFeedback(data.feedback[0], data.feedback[1]);
    }
}

// ── 判断配对是否正确 ──
function isCorrectPair(en, zh) {
    for (var i = 0; i < pairs.length; i++) {
        if (pairs[i][0] === en && pairs[i][1] === zh) return true;
    }
    return false;
}

// ── 交互 ──
function clickEn(word) {
    if (gameOver || matchedEn.has(word)) return;
    selectedEn = word;
    refreshUI();
}

function clickZh(word) {
    if (gameOver || matchedZh.has(word) || !selectedEn) return;

    if (isCorrectPair(selectedEn, word)) {
        matchedEn.add(selectedEn);
        matchedZh.add(word);
        selectedEn = null;
        refreshUI();

        if (matchedEn.size === pairs.length) {
            gameOver = true;
            setTimeout(function() { submitResult(); }, 400);
        }
    } else {
        errorCount++;
        selectedEn = null;
        refreshUI();
    }
}

// ── 提交 / 换题 / 重来 ──
function submitResult() {
    var matchList = [];
    for (var i = 0; i < pairs.length; i++) {
        matchList.push([pairs[i][0], pairs[i][1]]);
    }
    window.parent.postMessage({
        isStreamlitMessage: true,
        type: 'streamlit:setComponentValue',
        data: {
            action: 'submit',
            matches: matchList,
            errors: errorCount
        }
    }, '*');
}

function newQuestion() {
    window.parent.postMessage({
        isStreamlitMessage: true,
        type: 'streamlit:setComponentValue',
        data: { action: 'new_question' }
    }, '*');
}

function resetGame() {
    matchedEn = new Set();
    matchedZh = new Set();
    selectedEn = null;
    errorCount = 0;
    gameOver = false;
    refreshUI();
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

def _init_session():
    """初始化单词匹配的 session state"""
    if "wm_question" not in st.session_state:
        st.session_state.wm_question = None
    if "wm_msg" not in st.session_state:
        st.session_state.wm_msg = None


def _new_question():
    """生成新题，重置状态"""
    st.session_state.wm_question = generate_question()
    st.session_state.wm_msg = None


def render_game(game_def):
    """渲染单词匹配游戏 — 前端 HTML 处理交互，完成时自动提交"""
    _init_session()

    if st.session_state.wm_question is None:
        _new_question()

    q = st.session_state.wm_question

    initial_data = {
        "pairs": q["pairs"],
        "en_display": q["en_display"],
        "zh_display": q["zh_display"],
        "difficulty": q["difficulty"],
        "count": q["count"],
        "feedback": st.session_state.wm_msg,
    }

    result = components.html(_build_html(initial_data), height=560, scrolling=False)

    if result and isinstance(result, dict):
        action = result.get("action")

        if action == "submit":
            user_answer = {
                "matches": result.get("matches", []),
                "errors": result.get("errors", 0),
            }

            from storage import get_store
            from game_engine import calc_game_score
            store = get_store()
            result_obj = store.submit_game_score(
                game_def, q, user_answer, calc_game_score,
            )

            if result_obj.success:
                st.session_state.wm_msg = ("success", result_obj.message)
                _new_question()
            else:
                st.session_state.wm_msg = ("error", result_obj.message)

        elif action == "new_question":
            _new_question()

        st.rerun()
