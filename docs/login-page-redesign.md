# 🌙 登录页视觉优化方案

> 状态：待实施 | 日期：2026-08-02

---

## 一、现状分析

当前 `render_password_gate()` 登录页存在以下问题：

| 问题 | 影响 |
|------|------|
| 标题仅为静态文字 + 固定光晕 | 缺乏动感，与用户页星空氛围割裂 |
| 输入框/按钮使用 Streamlit 默认蓝色样式 | 与紫色星空主题不协调 |
| 无星星装饰 | 用户页有 10 颗闪烁星星，登录页完全空白 |
| 全局未指定中文字体 | Windows 默认宋体偏生硬，缺乏情感表达 |
| 管理员入口 `#555` 灰字 | 太低调，几乎不可见 |
| 密码卡片缺少层次感 | 纯色半透明，没有悬浮效果 |

---

## 二、设计目标

1. **视觉统一** — 登录页与用户页/管理页共享同一套星空夜幕设计语言
2. **情感传达** — 用户打开页面第一时间感受到"思念"的氛围
3. **品质感** — 细节打磨消除"模板感"，让页面看起来像精心设计的产品

---

## 三、具体改动

### 3.1 全局字体

```css
/* 衬线体更契合"思念"的情感基调 */
* {
    font-family: 'Georgia', 'Noto Serif SC', 'Songti SC', serif;
}
```

- 优先使用系统自带 `Georgia`（免加载外部资源）
- `Noto Serif SC` 作为备选，需在 `<head>` 引入 Google Fonts CSS
- 降级链保证各平台都有优雅的衬线字体渲染

### 3.2 标题增强 — 月亮呼吸光晕

```css
.title-missyou {
    text-align: center;
    font-size: 3rem;
    font-weight: bold;
    color: #e8d5f5;
    animation: moonGlow 3s ease-in-out infinite alternate;
}
@keyframes moonGlow {
    0%   { text-shadow: 0 0 20px rgba(180,130,220,0.6); }
    100% { text-shadow: 0 0 40px rgba(200,160,240,0.9),
                      0 0 80px rgba(160,120,220,0.5); }
}
```

光晕像呼吸一样 3 秒周期明暗交替，与用户页的 `skyPulse` 背景动画呼应。

### 3.3 密码卡片增强

```css
.password-box {
    background: rgba(20,15,45,0.7);
    backdrop-filter: blur(8px);
    border-radius: 20px;
    padding: 2.5rem 2rem;
    border: 1px solid rgba(180,130,220,0.35);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4),
                inset 0 1px 0 rgba(255,255,255,0.03);
}
```

- `backdrop-filter: blur(8px)` — 卡片悬浮在星空上的毛玻璃效果
- 外阴影 + 内高光 — 增加卡片厚度感
- 圆角从 16px → 20px，内边距加大，视觉更舒展

### 3.4 输入框统一样式

```css
div[data-testid="stTextInput"] input {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(180,140,220,0.4) !important;
    border-radius: 10px !important;
    color: #e8d5f5 !important;
    font-size: 1.05rem !important;
    padding: 10px 14px !important;
}
div[data-testid="stTextInput"] input::placeholder {
    color: #6a5a8a !important;
}
```

- 半透明暗底替换默认白底
- 紫色边框与主题统一
- placeholder 用暗紫色，不抢眼

### 3.5 按钮统一样式

```css
div[data-testid="stButton"] button {
    background: linear-gradient(135deg, rgba(140,100,200,0.5),
                                         rgba(100,60,180,0.5)) !important;
    border: 1px solid rgba(180,140,220,0.5) !important;
    border-radius: 12px !important;
    color: #f0e0ff !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
div[data-testid="stButton"] button:hover {
    background: linear-gradient(135deg, rgba(160,120,220,0.6),
                                         rgba(120,80,200,0.6)) !important;
    box-shadow: 0 0 20px rgba(150,100,220,0.4) !important;
    transform: scale(1.02);
}
```

- 紫色渐变替换默认蓝色
- hover 时光晕扩大 + 微微放大
- 圆角 12px 与卡片风格统一

### 3.6 登录页添加星星装饰

从用户页复制星星 HTML 结构 + CSS 动画（可减少至 5-6 颗），让用户打开页面第一眼就进入星空氛围。

### 3.7 管理员入口优化

```css
.admin-hint {
    text-align: center;
    color: #605080;
    font-size: 0.78rem;
    margin-top: 2rem;
    letter-spacing: 2px;
    transition: color 0.3s;
}
.admin-hint:hover {
    color: #9080b0;
}
```

- 颜色从 `#555` 改为主题一致的 `#605080`
- 加字间距，hover 微亮，暗示可交互

---

## 四、改动范围

| 文件 | 改动 |
|------|------|
| `app.py` | `render_password_gate()` 函数的 CSS 块（约 L120-L147） |
| `app.py` | 可选：`<head>` 区域添加 Google Fonts 引用 |

改动集中在 `render_password_gate()` 一个函数内，不影响其他页面。

---

## 五、效果对比

| 维度 | 改前 | 改后 |
|------|------|------|
| 字体 | 默认宋体 | Georgia / 衬线体，更优雅 |
| 标题 | 静态文字 | 呼吸光晕动画 |
| 输入框 | 白色底 | 暗色半透明 + 紫色边框 |
| 按钮 | Streamlit 蓝色 | 紫色渐变 |
| 密码卡片 | 简单半透明 | 毛玻璃 + 多层阴影 |
| 星空氛围 | 无星星 | 5-6 颗闪烁星星 |
| 管理员入口 | `#555` 灰字 | 主题暗紫，hover 提亮 |

---

## 六、实施建议

1. **分两次提交**：第一次改字体 + 控件样式（覆盖范围大但风险低），第二次加动画 + 星星（纯增量）
2. **字体降级**：优先 `Georgia` 不加载外部资源，`Noto Serif SC` 后续可选加
3. **测试点**：移动端 Safari 中 Star 元素位置是否正常、Chrome 中 `backdrop-filter` 兼容性
