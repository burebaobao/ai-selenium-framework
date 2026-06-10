"""
tests/test_login.py
目标网站登录测试
"""

import logging

import pytest

from pages.login_page import LoginPage

logger = logging.getLogger(__name__)

# 测试账号
TEST_EMAIL = "739891689@qq.com"
TEST_PASSWORD = "ps123456"


class TestLogin:
    """登录功能测试"""

    @pytest.mark.smoke
    def test_login_page_loads(self, driver):
        """验证登录页能够正常加载"""
        page = LoginPage(driver)
        page.open()
        page.wait_for_page_loaded()

        assert "登录" in page.title, f"页面标题错误: {page.title}"
        assert page.email_input.is_displayed, "邮箱输入框未显示"
        assert page.password_input.is_displayed, "密码输入框未显示"
        assert page.captcha_input.is_displayed, "验证码输入框未显示"
        assert page.login_button.is_displayed, "登录按钮未显示"

        logger.info("✓ 登录页加载正常，所有元素可见")

    @pytest.mark.smoke
    @pytest.mark.manual_captcha
    def test_login_with_manual_captcha(self, driver):
        """
        登录测试（手动输入验证码）
        运行后会弹出验证码图片，需要人工输入验证码文字
        """
        page = LoginPage(driver)
        result = page.login(
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
        )
        assert result, "登录失败"
        logger.info("✓ 登录成功")

    @pytest.mark.smoke
    def test_login_via_api(self, driver):
        """
        登录测试（API 方式）
        自动识别验证码（需要 Tesseract 支持）
        如果验证码无法识别，会提示手动输入
        """
        page = LoginPage(driver)
        result = page.login_via_api(
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
        )
        assert result, "API 登录失败"
        logger.info("✓ API 登录成功")

    def test_login_form_fields(self, driver):
        """验证表单字段功能"""
        page = LoginPage(driver)
        page.open()
        page.wait_for_page_loaded()

        # 输入内容
        page.email_input.input(TEST_EMAIL)
        page.password_input.input(TEST_PASSWORD)

        # 验证输入
        email_val = page.driver.execute_script(
            'return document.querySelector(\'input[placeholder="邮箱"]\').value'
        )
        pwd_val = page.driver.execute_script(
            'return document.querySelector(\'input[placeholder="密码"]\').value'
        )

        assert email_val == TEST_EMAIL, f"邮箱输入错误: {email_val}"
        assert pwd_val == TEST_PASSWORD, "密码输入错误"

        logger.info("✓ 表单字段功能正常")
