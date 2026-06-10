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
- [🧪 完整上手指南：以百度搜索为例](#-完整上手指南以百度搜索为例)
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
# 使用框架自带的 AI 发现模式验证
cd ai-selenium-framework
.venv\Scripts\activate
python scripts/run_nl_test.py --discover "https://www.baidu.com" "搜索输入框,百度一下按钮"
```

看到 AI 返回元素定位结果表示全部就绪。

</details>

### 第一个测试（不需要验证码）

```bash
# 使用 AI 发现模式：打开任意页面，让 AI 分析元素
python scripts/run_nl_test.py --discover "https://www.baidu.com" "搜索输入框,搜索按钮"

# 或直接跑自带的 demo 页面加载验证
pytest tests/ -v --headless -k "test_login_page_loads"
```

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

---

## 🧪 完整上手指南：以百度搜索为例

从零开始，一步步演示如何用自然语言完成一个完整的 Web 自动化测试。

### 第 1 步：发现元素

先让 AI 去百度首页看一看，找到我们要操作的页面元素：

```bash
python scripts/run_nl_test.py --discover "https://www.baidu.com" "搜索输入框,百度一下按钮"
```

输出：

```
🔍 正在打开: https://www.baidu.com
🎯 目标元素: 搜索输入框, 百度一下按钮

  ✅ [搜索输入框]
     定位方式: css_selector
     定位值:   #kw
     置信度:   92%
     说明:     通过 id='kw' 定位搜索输入框

  ✅ [百度一下按钮]
     定位方式: css_selector
     定位值:   #su
     置信度:   90%
     说明:     通过 id='su' 定位搜索按钮
```

> AI 帮你找到了：搜索框是 `#kw`，搜索按钮是 `#su`。

### 第 2 步：配环境变量（可选）

```bash
# macOS / Linux
export AI_PROVIDER=claude

# Windows PowerShell
# $env:AI_PROVIDER='claude'
```

不配也行，框架用 mock 模式也能运行（定位器为模拟结果，不影响流程演示）。

### 第 3 步：一句话执行测试

```bash
python scripts/run_nl_test.py "打开 https://www.baidu.com，在搜索输入框输入 AI测试，点击百度一下按钮，等待3秒，验证标题包含 AI测试" --headless
```

执行过程：

```
📝 自然语言描述: 打开 https://www.baidu.com，在搜索输入框输入 AI测试，点击百度一下按钮，等待3秒，验证标题包含 AI测试

📄 生成测试文件: tests/ai_generated/test_baidu.py
📋 解析步骤 (4 步):
  🌐 步骤1: 打开https://www.baidu.com
  ⌨️ 步骤2: 在搜索输入框输入AI测试
  👆 步骤3: 点击百度一下按钮
  ⏳ 步骤4: 等待3秒
  ✅ 步骤5: 标题包含AI测试

▶️  正在执行测试...

tests/ai_generated/test_baidu.py ✓ PASSED [100%]

✅ 测试全部通过！
```

整个过程：**描述 → 生成 → 执行 → 报告**，一行命令完成。

### 第 4 步：查看生成的代码

框架执行完后，会自动保留生成的测试文件，供后续复用或修改：

```bash
# 查看生成的 Page Object
cat pages/ai_generated/baidu.py

# 查看生成的测试代码
cat tests/ai_generated/test_baidu.py
```

**生成的 Page Object** (`pages/ai_generated/baidu.py`)：

```python
"""
Page Object: BaiduPage
AI 自动生成
"""

from pages.base_page import BasePage


class BaiduPage(BasePage):
    """百度搜索页面"""

    url = "https://www.baidu.com"

    @property
    def 搜索输入框(self):
        return self.element("搜索输入框")

    @property
    def 百度一下按钮(self):
        return self.element("百度一下按钮")
```

**生成的测试代码** (`tests/ai_generated/test_baidu.py`)：

```python
"""
Test: 打开https://www.baidu.com -> 在搜索输入框输入AI测试 -> 点击百度一下按钮 -> 等待3秒 -> 标题包含AI测试
Generated: 2026-06-10 22:30:00
Framework: AI + Selenium
"""

import pytest
from pages.ai_generated.baidu import BaiduPage


class TestBaiduPage:
    """AI 生成的自动化测试"""

    @pytest.fixture(autouse=True)
    def setup(self, request, driver):
        self.driver = driver
        self.baidu_page = BaiduPage(driver)
        yield

    @pytest.mark.ai_generated
    def test_打开百度搜索AI测试(self):
        """打开https://www.baidu.com -> 在搜索输入框输入AI测试 -> 点击百度一下按钮 -> 等待3秒 -> 验证标题包含AI测试"""
        self.baidu_page.open("https://www.baidu.com")
        self.baidu_page.wait_for_page_loaded()
        self.baidu_page.搜索输入框.input("AI测试")
        self.baidu_page.百度一下按钮.click()
        import time; time.sleep(3)
        assert "AI测试" in self.driver.title
```

### 第 5 步：复用和定制

生成后的测试文件可以直接用 pytest 反复运行，不再需要 AI：

```bash
# 直接运行已生成的测试
pytest tests/ai_generated/test_baidu.py -v --headless

# 或批量运行所有 AI 生成的测试
pytest tests/ai_generated/ -v --headless

# 修改测试后再次运行（改动会保留）
```

也可以在生成代码的基础上手动调整，比如增加更多断言、参数化测试数据等。

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

## 📖 Demo：登录测试参考

> **⚠️ 以下为框架验证用的 Demo，与你实际要测的网站无关。**  
> 核心框架本身**不绑定任何网站**，适配自己的网站见 [FAQ 中的方法](#q-如何适配自己的网站)。

`tests/test_login.py` + `pages/login_page.py` 是框架能力的参考实现，演示了：

- 页面加载验证（`test_login_page_loads`）
- 表单操作测试（`test_login_form_fields`）
- API 方式登录（`test_login_via_api`）
- UI 点击登录（`test_login_with_manual_captcha`）

### 验证码处理策略（框架通用能力）

```
环境变量 CAPTCHA_TEXT  →  直接使用（适合 CI / 预设）
        ↓ 不设置
Tesseract OCR 识别     →  自动尝试
        ↓ 识别失败
人工查看并输入         →  保存图片，提示用户
```

### 运行 Demo

```bash
# 不需要验证码的两个测试
pytest tests/test_login.py -k "test_login_page_loads or test_login_form_fields" -v --headless

# 需要验证码时，注入环境变量
# macOS / Linux:
CAPTCHA_TEXT='xxx' CAPTCHA_ID='xxx' pytest tests/test_login.py -k "login_via_api" -v --headless
# Windows PowerShell:
# $env:CAPTCHA_TEXT='xxx'; $env:CAPTCHA_ID='xxx'; pytest tests/test_login.py -k "login_via_api" -v --headless
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
