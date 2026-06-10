"""
core/ai_generator.py

AI 测试脚本生成器
接收自然语言描述的操作步骤，自动生成可执行的 pytest 测试脚本。
"""

import ast
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from utils.ai_client import LLMClient

logger = logging.getLogger(__name__)

# 支持的操作类型
ActionType = Literal[
    "open",           # 打开页面
    "click",          # 点击元素
    "type",           # 输入文本
    "select",         # 下拉选择
    "assert_text",    # 断言文本
    "assert_title",   # 断言标题
    "assert_url",     # 断言 URL
    "assert_visible", # 断言元素可见
    "wait",           # 等待
    "screenshot",     # 截图
    "hover",          # 悬停
    "scroll_to",      # 滚动到元素
]


@dataclass
class TestStep:
    """单个测试步骤"""
    action: ActionType
    element_desc: str = ""          # 元素语义描述，如"登录按钮"
    value: str = ""                 # 输入的值 / 断言的值
    locator: tuple[str, str] | None = None  # (by, value) 可选的传统定位器
    description: str = ""           # 步骤说明


@dataclass
class GeneratedTest:
    """生成的测试产物"""
    filepath: str                   # 生成的测试文件路径
    test_code: str                  # 测试代码
    page_object_code: str           # Page Object 代码
    steps: list[TestStep]           # 解析后的步骤
    element_mappings: dict          # 元素描述 → 定位器映射
    page_object_name: str           # Page Object 类名


class AITestGenerator:
    """
    AI 测试脚本生成器

    用法:
        generator = AITestGenerator()
        result = await generator.generate("打开百度，输入AI测试，点击搜索按钮")
        # → 生成 tests/ai_generated/test_baidu_search.py

    也支持同步调用:
        result = generator.generate_sync("打开登录页，输入用户名...")
    """

    def __init__(
        self,
        provider: str = "claude",
        output_dir: str = "tests/ai_generated",
        base_url: str = "",
    ):
        self._client = LLMClient(provider=provider)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url

    # ================================================================
    # 公共入口
    # ================================================================

    async def generate(self, description: str, project: str = "auto") -> GeneratedTest:
        """
        从自然语言描述生成完整的 pytest 测试

        Args:
            description: 自然语言描述
                "打开百度，在搜索框输入'AI测试'，点击搜索按钮，验证标题包含'AI测试'"
            project: 项目名，用于文件命名

        Returns:
            GeneratedTest 包含文件路径、代码、步骤等
        """
        # 1. 解析自然语言为结构化步骤
        steps = await self._parse_steps(description)
        logger.info(f"[AI生成] 解析到 {len(steps)} 个步骤")

        # 2. 提取 Page Object 名称
        po_name = self._extract_po_name(steps, project)

        # 3. 生成 Page Object 代码
        po_code = self._generate_page_object(po_name, steps)

        # 4. 生成测试代码
        test_code = self._generate_test_code(po_name, steps)

        # 5. 写入文件
        filepath = self._write_test_file(po_name, test_code, po_code)

        # 6. 构建元素映射
        element_mappings = {
            s.element_desc: s.locator
            for s in steps
            if s.element_desc and s.locator
        }

        logger.info(f"[AI生成] ✓ 测试已生成: {filepath}")
        return GeneratedTest(
            filepath=filepath,
            test_code=test_code,
            page_object_code=po_code,
            steps=steps,
            element_mappings=element_mappings,
            page_object_name=po_name,
        )

    def generate_sync(self, description: str, project: str = "auto") -> GeneratedTest:
        """同步版本的 generate"""
        import asyncio
        return asyncio.run(self.generate(description, project))

    # ================================================================
    # 步骤 1: 自然语言 → 结构化步骤
    # ================================================================

    async def _parse_steps(self, description: str) -> list[TestStep]:
        """AI 解析自然语言为步骤列表"""
        prompt = f"""你是一个 Web 自动化测试专家。请将以下的测试描述解析为结构化的步骤列表。

## 规则
- 每个步骤包含: action(操作类型) + element_desc(元素描述) + value(值)
- 操作类型必须是以下之一:
  - open: 打开页面，element_desc 填 URL，value 填完整 URL
  - click: 点击元素，element_desc 填元素描述
  - type: 输入文本，element_desc 填元素描述，value 填要输入的内容
  - assert_text: 断言元素文本，element_desc 填元素描述，value 填期望文本
  - assert_title: 断言页面标题，value 填期望标题
  - assert_url: 断言 URL，value 填期望 URL 片段
  - wait: 等待，value 填秒数
  - screenshot: 截图
  - hover: 悬停到元素
  - scroll_to: 滚动到元素

## 输入
{description}

## 输出
请严格返回 JSON 数组（不要 markdown 格式）:
[
  {{
    "action": "open",
    "element_desc": "",
    "value": "https://example.com",
    "description": "打开示例网站"
  }},
  {{
    "action": "type",
    "element_desc": "搜索输入框",
    "value": "AI测试",
    "description": "在搜索框输入 AI 测试"
  }}
]
"""
        try:
            response = await self._client.ask(prompt)
            data = json.loads(self._extract_json(response))
            steps = []
            for item in data:
                step = TestStep(
                    action=item.get("action", "click"),
                    element_desc=item.get("element_desc", ""),
                    value=item.get("value", ""),
                    description=item.get("description", ""),
                )
                steps.append(step)
            return steps
        except Exception as e:
            logger.error(f"[AI生成] 解析步骤失败: {e}")
            return self._fallback_parse(description)

    def _fallback_parse(self, description: str) -> list[TestStep]:
        """当 AI 解析失败时的兜底解析（覆盖常见中文模式）"""
        steps = []

        # 1. 打开页面
        if m := re.search(r"打开\s*(.+?)(?:$|，|,|\.)", description):
            url = m.group(1).strip()
            if not url.startswith("http"):
                url = self.base_url or f"https://{url}"
            steps.append(TestStep(action="open", value=url, description=f"打开{url}"))

        # 2. 等待 X 秒 / 暂停
        for m in re.finditer(r"(?:等待|暂停|等)\s*(\d+)\s*(?:秒|s|)", description):
            steps.append(TestStep(action="wait", value=m.group(1), description=f"等待{m.group(1)}秒"))

        # 3. 截图
        if re.search(r"(?:截图|截屏|截图保存|screen)", description, re.I):
            steps.append(TestStep(action="screenshot", description="截图"))

        # 4. 在 X 输入 Y (在搜索框输入AI测试)
        for m in re.finditer(r"在\s*(.+?)(?:输入|键入|填写)\s*[`'\"「」『』【】]?(.+?)[`'\"「」『』【】]?(?:$|，|,|。|的)", description):
            steps.append(TestStep(
                action="type",
                element_desc=m.group(1).strip(),
                value=m.group(2).strip(),
                description=f"在{m.group(1).strip()}输入{m.group(2).strip()}",
            ))

        # 5. 直接输入 X (输入admin)
        for m in re.finditer(r"(?<!在\s)(?:输入|键入|填写)\s*[`'\"「」『』【】]?(.+?)[`'\"「」『』【】]?(?:$|，|,|。)", description):
            steps.append(TestStep(
                action="type",
                element_desc="输入框",
                value=m.group(1).strip(),
                description=f"输入{m.group(1).strip()}",
            ))

        # 6. 点击 X
        for m in re.finditer(r"点击\s*(.+?)(?:$|，|,|。)", description):
            steps.append(TestStep(
                action="click",
                element_desc=m.group(1).strip(),
                description=f"点击{m.group(1).strip()}",
            ))

        # 7. 验证/断言 X 包含/是/为 Y
        for m in re.finditer(r"(?:验证|断言|检查|检测)\s*(.+?)(?:包含|含有|为|是|等于)\s*[`'\"「」『』【】]?(.+?)[`'\"「」『』【】]?(?:$|，|,|。)", description):
            steps.append(TestStep(
                action="assert_text",
                element_desc=m.group(1).strip(),
                value=m.group(2).strip(),
                description=f"验证{m.group(1).strip()}包含{m.group(2).strip()}",
            ))

        # 8. 验证/断言标题包含 Y
        for m in re.finditer(r"(?:标题|页面标题)\s*(?:包含|含有|为|是)\s*[`'\"「」『』【】]?(.+?)[`'\"「」『』【】]?", description):
            steps.append(TestStep(
                action="assert_title",
                value=m.group(1).strip(),
                description=f"验证标题包含{m.group(1).strip()}",
            ))

        # 9. 滚动到 X
        for m in re.finditer(r"滚动到\s*(.+?)(?:$|，|,|。)", description):
            steps.append(TestStep(
                action="scroll_to",
                element_desc=m.group(1).strip(),
                description=f"滚动到{m.group(1).strip()}",
            ))

        # 10. 悬停到 X
        for m in re.finditer(r"(?:悬停|移到|hover)\s*(.+?)(?:$|，|,|。)", description):
            steps.append(TestStep(
                action="hover",
                element_desc=m.group(1).strip(),
                description=f"悬停到{m.group(1).strip()}",
            ))

        if not steps:
            steps.append(TestStep(action="open", value=self.base_url or "about:blank"))

        return steps

    # ================================================================
    # 步骤 2: 提取 Page Object 名称
    # ================================================================

    def _extract_po_name(self, steps: list[TestStep], project: str) -> str:
        """从步骤中提取合适的 PO 名称"""
        for s in steps:
            if s.action == "open" and s.value:
                # 从 URL 提取网站名
                if m := re.search(r"//([^.]+)", s.value):
                    name = m.group(1).capitalize() + "Page"
                    return name
                if m := re.search(r"(\w+)\.\w+", s.value):
                    name = m.group(1).capitalize() + "Page"
                    return name
        return project.capitalize() + "Page"

    # ================================================================
    # 步骤 3: 生成 Page Object 代码
    # ================================================================

    def _generate_page_object(self, po_name: str, steps: list[TestStep]) -> str:
        """生成 Page Object 代码"""
        elements = set()
        for s in steps:
            if s.element_desc:
                elements.add(s.element_desc)

        elem_properties = []
        for desc in elements:
            prop_name = self._desc_to_var(desc)
            elem_properties.append(f"""    @property
    def {prop_name}(self):
        return self.element("{desc}")""")

        elem_code = "\n".join(elem_properties) if elem_properties else "    pass"

        # 提取 base_url
        base_url = ""
        for s in steps:
            if s.action == "open" and s.value:
                base_url = s.value
                break

        return f'''"""
Page Object: {po_name}
AI 自动生成 — {datetime.now().strftime("%Y-%m-%d %H:%M")}
"""

from pages.base_page import BasePage


class {po_name}(BasePage):
    """{"页面对象" if not po_name.endswith("Page") else po_name}"""

    url = "{base_url}"

{elem_code}
'''

    # ================================================================
    # 步骤 4: 生成测试代码
    # ================================================================

    def _generate_test_code(self, po_name: str, steps: list[TestStep]) -> str:
        """生成 pytest 测试代码"""
        po_filename = self._page_file_name(po_name)
        po_class = po_filename.replace("_", " ").title().replace(" ", "") + "Page"

        test_methods = []

        # 主测试方法
        test_body_lines = []
        page_var = po_filename + "_page"

        for i, step in enumerate(steps):
            indent = "        "
            if step.action == "open":
                if step.value:
                    test_body_lines.append(f'{indent}self.{page_var}.open("{step.value}")')
                else:
                    test_body_lines.append(f'{indent}self.{page_var}.open()')
                test_body_lines.append(f'{indent}self.{page_var}.wait_for_page_loaded()')

            elif step.action == "click":
                prop = self._desc_to_var(step.element_desc)
                test_body_lines.append(f'{indent}self.{page_var}.{prop}.click()')

            elif step.action == "type":
                prop = self._desc_to_var(step.element_desc)
                safe_val = step.value.replace("'", "\\'").replace('"', '\\"')
                test_body_lines.append(f'{indent}self.{page_var}.{prop}.input("{safe_val}")')

            elif step.action == "assert_text":
                prop = self._desc_to_var(step.element_desc)
                safe_val = step.value.replace("'", "\\'").replace('"', '\\"')
                test_body_lines.append(f'{indent}assert "{safe_val}" in self.{page_var}.{prop}.get_text()')

            elif step.action == "assert_title":
                safe_val = step.value.replace("'", "\\'").replace('"', '\\"')
                test_body_lines.append(f'{indent}assert "{safe_val}" in self.driver.title')

            elif step.action == "assert_url":
                safe_val = step.value.replace("'", "\\'").replace('"', '\\"')
                test_body_lines.append(f'{indent}assert "{safe_val}" in self.driver.current_url')

            elif step.action == "wait":
                secs = step.value or "2"
                test_body_lines.append(f'{indent}import time; time.sleep({secs})')

            elif step.action == "screenshot":
                test_body_lines.append(f'{indent}self.{page_var}.take_screenshot("step_{i}")')

        test_body = "\n".join(test_body_lines)

        # 生成测试方法名称
        desc_text = " ".join(s.description for s in steps if s.description)[:60]
        test_name = "test_" + re.sub(r'[^a-zA-Z0-9一-鿿]', '_', desc_text)[:40].lower().strip("_")
        if not test_name or test_name == "test_":
            test_name = f"test_ai_generated_{datetime.now().strftime('%H%M%S')}"

        return f'''"""
Test: {desc_text or "AI 自动生成测试"}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Framework: AI + Selenium
"""

import pytest
from pages.ai_generated.{po_filename} import {po_class}


class Test{po_class}:
    """AI 生成的自动化测试"""

    @pytest.fixture(autouse=True)
    def setup(self, request, driver):
        self.driver = driver
        self.{page_var} = {po_class}(driver)
        yield

    @pytest.mark.ai_generated
    def {test_name}(self):
        """{" -> ".join(s.description for s in steps if s.description)}"""
{test_body}
'''

    # ================================================================
    # 步骤 5: 写入文件
    # ================================================================

    def _write_test_file(self, project: str, test_code: str, po_code: str) -> str:
        """写入测试文件和 Page Object 文件"""
        pages_dir = Path("pages/ai_generated")
        pages_dir.mkdir(parents=True, exist_ok=True)
        (pages_dir / "__init__.py").touch(exist_ok=True)
        test_dir = self.output_dir
        test_dir.mkdir(parents=True, exist_ok=True)
        (test_dir / "__init__.py").touch(exist_ok=True)

        po_filename = self._page_file_name(project)
        po_class = po_filename.replace("_", " ").title().replace(" ", "") + "Page"

        # 修正 PO 代码中的类名
        replaced_po = re.sub(
            r"class\s+\w+Page",
            f"class {po_class}",
            po_code
        )

        # 写入 PO 文件到 pages/ai_generated/
        po_file = pages_dir / f"{po_filename}.py"
        if not po_file.exists():
            po_file.write_text(replaced_po, encoding="utf-8")
            logger.info(f"[AI生成] 写入 Page Object: {po_file}")

        # 写入测试文件
        test_name = f"test_{po_filename}"
        test_path = str(test_dir / f"{test_name}.py")
        Path(test_path).write_text(test_code, encoding="utf-8")
        logger.info(f"[AI生成] 写入测试文件: {test_path}")

        return test_path

    # ================================================================
    # 工具方法
    # ================================================================

    def _desc_to_var(self, desc: str) -> str:
        """将中文描述转为合法的 Python 变量名"""
        var = desc.strip()
        # 中文转拼音近似（直接去除中文，保留英文数字）
        var = re.sub(r'[^\w]', '_', var)
        var = re.sub(r'_+', '_', var).strip('_')
        if not var:
            var = "element"
        if var[0].isdigit():
            var = "el_" + var
        return var.lower()

    def _page_file_name(self, project: str) -> str:
        """生成 Page Object 文件名"""
        name = re.sub(r'[A-Z]', lambda m: '_' + m.group(0).lower(), project)
        name = name.strip('_')
        return name.replace("_page", "").replace("__", "_").strip("_") or "page"

    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON 数组/对象"""
        # 尝试匹配 ```json ... ``` 块
        if m := re.search(r'```(?:json)?\s*([\s\S]*?)```', text):
            return m.group(1).strip()
        # 尝试匹配 `[...]` 或 `{...}`
        if m := re.search(r'(\[[\s\S]*?\]|\{[\s\S]*\})', text):
            return m.group(1).strip()
        return text


# ================================================================
# 便捷函数：一行命令生成并执行
# ================================================================

def generate_and_run(description: str, **kwargs) -> bool:
    """
    一句话：生成测试并立即执行

    Args:
        description: "打开百度，搜索AI"
        kwargs: 传给 pytest 的额外参数（--headless, --browser 等）

    Returns:
        True=测试全部通过
    """
    import asyncio
    import subprocess
    import sys

    generator = AITestGenerator()
    result = asyncio.run(generator.generate(description))

    print(f"\n{'='*50}")
    print(f"📄 测试文件: {result.filepath}")
    print(f"📋 步骤数: {len(result.steps)}")
    print(f"{'='*50}\n")

    # 运行生成的测试
    cmd = [
        sys.executable, "-m", "pytest", result.filepath,
        "-v", "--tb=short",
    ]
    for k, v in kwargs.items():
        flag = f"--{k.replace('_', '-')}"
        if isinstance(v, bool) and v:
            cmd.append(flag)
        elif not isinstance(v, bool):
            cmd.extend([flag, str(v)])

    result_run = subprocess.run(cmd, capture_output=False)
    return result_run.returncode == 0
