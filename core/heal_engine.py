"""
core/heal_engine.py

AI 自愈引擎
当 find_element 失败时，调用 AI 分析页面并推荐新的定位策略。
"""

import datetime
import json
import logging
from pathlib import Path

from core.ai_locator import AIElementLocator, LocatorResult

logger = logging.getLogger(__name__)


class HealEngine:
    """
    自愈引擎

    工作流程：
    1. 拦截定位失败异常
    2. 用 AI 分析当前页面 HTML → 新定位器
    3. 验证新定位器是否有效
    4. 有效 → 自动更新元素仓库（置信度高）/ 标记待审核（置信度低）
    5. 无效 → 返回 None，继续抛异常
    """

    def __init__(
        self,
        enabled: bool = True,
        ai_locator: AIElementLocator | None = None,
        element_repo_path: str = "element_repository/elements.yaml",
        auto_approve_threshold: float = 0.85,
    ):
        self.enabled = enabled
        self.ai_locator = ai_locator
        self.element_repo_path = Path(element_repo_path)
        self.auto_approve_threshold = auto_approve_threshold
        self._healing_log: list[dict] = []

    def heal(
        self,
        driver,
        by: str,
        old_value: str,
        page_source: str,
    ) -> str | None:
        """
        自愈入口：给定失败的定位信息，尝试找到新定位器

        Args:
            driver: WebDriver 实例
            by: 原定位方式 (如 "id", "css selector")
            old_value: 原定位值
            page_source: 当前页面 HTML

        Returns:
            新定位值（字符串），None 表示自愈失败
        """
        if not self.enabled:
            return None

        logger.info(f"[自愈] 开始修复: {by}={old_value}")

        try:
            element_desc = self._get_element_description(by, old_value)

            import asyncio
            result: LocatorResult = asyncio.run(
                self.ai_locator.locate(
                    page_source=page_source,
                    element_desc=element_desc or f"元素(原定位: {by}={old_value})",
                    url=driver.current_url,
                    use_cache=False,
                )
            )

            if not result.found or result.confidence < 0.5:
                logger.warning(f"[自愈] AI 无法定位: {element_desc}")
                return None

            if self._verify_locator(driver, result.locator_type, result.locator_value):
                self._log_healing(
                    old_by=by,
                    old_value=old_value,
                    new_type=result.locator_type,
                    new_value=result.locator_value,
                    confidence=result.confidence,
                    reasoning=result.reasoning,
                )

                if result.confidence >= self.auto_approve_threshold:
                    self._update_repository(
                        desc=element_desc or "未知元素",
                        locator_type=result.locator_type,
                        locator_value=result.locator_value,
                    )
                    logger.info(
                        f"[自愈] ✓ 自动采纳: {result.locator_type}={result.locator_value}"
                    )
                else:
                    logger.info(
                        f"[自愈] ⚠ 需人工审核: confidence={result.confidence:.2f}"
                    )

                return result.locator_value

            logger.warning("[自愈] 新定位器验证失败")
            return None

        except Exception as e:
            logger.error(f"[自愈] 异常: {e}")
            return None

    def _verify_locator(self, driver, locator_type: str, locator_value: str) -> bool:
        """验证定位器能否在当前页面找到元素"""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        by_map = {
            "css_selector": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "text": By.XPATH,
            "aria_label": By.CSS_SELECTOR,
            "id": By.ID,
            "name": By.NAME,
            "class_name": By.CLASS_NAME,
        }

        by = by_map.get(locator_type, By.CSS_SELECTOR)
        try:
            if locator_type == "text":
                value = f"//*[contains(text(), '{locator_value}')]"
            else:
                value = locator_value

            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except Exception:
            return False

    def _get_element_description(self, by: str, value: str) -> str | None:
        """从元素仓库读取语义描述"""
        try:
            import yaml
            if self.element_repo_path.exists():
                with open(self.element_repo_path) as f:
                    repo = yaml.safe_load(f) or {}
                for name, elem in repo.get("elements", {}).items():
                    for loc in elem.get("locators", []):
                        if loc.get("value") == value:
                            return elem.get("description") or name
        except Exception:
            pass
        return None

    def _log_healing(self, **kwargs):
        """记录自愈日志"""
        entry = {"timestamp": datetime.datetime.now().isoformat(), **kwargs}
        self._healing_log.append(entry)

        log_path = Path("element_repository/healing_log.jsonl")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _update_repository(self, desc: str, locator_type: str, locator_value: str):
        """更新元素仓库"""
        try:
            import yaml
            repo_path = self.element_repo_path
            repo_path.parent.mkdir(parents=True, exist_ok=True)

            if repo_path.exists():
                with open(repo_path) as f:
                    repo = yaml.safe_load(f) or {"elements": {}}
            else:
                repo = {"elements": {}}

            elem_key = desc.lower().replace(" ", "_")[:30]
            if elem_key not in repo["elements"]:
                repo["elements"][elem_key] = {
                    "description": desc,
                    "locators": [],
                    "last_updated": datetime.datetime.now().isoformat(),
                }

            repo["elements"][elem_key]["locators"].append({
                "type": locator_type,
                "value": locator_value,
                "priority": 1,
                "status": "auto_approved",
                "added_at": datetime.datetime.now().isoformat(),
            })

            with open(repo_path, "w", encoding="utf-8") as f:
                yaml.dump(repo, f, allow_unicode=True, default_flow_style=False)

        except Exception as e:
            logger.error(f"[自愈] 仓库更新失败: {e}")
