"""
检查 Google Sheet 内容 — 验证表格连接、工作表结构、初始数据
使用方法: python check_sheets.py
"""
import gspread
from google.oauth2.service_account import Credentials
import sys

# 配置 — 根据你的实际路径可能需要修改
CREDENTIALS_PATH = "d:/ProgramData/doubao/no1project-5555-73945d64b6ec.json"
SHEET_ID = "1xrbzgA86ujg4plQQDwQlIEoqDnIMWPJFG8GD1Ye8vYo"

# 预期的工作表定义
EXPECTED_SHEETS = {
    "账户状态": ["当前思念值", "每日衰减量", "最后更新时间", "思念起始日"],
    "操作记录": ["时间", "操作类型", "数值变化", "操作后余额", "备注"],
}


def main():
    errors = []

    # 1. 连接 Google Sheets
    print("=" * 60)
    print("1. 连接 Google Sheets...")
    try:
        creds = Credentials.from_service_account_file(
            CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID)
        print(f"   ✅ 连接成功 → 表格名称: {sheet.title}")
    except FileNotFoundError:
        print(f"   ❌ 凭证文件不存在: {CREDENTIALS_PATH}")
        sys.exit(1)
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
        print("   → 检查: 凭证有效? 表格已分享给服务账号? 网络正常?")
        sys.exit(1)

    # 2. 检查工作表
    print("\n2. 检查工作表...")
    existing_titles = {ws.title for ws in sheet.worksheets()}

    for expected_name, expected_headers in EXPECTED_SHEETS.items():
        if expected_name not in existing_titles:
            print(f"   ❌ 缺少工作表: [{expected_name}]")
            errors.append(f"请创建 [{expected_name}] 工作表")
        else:
            ws = sheet.worksheet(expected_name)
            data = ws.get_all_values()

            if not data:
                print(f"   ⚠️  [{expected_name}] 存在但为空 — 需要添加表头和数据")
                errors.append(f"[{expected_name}] 是空的，请添加表头")
                continue

            headers = data[0]
            missing = [h for h in expected_headers if h not in headers]
            if missing:
                print(f"   ⚠️  [{expected_name}] 缺少列: {missing}")
                errors.append(f"[{expected_name}] 缺少列 {missing}")
            else:
                print(f"   ✅ [{expected_name}] 列结构正确 ({len(headers)}列)")

            # 显示数据行
            data_rows = data[1:] if len(data) > 1 else []
            if data_rows:
                print(f"      数据行数: {len(data_rows)}")
                for i, row in enumerate(data_rows):
                    print(f"      行{i+2}: {row}")
            else:
                print(f"      (暂无数据行)")

    # 3. 检查多余工作表
    extras = existing_titles - set(EXPECTED_SHEETS.keys())
    if extras:
        print(f"\n   ℹ️  额外工作表: {extras} （非预期，不影响运行）")

    # 4. 总结
    print("\n" + "=" * 60)
    if errors:
        print(f"❌ 发现 {len(errors)} 个问题:")
        for e in errors:
            print(f"   - {e}")
        print("\n修复后重新运行此脚本验证。")
        sys.exit(1)
    else:
        print("✅ 一切正常！表格结构符合预期，可以部署了。")
        sys.exit(0)


if __name__ == "__main__":
    main()
