"""
core/ai_locator.py

AI 驱动的元素定位引擎
使用大语言模型分析页面 DOM，在传统定位器失效时定位元素。
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Literal

from utils.ai_client import LLMClient

logger = logging.getLogger(__name__)

LocatorType = Literal[
    "css_selector", "xpath", "text", "aria_label", "id", "name", "class_name"
]


@dataclass
class LocatorResult:
    """AI 定位结果"""

    found: bool
    locator_type: LocatorType = "css_selector"
    locator_value: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    fallback_strategies: list[dict] = field(default_factory=list)


class AIElementLocator:
    """
    AI 元素定位器

    当传统的 find_element 找不到元素时，
    将页面 HTML 和元素语义描述发给 LLM 进行分析，
    返回最佳定位策略。
    """

    def __init__(
        self,
        provider: Literal["claude", "openai", "local"] = "claude",
        api_key: str | None = None,
        model: str | None = None,
    ):
        self._client = LLMClient(provider=provider, api_key=api_key, model=model)
        self._cache: dict[str, LocatorResult] = {}

    # ---------------------------------------------------------------
    # 公共接口
    # ---------------------------------------------------------------

    async def locate(
        self,
        page_source: str,
        element_desc: str,
        url: str = "",
        use_cache: bool = True,
    ) -> LocatorResult:
        """
        定位元素

        Args:
            page_source: 页面 HTML 源码
            element_desc: 元素语义描述（如 "登录按钮"、"搜索输入框"）
            url: 当前页面 URL，用于上下文
            use_cache: 是否使用缓存

        Returns:
            LocatorResult 定位结果
        """
        cache_key = f"{element_desc}|{url}"

        if use_cache and cache_key in self._cache:
            logger.info(f"[AI定位] 命中缓存: {element_desc}")
            return self._cache[cache_key]

        cleaned = self._clean_html(page_source)
        prompt = self._build_prompt(cleaned, element_desc, url)

        try:
            response = await self._client.ask(prompt)
            result = self._parse_response(response)
            logger.info(
                f"[AI定位] {'✓' if result.found else '✗'} "
                f"{element_desc} → {result.locator_type}={result.locator_value} "
                f"(置信度: {result.confidence:.2f})"
            )
        except Exception as e:
            logger.error(f"[AI定位] 异常: {e}")
            result = LocatorResult(
                found=False, confidence=0.0, reasoning=str(e)
            )

        self._cache[cache_key] = result
        return result

    # ---------------------------------------------------------------
    # HTML 清洗
    # ---------------------------------------------------------------

    def _clean_html(self, html: str, max_length: int = 8000) -> str:
        """
        清洗 HTML：移除 script/style/注释，精简属性，截断超长内容。
        """
        html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL)
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        html = re.sub(r'\s+class="[^"]*"', '', html)
        html = re.sub(r'\s+style="[^"]*"', '', html)
        html = re.sub(r'\s+', ' ', html).strip()
        # 保留可交互元素的关键属性
        html = re.sub(
            r'<(input|button|a|select|textarea|label)([^>]*)>',
            lambda m: f'<{m.group(1)} {_keep_attrs(m.group(2))}>',
            html,
        )
        return html[:max_length]

    # ---------------------------------------------------------------
    # Prompt 构建
    # ---------------------------------------------------------------

    def _build_prompt(self, cleaned_html: str, element_desc: str, url: str) -> str:
        return f"""你是一个 Web 元素定位专家。给定页面的 HTML 结构和元素的语义描述，
请分析并返回该元素的最佳定位策略。

## 页面 HTML（精简后）
```
{cleaned_html}
```

## 元素语义描述
"{element_desc}"

## 页面上下文
- URL: {url}

## 分析要求
1. 仔细阅读 HTML，找出与 "{element_desc}" 最匹配的元素
2. 优先使用稳定的属性定位（id、data-*、name、aria-*）
3. 次选基于文本内容定位（text()、contains(text())）
4. 最后才考虑结构化路径（CSS/XPath 层级）
5. 提供至少一个备选方案

## 输出格式
请严格返回 JSON（不要 markdown 代码块），格式如下：
{{
    "found": true,
    "locator_type": "css_selector | xpath | text | aria_label | id | name",
    "locator_value": "具体的定位表达式",
    "confidence": 0.95,
    "reasoning": "简要说明选择理由",
    "fallback_strategies": [
        {{"type": "xpath", "value": "...", "confidence": 0.8}}
    ]
}}

如果完全无法定位，返回:
{{
    "found": false,
    "confidence": 0.0,
    "reasoning": "无法定位的原因"
}}
"""

    # ---------------------------------------------------------------
    # 响应解析
    # ---------------------------------------------------------------

    def _parse_response(self, response: str) -> LocatorResult:
        """解析 LLM 返回的 JSON"""
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            return LocatorResult(found=False, reasoning="无法从 LLM 响应中提取 JSON")

        try:
            data = json.loads(json_match.group())
            return LocatorResult(
                found=data.get("found", False),
                locator_type=data.get("locator_type", "css_selector"),
                locator_value=data.get("locator_value", ""),
                confidence=float(data.get("confidence", 0.0)),
                reasoning=data.get("reasoning", ""),
                fallback_strategies=data.get("fallback_strategies", []),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            return LocatorResult(found=False, reasoning=f"JSON 解析失败: {e}")


def _keep_attrs(attrs: str) -> str:
    """只保留对定位有用的属性"""
    important = ["id", "name", "type", "placeholder", "value", "data-", "aria-", "role", "href"]
    parts = re.findall(r'(\w+(?:-\w+)*)\s*=\s*"[^"]*"', attrs)
    kept = [p for p in parts if any(p.startswith(imp) for imp in important)]
    return " ".join(kept)
