"""
utils/ai_client.py
LLM 客户端封装 —— 支持 Claude / OpenAI / Local
"""

import json
import logging
from typing import Any

from config.settings import get_api_key

logger = logging.getLogger(__name__)


class LLMClient:
    """统一的大模型客户端"""

    def __init__(
        self,
        provider: str = "claude",
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.provider = provider
        self.api_key = api_key or get_api_key(provider) or "dummy-key"
        self.model = model or self._default_model()
        self._client = None

    def _default_model(self) -> str:
        models = {
            "claude": "claude-sonnet-4-20250514",
            "openai": "gpt-4o",
            "local": "qwen2.5:7b",
        }
        return models.get(self.provider, "claude-sonnet-4-20250514")

    async def ask(self, prompt: str, response_model: type | None = None) -> Any:
        """
        向 LLM 发送请求并获取响应

        Args:
            prompt: 输入提示词
            response_model: 期望的响应模型（可选）

        Returns:
            LLM 的响应文本，或解析后的结构化数据
        """
        if self.provider == "local":
            return await self._ask_local(prompt)
        elif self.provider == "openai":
            return await self._ask_openai(prompt)
        else:
            return await self._ask_claude(prompt)

    async def _ask_claude(self, prompt: str) -> str:
        """调用 Claude API"""
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=self.api_key)
            response = await client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text if response.content else ""
        except ImportError:
            logger.warning("anthropic 未安装，使用模拟响应")
            return self._mock_response(prompt)
        except Exception as e:
            logger.error(f"Claude API 调用失败: {e}")
            return self._mock_response(prompt)

    async def _ask_openai(self, prompt: str) -> str:
        """调用 OpenAI API"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)
            response = await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content or ""
        except ImportError:
            logger.warning("openai 未安装，使用模拟响应")
            return self._mock_response(prompt)
        except Exception as e:
            logger.error(f"OpenAI API 调用失败: {e}")
            return self._mock_response(prompt)

    async def _ask_local(self, prompt: str) -> str:
        """调用本地模型（Ollama 等）"""
        try:
            import httpx

            from config.settings import settings

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{settings.local_model_url}/chat/completions",
                    json={
                        "model": settings.local_model_name,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"本地模型调用失败: {e}")
            return self._mock_response(prompt)

    def _mock_response(self, prompt: str) -> str:
        """
        模拟响应（用于无 API Key 时的开发调试）
        根据 prompt 内容自动判断返回格式（步骤列表 / 定位结果）
        """
        import json

        # 判断 prompt 类型
        if "解析为结构化的步骤" in prompt or "测试描述" in prompt:
            # 返回步骤列表格式
            return json.dumps([
                {"action": "open", "element_desc": "", "value": "https://example.com", "description": "打开页面"},
                {"action": "click", "element_desc": "按钮", "value": "", "description": "点击按钮"},
            ], ensure_ascii=False)

        # 默认：元素定位结果
        import re
        import uuid
        found_match = re.search(r'"([^"]+)"', prompt.split("元素语义描述")[-1] if "元素语义描述" in prompt else "")
        element = found_match.group(1) if found_match else "未知元素"

        mock = {
            "found": True,
            "locator_type": "css_selector",
            "locator_value": f"[data-ai-locator='{uuid.uuid4().hex[:8]}']",
            "confidence": 0.75,
            "reasoning": f"[模拟] 假设元素 '{element}' 通过 mock 定位器找到",
            "fallback_strategies": [
                {"type": "xpath", "value": f"//*[contains(text(), '{element}')]", "confidence": 0.6}
            ],
        }
        return json.dumps(mock, ensure_ascii=False)
