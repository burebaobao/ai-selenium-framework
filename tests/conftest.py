"""
tests/conftest.py

pytest 全局配置 —— 扩展 CLI 选项、提供 fixture、自愈 hook
"""

import logging
from pathlib import Path
from typing import Generator

import pytest
from selenium.webdriver.remote.webdriver import WebDriver

from core.ai_locator import AIElementLocator
from core.driver_factory import DriverFactory
from core.heal_engine import HealEngine
from utils.logger import setup_logging

logger = logging.getLogger(__name__)


# ================================================================
# CLI 选项扩展
# ================================================================

def pytest_addoption(parser):
    """自定义 pytest CLI 参数"""
    group = parser.getgroup("ai-selenium", "AI + Selenium 框架参数")

    group.addoption(
        "--ai-heal",
        action="store_true",
        default=None,
        help="启用 AI 自愈（定位失败时自动修复）",
    )
    group.addoption(
        "--no-ai-heal",
        action="store_false",
        dest="ai_heal",
        help="禁用 AI 自愈",
    )
    group.addoption(
        "--ai-provider",
        choices=["claude", "openai", "local"],
        default="claude",
        help="AI 模型供应商",
    )
    group.addoption(
        "--browser",
        choices=["chrome", "firefox", "edge"],
        default="chrome",
        help="浏览器类型",
    )
    group.addoption(
        "--headless",
        action="store_true",
        default=False,
        help="无头模式运行",
    )


# ================================================================
# 注册自定义 Markers
# ================================================================

def pytest_configure(config):
    config.addinivalue_line("markers", "smoke: 冒烟测试")
    config.addinivalue_line("markers", "regression: 回归测试")
    config.addinivalue_line("markers", "ai_generated: AI 自动生成")
    config.addinivalue_line("markers", "healed: 经过自愈的用例")
    config.addinivalue_line("markers", "flaky: 已知不稳定的用例")
    config.addinivalue_line("markers", "manual_captcha: 需要手动输入验证码的用例")


# ================================================================
# 全局 Fixture
# ================================================================

@pytest.fixture(scope="session")
def ai_locator(request) -> AIElementLocator:
    """AI 元素定位器（session 级别，复用连接）"""
    provider = request.config.getoption("--ai-provider")
    return AIElementLocator(provider=provider)


@pytest.fixture(scope="session")
def heal_engine(request, ai_locator) -> HealEngine:
    """自愈引擎"""
    # CLI 参数优先，其次读配置，默认启用
    ai_heal = request.config.getoption("--ai-heal")
    if ai_heal is None:
        ai_heal = True

    return HealEngine(
        enabled=ai_heal,
        ai_locator=ai_locator,
        element_repo_path="element_repository/elements.yaml",
    )


@pytest.fixture(scope="function")
def driver(request) -> Generator[WebDriver, None, None]:
    """
    WebDriver fixture

    特性:
    - 通过 --browser / --headless 切换浏览器和模式
    - 测试失败自动截图
    - 注入自愈引擎
    """
    browser = request.config.getoption("--browser")
    headless = request.config.getoption("--headless")

    driver = DriverFactory.create_driver(
        browser=browser,
        headless=headless,
    )

    # 注入 AI 定位器到 driver（供 pages/base_page 使用）
    ai = request.getfixturevalue("ai_locator")
    driver._ai_locator = ai

    yield driver

    # 失败时自动截图
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        _capture_failure(driver, request.node)

    driver.quit()


# ================================================================
# Hook: 测试结果追踪
# ================================================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """记录每个测试阶段的结果（用于 fixture 判断失败）"""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# ================================================================
# 自愈包装器
# ================================================================

@pytest.fixture(autouse=True)
def auto_heal(driver, heal_engine):
    """
    自动自愈包装器

    透明地拦截 driver.find_element 调用，
    在 NoSuchElementException 时自动触发 AI 自愈。
    """
    original_find = driver.find_element
    _retry_count = 0
    _max_retries = 3

    def healing_find(by, value):
        nonlocal _retry_count
        try:
            return original_find(by, value)
        except Exception:
            if not heal_engine.enabled:
                raise

            _retry_count += 1
            if _retry_count > _max_retries:
                logger.warning(f"[自愈] 全局已达上限 ({_max_retries}次), 放弃自愈")
                raise

            new_value = heal_engine.heal(
                driver=driver,
                by=by,
                old_value=value,
                page_source=driver.page_source,
            )
            if new_value:
                try:
                    return original_find(by, new_value)
                except Exception:
                    _retry_count += 1
                    if _retry_count > _max_retries:
                        raise
                    # 再试一次
                    return original_find(by, new_value)
            raise

    driver.find_element = healing_find
    yield
    driver.find_element = original_find


# ================================================================
# 辅助方法
# ================================================================

def _capture_failure(driver: WebDriver, node):
    """失败截图保存"""
    screenshot_dir = Path("reports/screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    timestamp = node.nodeid.replace("/", "_").replace("::", "_")
    path = str(screenshot_dir / f"{timestamp}.png")
    try:
        driver.save_screenshot(path)
        logger.info(f"失败截图已保存: {path}")
    except Exception as e:
        logger.warning(f"截图保存失败: {e}")
