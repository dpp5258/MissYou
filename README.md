# MissYou — 思念量化系统

星空夜幕主题 🌙 | Streamlit | Google Sheets | 免费部署

> "每一份思念都值得被看见"

## 快速部署

### 1. Google Sheets 准备
- 前往 https://sheets.google.com 创建新的 Google Sheet，命名为 `MissYou`
- 新建两个工作表（底部标签页）：
  - `账户状态` — 第 1 行填入表头：`当前思念值 | 每日衰减量 | 最后更新时间 | 思念起始日`
  - `操作记录` — 第 1 行填入表头：`时间 | 操作类型 | 数值变化 | 操作后余额 | 备注`
- 在 `账户状态` 第 2 行填入初始数据，例如：`10000 | 10 | 2026-06-06 | 2025-08-15`

### 2. Google Cloud 配置
- 前往 https://console.cloud.google.com/
- 新建项目（或使用已有项目）
- 左侧菜单 → API 和服务 → 库 → 搜索 "Google Sheets API" → 启用
- 左侧菜单 → API 和服务 → 凭据 → 创建凭据 → 服务账号
- 服务账号名称随意填 → 创建 → 选择"编辑者"角色 → 完成
- 点击创建好的服务账号 → 密钥 → 添加密钥 → 创建新密钥 → JSON → 下载
- **重要：** 打开下载的 JSON 文件，复制 `client_email` 的值
- 回到你的 Google Sheet → 右上角"共享" → 粘贴 `client_email` → 赋予编辑权限

### 3. Streamlit Cloud 部署
- 将本仓库 Fork 到你的 GitHub 账号（或直接上传代码）
- 前往 https://share.streamlit.io/ → 用 GitHub 账号登录
- 右上角 **New app**
- 三栏填写：
  - Repository：选择你的仓库
  - Branch：`main`
  - Main file path：`app.py`
- 点击 **Advanced settings** → Secrets 中填入以下内容：

```toml
USER_PWD = "你设定的用户查看密码"
ADMIN_PWD = "你设定的管理员密码"
SHEET_NAME = "MissYou"

GOOGLE_CREDENTIALS = """
粘贴刚才下载的 JSON 文件全部内容
"""
```

- 点击 **Deploy!** 等待 1-3 分钟

### 4. 使用
- 部署成功后获得网址：`https://xxx.streamlit.app`
- 将链接发给用户，用户用 `USER_PWD` 查看思念余额
- 你自己用 `ADMIN_PWD` 进入后台操作 tokens
- 后台支持：手动增减余额、调整每日衰减速度、查看操作记录

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 复制 secrets 模板并填入真实值
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# 编辑 .streamlit/secrets.toml，填入真实的 Google 凭证和密码

# 启动
streamlit run app.py
```

## 技术栈

- **Python 3.9+** + **Streamlit** — 网页框架
- **Google Sheets** — 免费数据存储
- **gspread** — Python 操作 Google Sheets
- **Streamlit Cloud** — 免费部署，永久外网链接

## 安全说明

- 用户密码和管理员密码分开设置
- Google 凭证存储在 Streamlit Secrets 中，不暴露在代码仓库
- 操作日志中数据已做 HTML 转义防护
- 建议定期更换密码
