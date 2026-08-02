# 🌙 MissYou — 思念量化系统

> "每一份思念都值得被看见"

星空夜幕主题的思念值管理系统，内置记忆翻牌小游戏，通过 Google Sheets 免费存储数据，一键部署到 Streamlit Cloud。

---

## ✨ 功能

- **🔐 双密码门** — 用户密码查看思念余额，管理员密码进入后台
- **📊 思念值仪表盘** — 星空动画背景，余额卡片、每日流逝、累计消散、起始之日
- **⚙️ 管理员后台** — 手动增减余额、调整每日衰减速度、查看操作记录
- **🃏 记忆翻牌** — 翻牌配对赚思念值，动态计分（翻牌次数越少得分越高），7 天去重
- **⏳ 每日衰减** — 余额随时间自动递减，模拟"思念随时间流逝"

---

## 🏗️ 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端框架** | [Streamlit](https://streamlit.io/) 1.36 | Python 驱动的 Web UI，零前端代码 |
| **数据存储** | [Google Sheets](https://sheets.google.com) | 免费云端表格，替代传统数据库 |
| **表格 SDK** | [gspread](https://docs.gspread.org/) 6.1 | Python 读写 Google Sheets |
| **认证** | [google-auth](https://google-auth.readthedocs.io/) 2.32 | Google 服务账号 OAuth2 鉴权 |
| **云端部署** | [Streamlit Cloud](https://share.streamlit.io/) | 免费托管，自动 CI/CD，永久外网链接 |
| **测试** | [pytest](https://pytest.org/) | 25 个单元测试，覆盖业务逻辑和游戏引擎 |
| **运行环境** | Python 3.9+ | `.python-version` 锁定版本 |

### 架构分层

```
app.py                  # Streamlit 页面：密码门 → 用户页/管理员页
  ├── game_engine.py    # 游戏框架：GameDef 数据类、注册表、动态计分
  ├── game_memory_match.py  # 记忆翻牌：出题、前端 HTML/CSS/JS、提交验证
  └── storage.py        # 数据层：MissYouStore 单例、Google Sheets 读写
```

- **纯函数业务逻辑**（密码验证、衰减计算）在 `app.py` 顶层，不依赖 Streamlit session state
- **游戏引擎** (`game_engine.py`) 定义统一的 `GameDef` 接口，新游戏只需实现 `generate` / `validate` / `render` / `question_id` 四个函数即可注册
- **存储层** (`storage.py`) 通过模块级单例 `get_store()` 访问，所有 Google Sheets 操作集中管理，避免循环依赖

---

## 🚀 快速部署

### 1. Google Sheets 准备

- 前往 [Google Sheets](https://sheets.google.com) 创建新的 Google Sheet，命名为 `MissYou`
- 新建三个工作表（底部标签页）：

| 工作表 | 表头 |
|--------|------|
| `账户状态` | `当前思念值 \| 每日衰减量 \| 最后更新时间 \| 思念起始日` |
| `操作记录` | `时间 \| 操作类型 \| 数值变化 \| 操作后余额 \| 备注` |
| `游戏记录` | 自动创建，无需手动建表 |

- 在 `账户状态` 第 2 行填入初始数据，例如：`10000 | 10 | 2026-08-01 | 2025-08-15`

### 2. Google Cloud 配置

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 新建项目（或使用已有项目）
3. 左侧菜单 → **API 和服务** → **库** → 搜索并启用 **Google Sheets API**
4. 左侧菜单 → **API 和服务** → **凭据** → **创建凭据** → **服务账号**
5. 服务账号名称随意填 → 选择"编辑者"角色 → 完成
6. 点击创建好的服务账号 → **密钥** → **添加密钥** → **创建新密钥** → **JSON** → 下载
7. **关键步骤：** 打开下载的 JSON 文件，复制 `client_email` 的值
8. 回到你的 Google Sheet → 右上角 **共享** → 粘贴 `client_email` → 赋予**编辑者**权限

### 3. Streamlit Cloud 部署

1. 将本仓库 Fork 到你的 GitHub 账号（或直接 `git push`）
2. 前往 [share.streamlit.io](https://share.streamlit.io/) → 用 GitHub 账号登录
3. 右上角 **New app**
4. 三栏填写：
   - **Repository**：你的仓库
   - **Branch**：`main`
   - **Main file path**：`app.py`
5. 点击 **Advanced settings** → **Secrets** 中填入：

```toml
USER_PWD = "用户查看密码"
ADMIN_PWD = "管理员后台密码"
SHEET_NAME = "MissYou"
SHEET_ID = "你的 Google Sheet ID（从浏览器地址栏复制那串长 ID）"

GOOGLE_CREDENTIALS = """
粘贴刚才下载的 JSON 文件全部内容（包括花括号）
"""
```

6. 点击 **Deploy!** → 等待 1-3 分钟 → 获得 `https://xxx.streamlit.app` 永久链接

### 4. 使用

- 将链接发给用户，用户用 `USER_PWD` 查看思念余额 + 玩记忆翻牌赚思念值
- 你自己用 `ADMIN_PWD` 进入后台操作余额、调整衰减、查看操作记录

---

## 💻 本地运行

```bash
# 克隆仓库
git clone <your-repo-url>
cd MissYou

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置 secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# 编辑 .streamlit/secrets.toml，填入真实的 Google 凭证和密码

# 启动
streamlit run app.py
```

### 运行测试

```bash
pytest test_game.py test_app.py -v
# 25 passed — 覆盖衰减计算、密码验证、游戏出题/验证/去重/动态计分、注册表
```

---

## 📁 项目结构

```
MissYou/
├── app.py                  # 主入口：页面路由、密码验证、衰减逻辑
├── game_engine.py          # 游戏框架：GameDef 数据类、注册表、动态计分
├── game_memory_match.py    # 记忆翻牌：出题/验证/前端 HTML+CSS+JS
├── storage.py              # 数据层：Google Sheets 读写、统一加分流程
├── test_game.py            # 游戏引擎 & 存储层单元测试 (19 个)
├── test_app.py             # 业务逻辑单元测试 (6 个)
├── requirements.txt        # Python 依赖
├── packages.txt            # Streamlit Cloud 系统依赖
├── .python-version         # Python 版本
├── .streamlit/
│   └── secrets.toml.example  # Secrets 模板（不含真实凭证）
├── .devcontainer/
│   └── devcontainer.json   # VS Code Dev Container 配置
└── docs/
    └── superpowers/        # 设计文档 & 开发计划
```

---

## 🔒 安全说明

- 用户密码和管理员密码分开，通过 Streamlit Secrets 注入，**不存储在代码仓库中**
- Google 服务账号凭证同样存储在 Secrets 中，代码仓库只保留 `.example` 模板
- 操作日志中所有用户输入均做 HTML 转义防护
- 游戏答题需经过服务端二次验证（防客户端篡改），仅通过 URL 参数传递会触发拒绝
- 建议定期更换密码

---

## 🎮 记忆翻牌游戏规则

| 项目 | 说明 |
|------|------|
| **布局** | 随机 4×3（6 对）或 4×4（8 对） |
| **卡牌** | 32 种 emoji（动物、水果、符号等） |
| **得分** | 基准 370 思念值 × 翻牌效率系数 |
| **最优** | pair_count × 2 次翻牌 → 满分 |
| **保底** | 即使翻很多次，至少拿 50% 分数 |
| **去重** | 同一道题 7 天内答对不再重复加分 |
| **换题** | 预生成 10 题池，本地秒切，无需等服务端 |
