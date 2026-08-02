"""
测试 storage.py 存储层 — 覆盖所有读写操作
支持两种模式：
  1. 如果有真实 Google 凭证 → 端到端集成测试
  2. 如果凭证是占位符 → Mock 测试（不联网）
"""
import json
import os
import sys
import re
from datetime import date, datetime
from unittest.mock import Mock, patch

import toml as _toml
import storage
from game_engine import GameDef, calc_game_score


# ============================================================
# 辅助：判断凭证是否真实
# ============================================================

def _is_placeholder(creds: dict) -> bool:
    """检查凭证 key 是否包含明显的占位符"""
    pk = creds.get("private_key", "")
    pid = creds.get("project_id", "")
    # 真实 key 长度 > 1000，占位符只有几十个字符
    return len(pk) < 500 or pid == "xxx"


# ============================================================
# Mock 模式测试（无需联网，秒过）
# ============================================================

def test_with_mock():
    """用 Mock 对象模拟 Google Sheets，测试所有存储操作"""
    print("=" * 60)
    print("🧪 Mock 模式 — 模拟测试存储层全部操作")
    print("=" * 60)

    passed = 0
    failed = 0

    # 初始化一个假 store，手动注入 mock sheet
    store = storage.MissYouStore({"test": "dummy"}, "mock_sheet_id")

    # ---- 构造 Mock 工作表 ----
    mock_account_ws = Mock()
    mock_log_ws = Mock()
    mock_game_ws = Mock()

    # 账户状态 mock
    mock_account_ws.row_values.return_value = ["10000", "10", "2026-08-01", "2025-08-15"]
    mock_account_ws.update = Mock()

    # 操作日志 mock（空表）
    mock_log_ws.get_all_values.return_value = [
        ["时间", "操作类型", "数值变化", "操作后余额", "备注"],
    ]
    mock_log_ws.append_row = Mock()

    # 游戏记录 mock（空表）
    mock_game_ws.get_all_values.return_value = [
        ["时间", "游戏类型", "题目ID", "题目数据", "用户答案", "得分", "操作后余额"],
    ]
    mock_game_ws.append_row = Mock()

    def _ws_side_effect(name):
        if name == "账户状态":
            return mock_account_ws
        elif name == "操作记录":
            return mock_log_ws
        elif name == "游戏记录":
            return mock_game_ws
        raise ValueError(f"未知工作表: {name}")

    store._sheet = Mock()
    store._sheet.worksheet.side_effect = _ws_side_effect

    # ── 测试 1: get_account() ──
    print("\n📋 [1/8] get_account() — 读取账户状态")
    try:
        account = store.get_account()
        assert account.balance == 10000.0, f"余额应为 10000，实际 {account.balance}"
        assert account.daily_decay == 10.0
        assert account.last_update == "2026-08-01"
        assert account.start_date == "2025-08-15"
        print(f"   ✅ 余额={account.balance}, 衰减={account.daily_decay}, "
              f"最后更新={account.last_update}, 起始日={account.start_date}")
        passed += 1
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        failed += 1

    # ── 测试 2: set_balance() ──
    print("\n📋 [2/8] set_balance() — 覆写账户状态")
    try:
        store.set_balance(10500.0, 8.0, "2026-08-02", "2025-08-15")
        mock_account_ws.update.assert_called_once()
        call_args = mock_account_ws.update.call_args
        # update("A2:D2", [[balance, decay, date, start_date]])
        assert call_args[0][0] == "A2:D2"
        data = call_args[0][1]
        assert data[0][0] == 10500.0
        assert data[0][1] == 8.0
        assert data[0][2] == "2026-08-02"
        print(f"   ✅ 写入成功: 余额=10500, 衰减=8")
        passed += 1
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        failed += 1

    # ── 测试 3: add_log() ──
    print("\n📋 [3/8] add_log() — 追加操作日志")
    try:
        store.add_log("管理员调整", "+500", 10500.0, "测试写入")
        mock_log_ws.append_row.assert_called_once()
        log_args = mock_log_ws.append_row.call_args[0][0]
        assert len(log_args) == 5, f"应 5 列，实际 {len(log_args)}"
        assert log_args[1] == "管理员调整"
        assert log_args[2] == "+500"
        assert log_args[3] == 10500.0
        assert log_args[4] == "测试写入"
        # 验证时间戳格式
        datetime.strptime(log_args[0], "%Y-%m-%d %H:%M")
        print(f"   ✅ 日志已追加: [{log_args[0]}] {log_args[1]} | {log_args[2]}")
        passed += 1
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        failed += 1

    # ── 测试 4: get_logs() ──
    print("\n📋 [4/8] get_logs() — 读取操作日志")
    try:
        # 模拟两条日志（Sheet 中旧在上、新在下，append 追加到末尾）
        mock_log_ws.get_all_values.return_value = [
            ["时间", "操作类型", "数值变化", "操作后余额", "备注"],
            ["2026-08-01 09:00", "每日衰减", "-10", "10000", "自然流逝"],           # 旧 → 在上
            ["2026-08-01 10:00", "游戏奖励-记忆翻牌", "+370", "10370", "题目#MM_001"], # 新 → 在下
        ]
        logs = store.get_logs(limit=3)
        if len(logs) != 2:
            print(f"   ⚠️ 预期 2 条，实际 {len(logs)} 条: {logs}")
        assert len(logs) == 2, f"预期 2 条日志，实际 {len(logs)}"
        # 应倒序返回（最新在前）
        assert logs[0]["op_type"] == "游戏奖励-记忆翻牌", f"预期'游戏奖励'，实际'{logs[0]['op_type']}'"
        assert logs[1]["op_type"] == "每日衰减"
        assert logs[0]["change"] == "+370"
        assert logs[1]["change"] == "-10"
        print(f"   ✅ 读取 {len(logs)} 条日志（倒序）:")
        for l in logs:
            print(f"      [{l['time']}] {l['op_type']} | {l['change']} | 余额 {l['balance_after']}")
        passed += 1
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        failed += 1

    # ── 测试 5: is_question_recent() — 新题 ──
    print("\n📋 [5/8] is_question_recent() — 去重检查（新题）")
    try:
        result = store.is_question_recent("memory_match", "MM_new_001")
        assert result is False, "新题不应被拦截"
        print(f"   ✅ 新题未被拦截（is_recent={result}）")
        passed += 1
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        failed += 1

    # ── 测试 6: is_question_recent() — 旧题 ──
    print("\n📋 [6/8] is_question_recent() — 去重检查（7天内旧题）")
    try:
        today_str = date.today().strftime("%Y-%m-%d")
        mock_game_ws.get_all_values.return_value = [
            ["时间", "游戏类型", "题目ID", "题目数据", "用户答案", "得分", "操作后余额"],
            [f"{today_str} 12:00", "memory_match", "MM_dup_002", "...", "...", "370", "1000"],
        ]
        result = store.is_question_recent("memory_match", "MM_dup_002")
        assert result is True, "7天内的旧题应被拦截"
        print(f"   ✅ 旧题被正确拦截（is_recent={result}）")
        passed += 1
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        failed += 1

    # ── 测试 7: submit_game_score() — 完整加分链路 ──
    print("\n📋 [7/8] submit_game_score() — 完整加分链路")
    try:
        # 重置 mock 状态
        mock_game_ws.get_all_values.return_value = [
            ["时间", "游戏类型", "题目ID", "题目数据", "用户答案", "得分", "操作后余额"],
        ]
        mock_account_ws.row_values.return_value = ["10000", "10", "2026-08-01", "2025-08-15"]

        # 构造一个迷你游戏定义
        test_game = GameDef(
            game_id="memory_match",
            name="🃏 记忆翻牌",
            description="测试游戏",
            score=370,
            validate=lambda q, a: a.get("total_flips", 0) >= 12,
            question_id=lambda q: f"mock_{q['seed']}",
        )
        question = {"seed": 42, "cols": 4, "rows": 3, "pair_count": 6,
                     "cards": ["🐶","🐶","🐱","🐱","🐰","🐰","🐻","🐻","🐼","🐼","🦊","🦊"]}
        answer = {"total_flips": 14, "time_seconds": 38}

        result = store.submit_game_score(test_game, question, answer, calc_game_score)

        assert result.success, f"提交应成功: {result.message}"
        assert result.score > 0
        assert result.balance_after == 10000 + result.score

        # 验证三个写入都被调用了
        assert mock_account_ws.update.called, "应写账户状态"
        assert mock_log_ws.append_row.called, "应写操作日志"
        assert mock_game_ws.append_row.called, "应写游戏记录"

        print(f"   ✅ success={result.success}")
        print(f"   📊 得分: +{result.score} 思念值")
        print(f"   💰 余额: {result.balance_after}")
        print(f"   📝 消息: {result.message}")
        print(f"   ✅ 已确认三方写入: 账户状态 ✓ | 操作日志 ✓ | 游戏记录 ✓")
        passed += 1
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

    # ── 测试 8: submit_game_score() — 去重拦截 ──
    print("\n📋 [8/8] submit_game_score() — 去重拦截")
    try:
        today_str = date.today().strftime("%Y-%m-%d")
        mock_game_ws.get_all_values.return_value = [
            ["时间", "游戏类型", "题目ID", "题目数据", "用户答案", "得分", "操作后余额"],
            [f"{today_str} 12:00", "memory_match", "mock_42", "...", "...", "370", "1000"],
        ]

        test_game = GameDef(
            game_id="memory_match",
            name="🃏 记忆翻牌",
            description="",
            score=370,
            validate=lambda q, a: True,
            question_id=lambda q: f"mock_{q['seed']}",
        )
        question = {"seed": 42}
        answer = {"total_flips": 14}

        result = store.submit_game_score(test_game, question, answer)
        assert result.success is False
        assert "7 天" in result.message or "答过" in result.message
        print(f"   ✅ 去重拦截成功: {result.message}")
        passed += 1
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        failed += 1

    # ── 总结 ──
    print("\n" + "=" * 60)
    print(f"📊 结果: {passed} 通过, {failed} 失败 (共 {passed+failed} 项)")
    if failed == 0:
        print("✅ 所有 Mock 测试通过！")
    print("=" * 60)
    return passed, failed


# ============================================================
# 真实集成测试（尝试连接真实 Google Sheets）
# ============================================================

def _banner(title: str):
    print(f"\n{'─' * 50}\n  {title}\n{'─' * 50}")


def _load_real_credentials():
    """尝试从多个来源加载真实凭证，返回 (creds_dict, sheet_id) 或 (None, None)"""
    base = os.path.dirname(os.path.abspath(__file__))

    # 来源 1：secrets_config.txt（TOML 字典格式，推荐）
    config_path = os.path.join(base, "secrets_config.txt")
    if os.path.exists(config_path):
        try:
            conf = _toml.load(config_path)
            creds = conf.get("GOOGLE_CREDENTIALS")
            sid = conf.get("SHEET_ID", "")
            if creds and isinstance(creds, dict) and not _is_placeholder(creds):
                return creds, sid
        except Exception as e:
            print(f"   [DEBUG] secrets_config.txt 加载异常: {type(e).__name__}: {e}")

    # 来源 2：Google 服务账号 JSON 文件
    for fname in os.listdir(base):
        if "no1project" in fname and fname.endswith(".json"):
            try:
                with open(os.path.join(base, fname), "r", encoding="utf-8") as f:
                    creds = json.load(f)
                if not _is_placeholder(creds):
                    # SHEET_ID 从 secrets_config.txt 取
                    if os.path.exists(config_path):
                        conf = _toml.load(config_path)
                        sid = conf.get("SHEET_ID", "")
                    else:
                        sid = ""
                    return creds, sid
            except Exception:
                pass

    # 来源 3：.streamlit/secrets.toml（JSON 字符串嵌入 TOML）
    toml_path = os.path.join(base, ".streamlit", "secrets.toml")
    if os.path.exists(toml_path):
        try:
            with open(toml_path, "r", encoding="utf-8") as f:
                raw = f.read()
            match = re.search(r'GOOGLE_CREDENTIALS\s*=\s*"""\s*\n?(.*?)"""', raw, re.DOTALL)
            if match:
                creds = json.loads(match.group(1))
                m2 = re.search(r'SHEET_ID\s*=\s*"([^"]+)"', raw)
                sid = m2.group(1) if m2 else ""
                if not _is_placeholder(creds):
                    return creds, sid
        except Exception:
            pass

    return None, None


def test_with_real_sheets():
    """端到端测试 — 连接真实 Google Sheets 并写入验证"""
    print("=" * 60)
    print("🌐 集成测试 — 真实 Google Sheets 读写")
    print("=" * 60)

    creds, sheet_id = _load_real_credentials()
    if creds is None:
        print("⚠️  未找到真实 Google 凭证，跳过真实连接测试")
        print("   请确保 secrets_config.txt 或服务账号 JSON 文件存在于项目根目录")
        return 0, 0

    print(f"📋 Sheet ID: {sheet_id}")
    print(f"📧 服务账号: {creds.get('client_email', '?')}")

    passed = 0
    failed = 0

    # ── 1. 连接测试 ──
    _banner("[1/7] 连接 Google Sheets")
    try:
        storage.init_store(creds, sheet_id)
        store = storage.get_store()
        # 触发真正的连接
        sheet_obj = store.sheet
        print(f"✅ 连接成功！Sheet 标题: {sheet_obj.title}")
        print(f"   工作表列表: {[w.title for w in sheet_obj.worksheets()]}")
        passed += 1
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        failed += 1
        return passed, failed

    # ── 2. 读取账户状态 ──
    _banner("[2/7] 读取账户状态")
    try:
        account = store.get_account()
        print(f"   余额: {account.balance}")
        print(f"   每日衰减: {account.daily_decay}")
        print(f"   最后更新: {account.last_update}")
        print(f"   起始之日: {account.start_date}")
        passed += 1
    except Exception as e:
        print(f"❌ 失败: {e}")
        failed += 1

    # ── 3. 读取操作日志 ──
    _banner("[3/7] 读取操作日志（最近 5 条）")
    try:
        logs = store.get_logs(limit=5)
        if logs:
            for log in logs:
                print(f"   [{log['time']}] {log['op_type']} | {log['change']} | {log['note']}")
        else:
            print("   (操作记录为空)")
        passed += 1
    except Exception as e:
        print(f"❌ 失败: {e}")
        failed += 1

    # ── 4. 写入操作日志 ──
    _banner("[4/7] 写入一条测试日志")
    try:
        store.add_log("测试脚本", "+0", account.balance, "test_storage.py 测试写入")
        print("✅ 测试日志已写入「操作记录」")
        # 验证
        logs = store.get_logs(limit=1)
        assert len(logs) > 0
        assert logs[0]["op_type"] == "测试脚本"
        assert logs[0]["note"] == "test_storage.py 测试写入"
        print(f"✅ 验证成功: [{logs[0]['time']}] {logs[0]['op_type']} | {logs[0]['note']}")
        passed += 1
    except Exception as e:
        print(f"❌ 失败: {e}")
        failed += 1

    # ── 5. 覆写账户状态 ──
    _banner("[5/7] 修改账户余额（测试用 +1）")
    original_balance = account.balance
    try:
        new_test = original_balance + 1
        store.set_balance(new_test, account.daily_decay,
                          date.today().strftime("%Y-%m-%d"), account.start_date)
        # 验证
        updated = store.get_account()
        assert updated.balance == new_test, f"期望 {new_test}，实际 {updated.balance}"
        print(f"✅ 余额已更新: {original_balance} → {updated.balance}")
        passed += 1
    except Exception as e:
        print(f"❌ 失败: {e}")
        failed += 1

    # ── 6. 模拟游戏提交 ──
    _banner("[6/7] 模拟记忆翻牌游戏提交")
    try:
        from game_memory_match import generate_question, validate_answer, make_question_id

        test_game = GameDef(
            game_id="memory_match",
            name="🃏 记忆翻牌",
            description="测试用",
            score=370,
            validate=validate_answer,
            question_id=make_question_id,
        )
        q = generate_question()
        qid = make_question_id(q)
        print(f"   题目: {q['cols']}×{q['rows']} ({q['pair_count']}对)")
        print(f"   种子: {q['seed']}")

        # 检查去重状态
        recent = store.is_question_recent("memory_match", qid)
        if recent:
            print(f"   ⚠️ 此 QID ({qid}) 7 天内已答过，跳过加分测试")
        else:
            answer = {"total_flips": 14, "time_seconds": 35}
            result = store.submit_game_score(test_game, q, answer, calc_game_score)
            if result.success:
                print(f"   ✅ 提交成功: +{result.score} 思念值")
                print(f"   余额: {result.balance_after}")
                print(f"   消息: {result.message}")
            else:
                print(f"   ⚠️ {result.message}")
        passed += 1
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

    # ── 7. 恢复原始余额 ──
    _banner("[7/7] 恢复原始余额")
    try:
        store.set_balance(original_balance, account.daily_decay,
                          account.last_update, account.start_date)
        restored = store.get_account()
        assert restored.balance == original_balance
        print(f"✅ 余额已恢复: {restored.balance}")
        passed += 1
    except Exception as e:
        print(f"❌ 失败: {e}")
        failed += 1

    # ── 总结 ──
    print("\n" + "=" * 60)
    print(f"📊 集成测试结果: {passed} 通过, {failed} 失败 (共 {passed+failed} 项)")
    if failed == 0:
        print("✅ 所有集成测试通过！")
    print("=" * 60)
    return passed, failed


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    # 先跑真实连接测试（有凭证时），再跑 Mock 测试
    real_pass, real_fail = test_with_real_sheets()
    print("\n\n")
    mock_pass, mock_fail = test_with_mock()

    total_pass = real_pass + mock_pass
    total_fail = real_fail + mock_fail

    print(f"\n🏁 全部完成: {total_pass} 通过, {total_fail} 失败 (共 {total_pass+total_fail} 项)")
    sys.exit(0 if total_fail == 0 else 1)
