"""
英语单词匹配游戏 — MissYou 游戏模块
左侧英文单词，右侧中文释义，点击配对，全部匹配成功即通关

交互模式：前端 HTML/JS 处理所有点击和匹配判断
换一题：预生成题目池，JS 本地切换
提交：完成时 JS 通过父窗口 URL 参数传递数据，Python 服务端验证
"""
import json
import random
import hashlib

import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# 词库（大学生六级词汇）
# ============================================================

WORD_BANK = {
    "easy": [
        ("abandon", "放弃"), ("absorb", "吸收"),
        ("abundant", "丰富的"), ("abuse", "滥用"),
        ("accommodate", "容纳"), ("accomplish", "完成"),
        ("accumulate", "积累"), ("accurate", "精确的"),
        ("acknowledge", "承认"), ("acquire", "获得"),
        ("adequate", "充足的"), ("administer", "管理"),
        ("advocate", "提倡"), ("aggressive", "进取的"),
        ("allocate", "分配"), ("alternative", "替代的"),
        ("ambiguous", "模棱两可的"), ("ambitious", "有雄心的"),
        ("anticipate", "预期"), ("apparent", "明显的"),
        ("appreciate", "欣赏"), ("approach", "方法"),
        ("appropriate", "适当的"), ("approve", "批准"),
        ("artificial", "人造的"), ("assemble", "组装"),
        ("assess", "评估"), ("assign", "分配"),
        ("associate", "联系"), ("assume", "假设"),
        ("attain", "达到"), ("attribute", "归因于"),
        ("authority", "权威"), ("autonomous", "自治的"),
        ("barrier", "障碍"), ("bonus", "奖金"),
        ("budget", "预算"), ("capable", "有能力的"),
        ("capacity", "能力"), ("category", "类别"),
        ("cease", "停止"), ("circumstance", "环境"),
        ("collapse", "崩溃"), ("commence", "开始"),
        ("commitment", "承诺"), ("commodity", "商品"),
        ("compensate", "补偿"), ("competent", "胜任的"),
        ("comply", "遵守"), ("component", "组成部分"),
        ("comprehensive", "全面的"), ("comprise", "包含"),
        ("conceive", "构想"), ("concentrate", "集中"),
        ("confine", "限制"), ("confirm", "确认"),
        ("consent", "同意"), ("consequence", "后果"),
        ("conservative", "保守的"), ("considerable", "相当大的"),
        ("consistent", "一致的"), ("constant", "持续的"),
        ("constitute", "构成"), ("consult", "咨询"),
        ("contemporary", "当代的"), ("contribute", "贡献"),
        ("controversy", "争议"), ("convenient", "方便的"),
        ("conventional", "传统的"), ("convert", "转换"),
        ("convince", "说服"), ("cooperate", "合作"),
        ("coordinate", "协调"), ("core", "核心"),
    ],
    "hard": [
        ("deteriorate", "恶化"), ("dilemma", "困境"),
        ("diminish", "减少"), ("discriminate", "歧视"),
        ("disperse", "分散"), ("displace", "取代"),
        ("dispose", "处理"), ("dissolve", "溶解"),
        ("distinct", "明显的"), ("distort", "扭曲"),
        ("distribute", "分配"), ("diverse", "多样的"),
        ("domestic", "国内的"), ("dominate", "主导"),
        ("drastic", "激烈的"), ("elaborate", "精心制作的"),
        ("elevate", "提升"), ("eliminate", "消除"),
        ("embrace", "拥抱"), ("emerge", "出现"),
        ("emphasize", "强调"), ("empirical", "经验主义的"),
        ("encounter", "遭遇"), ("endeavor", "努力"),
        ("enforce", "强制执行"), ("enhance", "增强"),
        ("enormous", "巨大的"), ("enrich", "充实"),
        ("ensure", "确保"), ("enthusiasm", "热情"),
        ("equivalent", "等价的"), ("erode", "侵蚀"),
        ("essence", "本质"), ("establish", "建立"),
        ("estate", "房地产"), ("evaluate", "评估"),
        ("evolve", "进化"), ("exaggerate", "夸大"),
        ("exceed", "超过"), ("excessive", "过度的"),
        ("exclude", "排除"), ("exclusive", "独有的"),
        ("execute", "执行"), ("exert", "施加"),
        ("expand", "扩张"), ("expel", "驱逐"),
        ("explicit", "明确的"), ("exploit", "开发"),
        ("extensive", "广泛的"), ("external", "外部的"),
        ("extinct", "灭绝的"), ("extract", "提取"),
        ("extraordinary", "非凡的"), ("facilitate", "促进"),
        ("faculty", "才能"), ("feasible", "可行的"),
        ("flourish", "繁荣"), ("fluctuate", "波动"),
        ("formulate", "制定"), ("frustrate", "挫败"),
        ("fundamental", "基本的"), ("generate", "产生"),
        ("genuine", "真正的"), ("guarantee", "保证"),
        ("hinder", "阻碍"), ("hypothesis", "假说"),
        ("identical", "相同的"), ("ignite", "点燃"),
        ("illuminate", "照亮"), ("illustrate", "说明"),
        ("implement", "实施"), ("implicit", "含蓄的"),
        ("impose", "强加"), ("impulse", "冲动"),
        ("incentive", "激励"), ("incident", "事件"),
        ("incorporate", "合并"), ("indispensable", "不可或缺的"),
        ("inferior", "劣等的"), ("inhabit", "居住于"),
        ("inherit", "继承"), ("initiate", "发起"),
        ("innovation", "创新"), ("insight", "洞察力"),
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
    """构建完整的单词匹配 HTML/JS — DOM 操作模式"""
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
/* ── 结算浮层 ── */
.settlement-overlay { position:fixed; top:0;left:0;width:100%;height:100%;
  background:rgba(5,3,20,.85); display:flex; align-items:center;
  justify-content:center; z-index:1000;
  backdrop-filter:blur(6px); -webkit-backdrop-filter:blur(6px);
  animation:fadeIn .35s; }
@keyframes fadeIn { from{opacity:0} to{opacity:1} }
.settlement-card { background:linear-gradient(145deg,rgba(30,20,60,.95),rgba(15,10,40,.95));
  border:1px solid rgba(180,140,220,.5); border-radius:20px;
  padding:28px 24px 20px; text-align:center; max-width:340px; width:90%;
  box-shadow:0 0 40px rgba(120,80,200,.3),0 0 80px rgba(150,100,255,.15);
  animation:cardPop .4s cubic-bezier(.175,.885,.32,1.275); }
@keyframes cardPop { from{transform:scale(.85);opacity:0} to{transform:scale(1);opacity:1} }
.settlement-title { font-size:1.5rem; font-weight:bold; color:#f0e0ff; margin-bottom:4px; }
.settlement-score { font-size:2.8rem; font-weight:bold; color:#ff9944; margin:8px 0 2px;
  text-shadow:0 0 20px rgba(255,153,68,.5); font-family:Georgia,serif; }
.settlement-score-label { font-size:.85rem; color:#b0a0d0; margin-bottom:14px; }
.settlement-stats { display:flex; justify-content:center; gap:18px; margin:12px 0 16px; flex-wrap:wrap; }
.settlement-stat { text-align:center; min-width:60px; }
.settlement-stat-val { font-size:1.1rem; font-weight:bold; color:#e0d5f0; }
.settlement-stat-lbl { font-size:.7rem; color:#9080b0; margin-top:2px; }
.settlement-divider { height:1px; background:rgba(180,140,220,.25); margin:12px 0; }
.settlement-balance { font-size:.85rem; color:#b0a0d0; margin-bottom:16px; }
.settlement-balance span { color:#e0c080; font-weight:bold; }
.btn-play-again { background:linear-gradient(135deg,rgba(120,200,100,.3),rgba(100,180,80,.25));
  color:#a0e0a0; border:1px solid rgba(120,200,100,.5); border-radius:12px;
  padding:12px 40px; font-size:1rem; font-weight:700; cursor:pointer;
  transition:transform .15s,box-shadow .15s;
  box-shadow:0 0 12px rgba(100,200,100,.15); }
.btn-play-again:hover { box-shadow:0 0 20px rgba(100,200,100,.3); }
.btn-play-again:active { transform:scale(.95); }
</style>
</head>
<body>
<div id="app"></div>
<script>
// ── 题目池 ──
var questionPool = [];
var currentQIndex = 0;
var pairs = [];
var enDisplay = [];
var zhDisplay = [];
var difficulty = '';
var matchedEn = new Set();
var matchedZh = new Set();
var selectedEn = null;
var errorCount = 0;
var gameOver = false;
var timerStart = null, timerInterval = null, resultsShown = false;

// ── 加载指定题目 ──
function loadQuestion(idx) {
    if (idx < 0 || idx >= questionPool.length) return;
    currentQIndex = idx;
    var q = questionPool[idx];
    pairs = q.pairs || [];
    enDisplay = q.en_display || [];
    zhDisplay = q.zh_display || [];
    difficulty = q.difficulty || 'easy';

    matchedEn = new Set();
    matchedZh = new Set();
    selectedEn = null;
    errorCount = 0;
    gameOver = false;
    timerStart = null;
    if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }

    buildBoard();
}

// ── 一次性创建棋盘 ──
function buildBoard() {
    var diffCls = difficulty === 'easy' ? 'diff-easy' : 'diff-hard';
    var diffLabel = difficulty === 'easy' ? '六级·基础' : '六级·进阶';

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
        '<div>⏱ <span id="time-display">00:00</span></div>' +
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

// ── 刷新 UI ──
function refreshUI() {
    var mc = document.getElementById('match-count');
    if (mc) mc.textContent = matchedEn.size;
    var ec = document.getElementById('error-count');
    if (ec) ec.textContent = errorCount;

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
    questionPool = data.questions || [];
    currentQIndex = data.current_index || 0;

    loadQuestion(currentQIndex);

    if (data.feedback) {
        showFeedback(data.feedback[0], data.feedback[1]);
    }

    if (data.settlement && !resultsShown) {
        resultsShown = true;
        setTimeout(function() { showSettlement(data.settlement); }, 500);
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
    var m = Math.floor(s / 60), sec = s % 60;
    return String(m).padStart(2,'0') + ':' + String(sec).padStart(2,'0');
}
function isCorrectPair(en, zh) {
    for (var i = 0; i < pairs.length; i++) {
        if (pairs[i][0] === en && pairs[i][1] === zh) return true;
    }
    return false;
}

// ── 交互 ──
function clickEn(word) {
    if (gameOver || matchedEn.has(word)) return;
    startTimer();
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
            stopTimer();
            setTimeout(function() { submitResult(); }, 400);
        }
    } else {
        errorCount++;
        selectedEn = null;
        refreshUI();
    }
}

// ── 换一题：题目池本地循环 ──
function newQuestion() {
    currentQIndex = (currentQIndex + 1) % questionPool.length;
    loadQuestion(currentQIndex);
}

function resetGame() {
    matchedEn = new Set();
    matchedZh = new Set();
    selectedEn = null;
    errorCount = 0;
    gameOver = false;
    timerStart = null;
    if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }
    refreshUI();
}

// ── 提交：通过父窗口 URL 参数传递数据 ──
function submitResult() {
    var matchList = [];
    for (var i = 0; i < pairs.length; i++) {
        matchList.push([pairs[i][0], pairs[i][1]]);
    }
    var data = {
        action: 'submit',
        game: 'wm',
        matches: matchList,
        errors: errorCount,
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

// ── 结算浮层 ──
function showSettlement(s) {
    var diffLabel = s.stats.difficulty === 'easy' ? '六级·基础' : '六级·进阶';
    var statsHtml =
        '<div class="settlement-stat"><div class="settlement-stat-val">' +
        fmtTime(s.stats.time_seconds || 0) + '</div><div class="settlement-stat-lbl">用时</div></div>' +
        '<div class="settlement-stat"><div class="settlement-stat-val">' +
        s.stats.total_pairs + '</div><div class="settlement-stat-lbl">词对数</div></div>' +
        '<div class="settlement-stat"><div class="settlement-stat-val">' +
        s.stats.errors + '</div><div class="settlement-stat-lbl">错误</div></div>' +
        '<div class="settlement-stat"><div class="settlement-stat-val" style="font-size:0.85rem;">' +
        diffLabel + '</div><div class="settlement-stat-lbl">难度</div></div>';

    var html =
        '<div class="settlement-overlay" id="settlement-overlay">' +
        '<div class="settlement-card">' +
        '<div class="settlement-title">🏆 全部匹配！</div>' +
        '<div class="settlement-score">+' + s.score + '</div>' +
        '<div class="settlement-score-label">思念值</div>' +
        '<div class="settlement-stats">' + statsHtml + '</div>' +
        '<div class="settlement-divider"></div>' +
        '<div class="settlement-balance">💰 当前思念值 <span>' +
        (s.balance_after || 0).toLocaleString() + '</span></div>' +
        '<button class="btn-play-again" id="btn-play-again">🔄 再来一把</button>' +
        '</div></div>';

    var wrapper = document.createElement('div');
    wrapper.innerHTML = html;
    document.body.appendChild(wrapper.firstElementChild);

    document.getElementById('btn-play-again').addEventListener('click', function() {
        dismissSettlement();
        newQuestion();
    });
}

function dismissSettlement() {
    var el = document.getElementById('settlement-overlay');
    if (el) el.remove();
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
    """初始化单词匹配的 session state"""
    if "wm_pool" not in st.session_state:
        st.session_state.wm_pool = []
    if "wm_pool_idx" not in st.session_state:
        st.session_state.wm_pool_idx = 0
    if "wm_msg" not in st.session_state:
        st.session_state.wm_msg = None
    if "wm_processed_nonce" not in st.session_state:
        st.session_state.wm_processed_nonce = set()
    if "wm_settlement" not in st.session_state:
        st.session_state.wm_settlement = None


def _ensure_pool():
    """确保题目池有题"""
    if not st.session_state.wm_pool or st.session_state.wm_pool_idx >= len(st.session_state.wm_pool):
        st.session_state.wm_pool = [generate_question() for _ in range(POOL_SIZE)]
        st.session_state.wm_pool_idx = 0


def _new_question():
    """换一题：移动到池中下一题"""
    st.session_state.wm_pool_idx += 1


def render_game(game_def):
    """渲染单词匹配游戏"""
    _init_session()

    # ── 处理 URL Query Param 提交 ──
    if "ma" in st.query_params:
        try:
            raw = st.query_params["ma"]
            data = json.loads(raw)
            if data.get("game") == "wm" and data.get("action") == "submit":
                nonce = data.get("nonce", "")
                if nonce and nonce not in st.session_state.wm_processed_nonce:
                    st.session_state.wm_processed_nonce.add(nonce)
                    if len(st.session_state.wm_processed_nonce) > 20:
                        st.session_state.wm_processed_nonce = set(
                            list(st.session_state.wm_processed_nonce)[-20:]
                        )

                    user_answer = {
                        "matches": data.get("matches", []),
                        "errors": data.get("errors", 0),
                    }

                    _ensure_pool()
                    pool = st.session_state.wm_pool
                    idx = data.get("q_index", st.session_state.wm_pool_idx)
                    if idx < len(pool):
                        q = pool[idx]
                    else:
                        q = pool[st.session_state.wm_pool_idx]

                    from storage import get_store
                    from game_engine import calc_game_score
                    store = get_store()
                    result_obj = store.submit_game_score(
                        game_def, q, user_answer, calc_game_score,
                    )

                    if result_obj.success:
                        _new_question()
                        st.session_state.wm_msg = None
                        difficulty_label = "六级·基础" if q.get("difficulty") == "easy" else "六级·进阶"
                        st.session_state.wm_settlement = {
                            "game_id": "word_match",
                            "game_name": "单词匹配",
                            "score": result_obj.score,
                            "balance_after": result_obj.balance_after,
                            "message": result_obj.message,
                            "stats": {
                                "total_pairs": q.get("count", 0),
                                "errors": data.get("errors", 0),
                                "difficulty": q.get("difficulty", "easy"),
                                "difficulty_label": difficulty_label,
                                "time_seconds": data.get("time_seconds", 0),
                            },
                        }
                    else:
                        st.session_state.wm_msg = ("error", result_obj.message)
        except Exception:
            pass
        try:
            del st.query_params["ma"]
        except Exception:
            pass

    # ── 确保题目池有题 ──
    _ensure_pool()

    pool = st.session_state.wm_pool
    idx = st.session_state.wm_pool_idx
    q = pool[idx]

    # ── 构建前端数据 ──
    initial_data = {
        "questions": pool,
        "current_index": idx,
        "feedback": st.session_state.wm_msg,
        "settlement": st.session_state.wm_settlement,
    }

    # ── 渲染组件 ──
    components.html(_build_html(initial_data), height=560, scrolling=False)

    # 清除已显示的结算数据
    st.session_state.wm_settlement = None
    st.session_state.wm_msg = None
