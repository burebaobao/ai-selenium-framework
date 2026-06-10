"""
pages/base_page.py

AI 增强的 Page Object 基类
提供 AIElement 包装器，支持语义级元素定位和自愈。
"""

import logging
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.ai_locator import AIElementLocator, LocatorResult

logger = logging.getLogger(__name__)


class AIElement:
    """
    支持 AI 定位的智能元素包装器

    用法:
        btn = AIElement(driver, "登录按钮")
        btn.click()

        inp = AIElement(driver, "用户名输入框", locator=(By.ID, "username"))
        inp.type("admin")
    """

    def __init__(
        self,
        driver: WebDriver,
        description: str,
        locator: tuple[str, str] | None = None,
        ai_locator: AIElementLocator | None = None,
        wait_timeout: int = 10,
    ):
        self.driver = driver
        self.description = description
        self._locator = locator
        self._ai_locator = ai_locator
        self._wait_timeout = wait_timeout
        self._element: WebElement | None = None
        self._healed = False

    # ---------------------------------------------------------------
    # 核心：获取 WebElement
    # ---------------------------------------------------------------

    @property
    def element(self) -> WebElement:
        """获取 WebElement —— 自动降级：传统定位 → AI 语义定位"""
        if self._element is not None:
            return self._element

        if self._locator and not self._healed:
            try:
                by, value = self._locator
                self._element = WebDriverWait(
                    self.driver, self._wait_timeout
                ).until(EC.presence_of_element_located((by, value)))
                return self._element
            except Exception as e:
                logger.warning(
                    f"传统定位失败: {self.description} "
                    f"({self._locator[0]}={self._locator[1]}) 尝试 AI 定位..."
                )

        self._element = self._ai_locate()
        self._healed = True
        return self._element

    # ---------------------------------------------------------------
    # AI 定位
    # ---------------------------------------------------------------

    def _ai_locate(self) -> WebElement:
        """使用 AI 定位元素"""
        if not self._ai_locator:
            raise RuntimeError(
                f"AI 定位器未配置，无法定位元素: {self.description}"
            )

        import asyncio

        result: LocatorResult = asyncio.run(
            self._ai_locator.locate(
                page_source=self.driver.page_source,
                element_desc=self.description,
                url=self.driver.current_url,
            )
        )

        if not result.found:
            raise ElementNotFoundError(
                f"AI 未能定位元素: '{self.description}' "
                f"(置信度 {result.confidence:.2f})"
            )

        by_map = {
            "css_selector": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "text": By.XPATH,
            "aria_label": By.CSS_SELECTOR,
            "id": By.ID,
            "name": By.NAME,
        }

        by = by_map.get(result.locator_type, By.CSS_SELECTOR)
        value = (
            f"//*[contains(text(), '{result.locator_value}')]"
            if result.locator_type == "text"
            else result.locator_value
        )

        element = WebDriverWait(self.driver, self._wait_timeout).until(
            EC.presence_of_element_located((by, value))
        )

        logger.info(
            f"AI 定位成功: '{self.description}' → {by}={value} "
            f"({result.confidence:.0%})"
        )
        return element

    # ---------------------------------------------------------------
    # 操作代理
    # ---------------------------------------------------------------

    def click(self) -> "AIElement":
        """点击元素"""
        self.element.click()
        return self

    def input(self, text: str) -> "AIElement":
        """输入文本（先清空再输入）"""
        el = self.element
        el.clear()
        el.send_keys(text)
        return self

    def get_text(self) -> str:
        """获取元素文本"""
        return self.element.text

    def get_attribute(self, name: str) -> str:
        """获取元素属性"""
        return self.element.get_attribute(name) or ""

    @property
    def is_displayed(self) -> bool:
        """元素是否可见"""
        try:
            return self.element.is_displayed()
        except Exception:
            return False

    @property
    def is_enabled(self) -> bool:
        """元素是否可用"""
        try:
            return self.element.is_enabled()
        except Exception:
            return False


class BasePage:
    """
    页面基类 —— 所有 Page Object 的父类

    提供 AI 元素创建、页面跳转、截图等通用功能。
    """

    url: str = ""

    def __init__(self, driver: WebDriver):
        self.driver = driver
        self._ai_locator: AIElementLocator | None = getattr(
            driver, "_ai_locator", None
        )

    # ---------------------------------------------------------------
    # AI 元素
    # ---------------------------------------------------------------

    def element(
        self,
        description: str,
        locator: tuple[str, str] | None = None,
    ) -> AIElement:
        """创建 AI 智能元素"""
        return AIElement(
            driver=self.driver,
            description=description,
            locator=locator,
            ai_locator=self._ai_locator,
        )

    # ---------------------------------------------------------------
    # 页面导航
    # ---------------------------------------------------------------

    def open(self, url: str = "") -> "BasePage":
        """打开页面"""
        target = url or self.url
        if target:
            self.driver.get(target)
        return self

    def wait_for_page_loaded(self, timeout: int = 15) -> "BasePage":
        """等待页面加载完成"""
        WebDriverWait(self.driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        return self

    def wait_until(
        self, condition, timeout: int = 10
    ) -> "BasePage":
        """等待某个条件成立"""
        WebDriverWait(self.driver, timeout).until(condition)
        return self

    # ---------------------------------------------------------------
    # 截图
    # ---------------------------------------------------------------

    def take_screenshot(self, name: str = "") -> str:
        """截图保存到 reports/screenshots/"""
        screenshot_dir = Path("reports/screenshots")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        path = str(screenshot_dir / f"{name or 'screenshot'}.png")
        self.driver.save_screenshot(path)
        return path

    # ---------------------------------------------------------------
    # 页面信息
    # ---------------------------------------------------------------

    @property
    def title(self) -> str:
        return self.driver.title

    @property
    def current_url(self) -> str:
        return self.driver.current_url

    def execute_script(self, script: str, *args):
        """执行 JavaScript"""
        return self.driver.execute_script(script, *args)


class ElementNotFoundError(Exception):
    """元素未找到异常"""
    pass
