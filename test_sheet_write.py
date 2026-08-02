"""
测试脚本 — 模拟一次记忆翻牌游戏提交全流程
验证：账户状态、操作记录、游戏记录三个工作表的写入
"""
import json
import sys
import os

# 确保能 import 项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import toml as _toml
import storage
from game_engine import GameDef, calc_game_score
from game_memory_match import generate_question, validate_answer, make_question_id


def load_secrets():
    """用 toml 库读取（与 Streamlit 一致），json5 解析凭证（容忍 TOML 转义产生的控制字符）"""
    path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
    with open(path, "r", encoding="utf-8") as f:
        return _toml.load(f)


def main():
    secrets = load_secrets()
    sheet_name = secrets.get("SHEET_NAME", "MissYou")
    sheet_id = secrets.get("SHEET_ID", "")

    print("=" * 60)
    print(f"\U0001f4cb 测试目标：Google Sheet「{sheet_name}」(ID: {sheet_id})")
    print("=" * 60)

    # ── 1. 初始化存储 ──
    print("\n[1/6] 连接 Google Sheets...")
    # 直接从 TOML 源文件提取 JSON 字符串，绕过 TOML 解析
    # TOML 会把 \n 转义变成真实 0x0A → JSON 非法
    # 源文件中的 \n 是字面反斜杠+n → json.loads() 能正确处理
    import re
    secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
    with open(secrets_path, "r", encoding="utf-8") as f:
        raw_toml = f.read()
    match = re.search(
        r'GOOGLE_CREDENTIALS\s*=\s*"""\s*\n?(.*?)"""',
        raw_toml, re.DOTALL
    )
    if not match:
        print("❌ 无法从 secrets.toml 提取 GOOGLE_CREDENTIALS")
        return
    creds = json.loads(match.group(1))
    storage.init_store(creds, sheet_id)
    store = storage.get_store()
    print("✅ 连接成功")

    # ── 2. 读取当前账户状态 ──
    print("\n[2/6] 读取「账户状态」工作表...")
    account = store.get_account()
    print(f"   当前余额: {account.balance}")
    print(f"   每日衰减: {account.daily_decay}")
    print(f"   最后更新: {account.last_update}")
    print(f"   起始之日: {account.start_date}")

    # ── 3. 模拟生成题目 ──
    print("\n[3/6] 模拟生成记忆翻牌题目...")
    q = generate_question()
    qid = make_question_id(q)
    print(f"   布局: {q['cols']}×{q['rows']}（{q['pair_count']} 对）")
    print(f"   卡牌: {q['cards']}")
    print(f"   种子: {q['seed']}")
    print(f"   QID:  {qid}")

    # ── 4. 构造游戏定义 ──
    game = GameDef(
        game_id="memory_match",
        name="\U0001f0cf 记忆翻牌",
        description="翻开卡牌，找到所有配对",
        score=370,
        validate=validate_answer,
        question_id=make_question_id,
    )

    # ── 5. 模拟用户答案（假装翻了 16 次，用了 35 秒） ──
    user_answer = {"total_flips": 16, "time_seconds": 35}
    print(f"\n[4/6] 模拟用户答案: {json.dumps(user_answer, ensure_ascii=False)}")

    # 先检查去重
    already_done = store.is_question_recent(game.game_id, qid)
    if already_done:
        print("   ⚠️  该题已存在于游戏记录（7 天内），提交会被拦截")
    else:
        print("   ✅ 该题未在 7 天内重复，可以提交")

    # ── 6. 提交加分 ──
    print("\n[5/6] 执行 submit_game_score()...")
    result = store.submit_game_score(game, q, user_answer, calc_game_score)

    print(f"   success:       {result.success}")
    print(f"   message:       {result.message}")
    print(f"   score:         {result.score}")
    print(f"   balance_after: {result.balance_after}")

    # ── 7. 验证写入结果 ──
    print("\n[6/6] 验证三个工作表的写入...")

    # 账户状态
    account_after = store.get_account()
    expected = account.balance + result.score
    status = "✅" if account_after.balance == expected else "⚠️"
    print(f"   {status} 账户状态.余额: {account_after.balance}（预期: {expected}）")

    # 操作记录（最新 3 条）
    logs = store.get_logs(limit=3)
    print("   \U0001f4cb 操作记录（最新 3 条）:")
    for log in logs[:3]:
        print(f"      [{log['time']}] {log['op_type']} | {log['change']} | 余额 {log['balance_after']} | {log['note']}")

    # 游戏记录
    print(f"   \U0001f3ae 游戏记录（搜索 QID={qid}）:")
    try:
        ws = store.sheet.worksheet("游戏记录")
        all_rows = ws.get_all_values()
        found = [r for r in all_rows[1:] if len(r) >= 3 and r[2] == qid]
        if found:
            r = found[-1]
            print(f"      时间: {r[0]}")
            print(f"      游戏: {r[1]}")
            print(f"      QID:  {r[2]}")
            print(f"      题目: {r[3][:80]}...")
            print(f"      答案: {r[4]}")
            print(f"      得分: {r[5]}")
            print(f"      余额: {r[6]}")
        else:
            print("      ⚠️ 未找到记录（去重拦截或其他问题）")
    except Exception as e:
        print(f"      ⚠️ 查询游戏记录失败: {e}")

    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
