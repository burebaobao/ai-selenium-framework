"""
core/driver_factory.py

WebDriver 工厂 —— 支持多浏览器、本地/远程模式
"""

import logging
from typing import Literal

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver

logger = logging.getLogger(__name__)

BrowserType = Literal["chrome", "firefox", "edge"]


class DriverFactory:
    """WebDriver 工厂类"""

    @staticmethod
    def create_driver(
        browser: BrowserType = "chrome",
        headless: bool = False,
        implicit_wait: int = 5,
        remote_url: str | None = None,
        window_width: int = 1920,
        window_height: int = 1080,
        **extra_options,
    ) -> WebDriver:
        """
        创建 WebDriver 实例

        Args:
            browser: 浏览器类型
            headless: 是否无头模式
            implicit_wait: 隐式等待秒数
            remote_url: Selenium Grid 远程地址（可选）
            window_width: 窗口宽度
            window_height: 窗口高度
            extra_options: 额外浏览器参数

        Returns:
            WebDriver 实例
        """
        if remote_url:
            driver = DriverFactory._create_remote_driver(browser, remote_url, headless)
        else:
            factory = {
                "chrome": DriverFactory._create_chrome_driver,
                "firefox": DriverFactory._create_firefox_driver,
                "edge": DriverFactory._create_edge_driver,
            }
            factory_fn = factory.get(browser)
            if not factory_fn:
                raise ValueError(f"不支持的浏览器: {browser}")
            driver = factory_fn(headless, **extra_options)

        driver.implicitly_wait(implicit_wait)
        driver.set_window_size(window_width, window_height)

        logger.info(
            f"[Driver] ✓ {browser.upper()} | headless={headless} | "
            f"remote={bool(remote_url)}"
        )
        return driver

    @staticmethod
    def _create_chrome_driver(headless: bool = False, **kwargs) -> WebDriver:
        """创建 Chrome 驱动"""
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument(f"--window-size={kwargs.get('width', 1920)},{kwargs.get('height', 1080)}")
        options.add_argument("--lang=zh-CN")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    @staticmethod
    def _create_firefox_driver(headless: bool = False, **kwargs) -> WebDriver:
        """创建 Firefox 驱动"""
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service
        from webdriver_manager.firefox import GeckoDriverManager

        options = Options()
        if headless:
            options.add_argument("--headless")

        service = Service(GeckoDriverManager().install())
        return webdriver.Firefox(service=service, options=options)

    @staticmethod
    def _create_edge_driver(headless: bool = False, **kwargs) -> WebDriver:
        """创建 Edge 驱动"""
        from selenium.webdriver.edge.options import Options
        from selenium.webdriver.edge.service import Service
        from webdriver_manager.microsoft import EdgeChromiumDriverManager

        options = Options()
        if headless:
            options.add_argument("--headless=new")

        service = Service(EdgeChromiumDriverManager().install())
        return webdriver.Edge(service=service, options=options)

    @staticmethod
    def _create_remote_driver(
        browser: str, remote_url: str, headless: bool
    ) -> WebDriver:
        """创建远程 WebDriver（Selenium Grid）"""
        options_map = {
            "chrome": webdriver.ChromeOptions,
            "firefox": webdriver.FirefoxOptions,
            "edge": webdriver.EdgeOptions,
        }
        opt_cls = options_map.get(browser)
        if not opt_cls:
            raise ValueError(f"不支持的远程浏览器: {browser}")

        options = opt_cls()
        if headless:
            options.add_argument("--headless")

        return webdriver.Remote(command_executor=remote_url, options=options)
