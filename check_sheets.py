"""
查看 Google Sheet 全部数据 — 连接、所有工作表、所有行
使用方法: python check_sheets.py
"""
import gspread
from google.oauth2.service_account import Credentials
import sys

# 配置
CREDENTIALS_PATH = "d:/ProgramData/doubao/no1project-5555-73945d64b6ec.json"
SHEET_ID = "1xrbzgA86ujg4plQQDwQlIEoqDnIMWPJFG8GD1Ye8vYo"


def main():
    # 1. 连接
    print("=" * 70)
    print("  连接 Google Sheets...")
    try:
        creds = Credentials.from_service_account_file(
            CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID)
        print(f"  ✅ 连接成功 → 表格: {sheet.title}")
    except FileNotFoundError:
        print(f"  ❌ 凭证文件不存在: {CREDENTIALS_PATH}")
        sys.exit(1)
    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        sys.exit(1)

    # 2. 遍历所有工作表
    worksheets = sheet.worksheets()
    print(f"\n  共 {len(worksheets)} 个工作表\n")

    for ws in worksheets:
        data = ws.get_all_values()

        print("=" * 70)
        print(f"  📋 [{ws.title}] — {ws.row_count}行 × {ws.col_count}列")
        print("=" * 70)

        if not data:
            print("  (空表)\n")
            continue

        # 表头
        headers = data[0]
        # 计算每列最大宽度用于对齐
        col_widths = [len(h) for h in headers]
        for row in data:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))

        # 打印表头分隔线
        header_line = " | ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers))
        sep_line = "-" * len(header_line)

        print(f"  {header_line}")
        print(f"  {sep_line}")

        # 数据行
        data_rows = data[1:]
        if data_rows:
            for row in data_rows:
                padded = []
                for i, cell in enumerate(row):
                    if i < len(col_widths):
                        padded.append(str(cell).ljust(col_widths[i]))
                    else:
                        padded.append(str(cell))
                print(f"  {' | '.join(padded)}")
            print(f"\n  📊 数据行数: {len(data_rows)}")
        else:
            print(f"  (暂无数据行)")
        print()

    print("=" * 70)
    print("  ✅ 完成")


if __name__ == "__main__":
    main()
