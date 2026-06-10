# AI + Selenium Web 自动化测试框架

> **智能定位 · 自愈修复 · 自然语言驱动**  
> 用 AI 大语言模型驱动元素定位，Selenium 作为执行引擎，pytest 作为测试框架。

---

## 目录

- [快速开始](#快速开始)
- [核心特性](#核心特性)
- [项目结构](#项目结构)
- [运行测试](#运行测试)
- [🗣️ 自然语言测试](#️-自然语言测试)
- [AI 元素定位](#ai-元素定位)
- [登录测试说明](#登录测试说明)
- [配置说明](#配置说明)
- [CI/CD](#cicd)
- [FAQ](#faq)

---

## 快速开始

### 环境要求

- Python >= 3.10
- Chrome / Firefox / Edge 浏览器
- （可选）Tesseract OCR —— 用于验证码自动识别

### 安装

#### macOS / Linux

```bash
# 克隆项目
git clone https://gitee.com/burebaobao/ai-selenium-framework.git
cd ai-selenium-framework

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### Windows

```powershell
# 克隆项目
git clone https://gitee.com/burebaobao/ai-selenium-framework.git
cd ai-selenium-framework

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

> ⚠️ **Windows 注意**：使用 `python` 而不是 `python3`，路径分隔符用 `\`。

### Windows 环境准备（详细）

<details>
<summary>点击展开 Windows 完整安装步骤</summary>

#### 1. 安装 Python

- 从 [python.org](https://www.python.org/downloads/) 下载 Python >= 3.10
- **安装时勾选 "Add Python to PATH"**
- 安装后验证：
  ```powershell
  python --version
  pip --version
  ```

#### 2. 安装浏览器

- **Chrome**：[google.cn/chrome](https://www.google.cn/chrome/)
- 浏览器驱动由 `webdriver-manager` 自动管理，无需手动下载

#### 3. 安装 Git

- 从 [git-scm.com](https://git-scm.com/download/win) 下载安装
- 使用默认选项即可

#### 4. （可选）安装 Tesseract OCR

用于验证码自动识别。不安装不影响框架运行，只是验证码需要手动输入。

- 下载安装包：[GitHub UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
- 选择 **64位** 版本（如 `tesseract-ocr-w64-setup-5.x.x.exe`）
- 安装时勾选 **简体中文** 语言包
- 安装后添加到 PATH：
  ```powershell
  # 查看安装路径（默认）
  dir "C:\Program Files\Tesseract-OCR\tesseract.exe"

  # 手动添加到 PATH（以管理员身份运行 PowerShell）
  [Environment]::SetEnvironmentVariable(
      "Path",
      [Environment]::GetEnvironmentVariable("Path", "Machine") + ";C:\Program Files\Tesseract-OCR",
      "Machine"
  )

  # 验证
  tesseract --version
  ```

#### 5. 安装 Visual C++ 运行时

某些 Python 包需要 VC++ 运行时，如果 `pip install` 报错 `Microsoft Visual C++ 14.0 is required`：

- 下载 [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- 安装时选择 **"使用 C++ 的桌面开发"** 工作负载

#### 6. 验证安装

```powershell
# 激活虚拟环境后执行
cd ai-selenium-framework
.venv\Scripts\activate
pytest tests/test_login.py::TestLogin::test_login_page_loads -v --headless
```

看到 `PASSED` 表示全部就绪。

</details>

### 第一个测试

```bash
# 运行冒烟测试（页面加载验证，不需要验证码）
pytest tests/test_login.py::TestLogin::test_login_page_loads -v --headless
```

看到 `PASSED` 表示环境跑通了。

---

## 核心特性

### 🤖 AI 元素定位

传统 `find_element` 失败时，AI 引擎自动接管：

```
定位失败 (NoSuchElementException)
        ↓
AI 分析页面 HTML + 语义描述
        ↓
生成最佳定位策略 (CSS/XPath/文本/aria)
        ↓
验证定位器有效性
        ↓
自动修复 or 标记待审核
```

**代码示例：**

```python
# 传统方式（定位器写死）
login_btn = driver.find_element(By.ID, "login-btn")

# AI 方式（语义描述 + 传统定位回退）
self.element("登录按钮", locator=(By.ID, "login-btn")).click()
# → 如果 #login-btn 找不到，AI 自动分析页面找到真正的登录按钮
```

### 🔧 自愈引擎

页面 UI 改版后，定位器断掉也能自动修复：

| 场景 | 传统框架 | 本框架 |
|------|---------|--------|
| ID 变更 | ❌ 用例挂了 | ✅ AI 找到新 ID |
| 类名修改 | ❌ 手动改代码 | ✅ 自动修复 + 记录 |
| DOM 重构 | ❌ 从头查元素 | ✅ 语义定位 |
| 前端升级 | ❌ 大批量维护 | ✅ 渐进适应 |

### 📝 自然语言生成

（预留能力）描述操作即可生成测试脚本：

```yaml
# test_cases.yaml
- case: "打开登录页，输入账号密码，点击登录，验证跳转到首页"
```

---

## 项目结构

```
ai-selenium-framework/
│
├── core/                        # 核心引擎
│   ├── ai_locator.py            #   AI 元素定位器
│   ├── heal_engine.py           #   自愈引擎
│   ├── driver_factory.py        #   多浏览器驱动工厂
│   └── captcha_solver.py        #   验证码识别器
│
├── pages/                       # Page Object 页面对象
│   ├── base_page.py             #   AI 增强基类
│   └── login_page.py            #   登录页对象
│
├── tests/                       # 测试用例
│   ├── conftest.py              #   pytest 全局配置
│   └── test_login.py            #   登录功能测试
│
├── utils/                       # 工具类
│   ├── ai_client.py             #   LLM 客户端
│   └── logger.py                #   日志
│
├── config/                      # 配置
│   ├── settings.py              #   配置管理
│   └── config.yaml              #   全局配置
│
├── element_repository/          # 自愈元素仓库
│   ├── elements.yaml            #   元素定位器
│   └── healing_log.jsonl        #   自愈日志
│
├── scripts/
│   └── get_captcha.py           #   验证码获取脚本
│
├── reports/                     # 报告输出
│   ├── screenshots/             #   失败截图
│   ├── captcha/                 #   验证码图片
│   └── allure-results/          #   Allure 数据
│
└── requirements.txt             # 依赖清单
```

---

## 运行测试

### 全部测试

```bash
pytest tests/
```

### 指定浏览器

```bash
pytest tests/ --browser chrome     # Chrome（默认）
pytest tests/ --browser firefox    # Firefox
pytest tests/ --browser edge       # Edge
```

### 无头模式

```bash
pytest tests/ --headless
```

### 并发执行

```bash
pip install pytest-xdist
pytest tests/ -n 4                # 4 个线程并行
```

### 失败重试

```bash
pip install pytest-rerunfailures
pytest tests/ --reruns 2 --reruns-delay 3
```

### 标签过滤

```bash
pytest tests/ -m smoke              # 只跑冒烟测试
pytest tests/ -m "not manual_captcha"  # 跳过手动验证码测试
```

### 生成报告

```bash
# 安装 Allure（macOS）
brew install allure

# Windows: 从 https://github.com/allure-framework/allure2/releases 下载
# 解压后添加到 PATH，然后：
allure serve reports/allure-results
```

---

## 🗣️ 自然语言测试

用一句话描述操作，框架自动生成并执行测试。

### 一键执行

```bash
# macOS / Linux
python scripts/run_nl_test.py "打开 https://example.com，点击登录按钮，等待2秒，截图" --headless

# Windows PowerShell
python scripts/run_nl_test.py "打开 https://example.com，点击登录按钮，等待2秒，截图" --headless
```

支持的描述模式：

```
打开 https://...            → 导航到页面
在搜索框输入 AI测试          → 在元素中输入文本
点击登录按钮                 → 点击元素
等待3秒                      → 等待指定秒数
截图                         → 保存页面截图
验证标题包含 首页            → 断言页面标题
验证结果包含 成功            → 断言元素文本
悬停到菜单                   → 悬停到元素
滚动到底部                   → 滚动到元素
```

### 发现模式：AI 分析页面元素

```bash
# 告诉框架要找哪些元素，AI 自动分析页面并返回定位策略
# macOS / Linux
python scripts/run_nl_test.py --discover "https://example.com/login" "登录按钮,用户名输入框,密码输入框"

# Windows
python scripts/run_nl_test.py --discover "https://example.com/login" "登录按钮,用户名输入框,密码输入框"
```

输出示例：
```
🔍 正在打开: https://example.com/login
🎯 目标元素: 登录按钮, 用户名输入框, 密码输入框

  ✅ [登录按钮]
     定位方式: css_selector
     定位值:   .login-btn
     置信度:   92%
```

### 运行已生成的测试

```bash
python scripts/run_nl_test.py --run tests/ai_generated/
```

### 带验证码的登录测试

```bash
# 1. 获取验证码图片
python scripts/get_captcha.py

# 2. 注入验证码（Windows PowerShell 语法）
$env:CAPTCHA_TEXT='看到的验证码'
$env:CAPTCHA_ID='获取到的ID'
python scripts/run_nl_test.py "打开 https://user.hxapp.vip/pc/#/login，在邮箱输入框输入 your@email.com，在密码输入框输入 your_password，在验证码输入框输入，点击登录按钮" --headless
```

---

## AI 元素定位

### 基本用法

项目使用 `AIElement` 类包装元素，定位策略按优先级降级：

```python
from pages.base_page import BasePage

class MyPage(BasePage):
    @property
    def search_input(self):
        # 优先级 1: 传统定位（ID/class 等稳定属性）
        # 优先级 2: AI 语义定位（分析 HTML 自动查找）
        return self.element(
            "搜索输入框",                    # 语义描述
            locator=(By.ID, "search-input")  # 可选的传统定位
        )

    @property
    def search_button(self):
        return self.element("搜索按钮")
```

### 配置 AI 提供商

在 `.env` 文件中配置：

```bash
# Claude（推荐）
AI_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx

# 或者 OpenAI
# AI_PROVIDER=openai
# OPENAI_API_KEY=sk-xxxxxxxxxxxx

# 或者本地模型（Ollama）
# AI_PROVIDER=local
# LOCAL_MODEL_URL=http://localhost:11434/v1
# LOCAL_MODEL_NAME=qwen2.5:7b
```

> **注意**：不配置 API Key 也能运行，框架会使用模拟响应（mock 模式），适合开发调试。

### 自愈控制

```bash
# 启用自愈（默认开启）
pytest tests/ --ai-heal

# 禁用自愈
pytest tests/ --no-ai-heal
```

---

## 登录测试说明

本框架内置了一个目标网站的登录测试作为参考案例。

### 测试用例

| 用例 | 描述 | 需要验证码 |
|------|------|-----------|
| `test_login_page_loads` | 页面加载和元素可见性验证 | ❌ |
| `test_login_form_fields` | 表单输入功能验证 | ❌ |
| `test_login_via_api` | 通过 API 登录 | ✅ |
| `test_login_with_manual_captcha` | 通过 UI 点击登录 | ✅ |

### 验证码处理流程

该网站使用图形验证码，框架支持三种处理策略：

```
环境变量 CAPTCHA_TEXT  →  直接使用（适合 CI/预设）
        ↓ 不设置
Tesseract OCR 识别     →  自动尝试
        ↓ 识别失败
人工查看并输入         →  保存图片提示用户
```

### 带验证码的运行方式

**方式一：手动获取 + 注入（推荐）**

```bash
# 步骤 1: 获取验证码图片
python scripts/get_captcha.py

# 输出类似:
#   验证码图片: /path/to/reports/captcha/captcha.png
#   Captcha ID: xxxxxx

# 步骤 2: 打开图片查看验证码文字
open reports/captcha/captcha.png          # macOS
# start reports/captcha/captcha.png       # Windows
# xdg-open reports/captcha/captcha.png    # Linux

# 步骤 3: 用环境变量传入验证码，运行测试
# macOS / Linux:
CAPTCHA_TEXT='<看到的文字>' CAPTCHA_ID='<输出的ID>' pytest tests/test_login.py -k "login_via_api"
# Windows PowerShell:
# $env:CAPTCHA_TEXT='<看到的文字>'; $env:CAPTCHA_ID='<输出的ID>'; pytest tests/test_login.py -k "login_via_api"
```

**方式二：直接通过程序运行（一次性）**

```python
from pages.login_page import LoginPage

page = LoginPage(driver)
# 调用 login_via_api 时传参
page.login_via_api(
    email="your@email.com",
    password="your_password",
    captcha_text="看到的验证码",    # 直接传入
    captcha_id="获取到的ID",
)
```

---

## 配置说明

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--browser` | 浏览器类型 | `chrome` |
| `--headless` | 无头模式 | `false` |
| `--ai-heal` | 启用 AI 自愈 | `true` |
| `--no-ai-heal` | 禁用 AI 自愈 | — |
| `--ai-provider` | AI 供应商 | `claude` |

### 环境变量

| 变量 | 说明 |
|------|------|
| `ANTHROPIC_API_KEY` | Claude API Key |
| `OPENAI_API_KEY` | OpenAI API Key |
| `AI_PROVIDER` | AI 供应商选择 |
| `BROWSER` | 默认浏览器 |
| `HEADLESS` | 是否无头模式 |
| `CAPTCHA_TEXT` | 预置验证码文字 |
| `CAPTCHA_ID` | 预置验证码 ID |

### 自愈阈值

在 `core/heal_engine.py` 中调整：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `auto_approve_threshold` | 0.85 | 置信度 ≥ 85% 自动采纳新定位器 |
| `max_retries` | 2 | 自愈最大重试次数 |

---

## CI/CD

### GitHub Actions

```yaml
name: UI Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pytest tests/ --headless --browser chrome
```

### Docker

```bash
# 构建
docker build -t ai-selenium-framework -f docker/Dockerfile .

# 运行
docker run ai-selenium-framework
```

---

## FAQ

### Q: 没有 AI API Key 能用吗？

可以。框架默认使用 mock 模式返回模拟定位结果。AI 定位功能需要配 API Key 才生效，但框架的基础功能（传统定位、自愈流程、测试执行）不依赖 AI。

### Q: Windows 和 macOS/Linux 命令有什么区别？

| 操作 | macOS / Linux | Windows |
|------|--------------|---------|
| Python 命令 | `python3` | `python` |
| 虚拟环境创建 | `python3 -m venv .venv` | `python -m venv .venv` |
| 激活虚拟环境 | `source .venv/bin/activate` | `.venv\Scripts\activate` |
| 设置环境变量 | `export KEY=val` | `$env:KEY='val'` (PowerShell) |

### Q: Windows 上 `pip install` 报错 `Microsoft Visual C++ 14.0 is required`？

某些 Python 包需要 C++ 编译环境。解决方法：

1. 下载 [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. 安装时勾选 **"使用 C++ 的桌面开发"**
3. 或安装 [VC++ 可再发行组件包](https://aka.ms/vs/17/release/vc_redist.x64.exe)

### Q: Windows 上虚拟环境激活报错 `execution policy`？

```powershell
# 以管理员身份运行 PowerShell 后执行
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
.venv\Scripts\activate
```

### Q: Windows 上如何运行自然语言测试？

```powershell
# 注意用 python 而不是 python3，环境变量用 $env:
$env:AI_PROVIDER='claude'; python scripts/run_nl_test.py "打开百度，搜索AI测试，验证标题包含 AI" --headless
```

### Q: 验证码总是识别失败怎么办？

该网站的验证码抗 OCR 能力较强。建议的使用方式：
1. 运行 `python scripts/get_captcha.py` 获取验证码图片
2. 人工查看图片中的文字
3. 用 `CAPTCHA_TEXT` 环境变量注入

### Q: 如何适配自己的网站？

以登录页为例：

```python
# pages/my_page.py
from pages.base_page import BasePage
from selenium.webdriver.common.by import By

class MyLoginPage(BasePage):
    url = "https://your-site.com/login"

    @property
    def username(self):
        return self.element("用户名输入框", locator=(By.ID, "username"))

    @property
    def password(self):
        return self.element("密码输入框", locator=(By.ID, "password"))

    @property
    def login_btn(self):
        return self.element("登录按钮", locator=(By.CSS_SELECTOR, ".login-btn"))
```

然后创建对应的测试文件即可。

### Q: 自愈记录在哪看？

自愈日志保存在 `element_repository/healing_log.jsonl`，每次自愈都会记录：

```json
{
  "timestamp": "2026-06-10T21:00:00",
  "old_by": "id",
  "old_value": "login-btn",
  "new_type": "css_selector",
  "new_value": ".header-login-button",
  "confidence": 0.95,
  "reasoning": "ID 从 login-btn 变更为动态 ID，使用 class 定位更稳定"
}
```

---

## 许可证

MIT
