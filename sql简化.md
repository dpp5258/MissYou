# MissYou 存储层简化方案：Google Sheets → SQLite

## 目标

将数据存储从 Google Sheets (gspread) 替换为本地 SQLite，实现：
- **零外部依赖**：SQLite 是 Python 标准库，不需要 Google Cloud 服务账号
- **单文件存储**：所有数据存在 `missyou.db`，方便备份迁移
- **线程安全**：WAL 模式支持 Streamlit 多 session 并发读写
- **接口不变**：`storage` 模块对外暴露的方法签名保持一致，`app.py` 和游戏层无需改动

## 改动清单

### 1. 新建 `storage_sqlite.py`（约 150 行）

替换 `storage.py`，实现相同的 `MissYouStore` 类 + 6 个方法：

```
数据库: missyou.db（自动创建，与 app.py 同目录）
表结构（3 张表）:
  - account（1 行）: balance, daily_decay, last_update, start_date
  - logs（追加）: id, time, op_type, change, balance_after, note
  - game_records: id, time, game_type, qid, question_data, user_answer, score, balance_after
```

| 方法 | SQLite 实现 |
|------|------------|
| `get_account()` | `SELECT * FROM account WHERE id = 1` |
| `set_balance(...)` | `INSERT OR REPLACE INTO account ...` |
| `add_log(...)` | `INSERT INTO logs ...` |
| `get_logs(limit)` | `SELECT ... FROM logs ORDER BY id DESC LIMIT ?` |
| `is_question_recent(game_type, qid)` | `SELECT 1 FROM game_records WHERE game_type=? AND qid=? AND time >= ?` |
| `submit_game_score(...)` | 事务包裹：验证→计分→更新账户→写日志→写记录 |

### 2. 修改 `app.py`（1 行）

```python
# 第 12 行：改 import
- import storage
+ import storage_sqlite as storage
```

`_init_storage()` 中删掉 Google 凭据相关代码，改为直接初始化 SQLite：

```python
def _init_storage():
    storage.init_store()  # SQLite 不需要外部凭据
```

### 3. 修改 `requirements.txt`

```diff
- streamlit==1.36.0
- gspread==6.1.2
- google-auth==2.32.0
+ streamlit==1.36.0
```

### 4. 简化 `.streamlit/secrets.toml`

不再需要这三项：
- `GOOGLE_CREDENTIALS`
- `SHEET_ID`
- `SHEET_NAME`

保留 `USER_PWD` 和 `ADMIN_PWD` 即可。

## 不改动的文件

以下文件无需任何修改：
- `game_engine.py` — 不依赖存储层
- `game_memory_match.py` — 通过 `storage.get_store()` 调用，接口不变
- `test_game.py` — 纯游戏逻辑测试
- `test_app.py` — 衰减/密码函数仍是纯函数
- `test_storage.py` / `test_sheet_write.py` — 可后续更新

## 实施步骤

1. 激活 conda 环境：`conda activate copaw-env`
2. 创建 `storage_sqlite.py`
3. 修改 `app.py` 的 import 和 `_init_storage()`
4. 更新 `requirements.txt`
5. 运行现有测试验证
6. 启动应用确认功能正常

## 风险评估

- **数据迁移**：旧 Google Sheets 数据需要手动导出，但本项目是个人使用，不影响
- **测试**：`test_storage.py` 目前测试 Google Sheets 实现，后续需要更新为 SQLite 版本
- **兼容性**：对外接口完全相同，`get_store().get_account()` 等调用零改动
