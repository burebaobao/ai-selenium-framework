"""
pages/login_page.py

⚠️ Demo：框架验证用的参考实现，与你实际要测的网站无关。

这是演示框架能力的参考例子，展示了:
  - AIElement 语义定位用法
  - CaptchaSolver 验证码处理集成
  - API 方式 / UI 方式两种登录策略

适配你自己的网站，直接参考这个结构创建 pages/your_page.py 即可。
"""

import json
import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.captcha_solver import CaptchaSolver
from pages.base_page import BasePage

logger = logging.getLogger(__name__)

LOGIN_URL = "https://user.hxapp.vip/pc/#/login"


class LoginPage(BasePage):
    """登录页面对象"""

    url = LOGIN_URL

    def __init__(self, driver):
        super().__init__(driver)
        self.captcha_solver = CaptchaSolver(
            strategy="auto",
            project_dir="/Users/liwei/Documents/ai-selenium-framework",
        )

    # ---------------------------------------------------------------
    # 元素定义（先传统定位 → AI 语义回退）
    # ---------------------------------------------------------------

    @property
    def email_input(self):
        return self.element(
            "邮箱输入框",
            locator=(By.CSS_SELECTOR, 'input[placeholder="邮箱"]'),
        )

    @property
    def password_input(self):
        return self.element(
            "密码输入框",
            locator=(By.CSS_SELECTOR, 'input[placeholder="密码"]'),
        )

    @property
    def captcha_input(self):
        return self.element(
            "验证码输入框",
            locator=(By.CSS_SELECTOR, 'input[placeholder="验证码"]'),
        )

    @property
    def login_button(self):
        return self.element(
            "登录按钮",
            locator=(By.CSS_SELECTOR, "button.el-button--primary"),
        )

    # ---------------------------------------------------------------
    # 验证码处理
    # ---------------------------------------------------------------

    def fetch_captcha(self) -> tuple[str, str]:
        """
        从 API 获取验证码

        Returns:
            (captcha_id, captcha_base64)
        """
        result = self.driver.execute_script(
            """
            return fetch('/api/captcha', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(r => r.json())
            .then(d => JSON.stringify(d.data))
            .catch(e => 'error: ' + e.toString());
            """
        )
        data = json.loads(result)
        return data["id"], data["captcha"]

    def solve_captcha(self, captcha_base64: str) -> str:
        """识别验证码文字"""
        return self.captcha_solver.solve(captcha_base64)

    def get_captcha_id(self) -> str:
        """从页面获取当前验证码 ID（通过 API）"""
        captcha_id, _ = self.fetch_captcha()
        return captcha_id

    # ---------------------------------------------------------------
    # 登录操作
    # ---------------------------------------------------------------

    def login(
        self, email: str, password: str, captcha_text: str | None = None
    ) -> bool:
        """
        执行登录（通过点击 UI 按钮）

        Args:
            email: 邮箱
            password: 密码
            captcha_text: 验证码文字（None 则自动识别）

        Returns:
            True=登录成功, False=登录失败
        """
        self.open()
        self.wait_for_page_loaded()

        # 获取验证码
        captcha_id, captcha_b64 = self.fetch_captcha()
        if not captcha_text:
            captcha_text = self.solve_captcha(captcha_b64)

        if not captcha_text:
            logger.error("[登录] 验证码识别失败，请手动检查")
            return False

        logger.info(f"[登录] 验证码: {captcha_text} (id={captcha_id[:8]}...)")

        # 填写表单
        self.email_input.input(email)
        self.password_input.input(password)

        # 用 JavaScript 填入验证码（绕过前端的 captcha refresh）
        self.driver.execute_script(
            """
            const inp = document.querySelector('input[placeholder="验证码"]');
            if (inp) {
                Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set.call(inp, arguments[0]);
                inp.dispatchEvent(new Event('input', { bubbles: true }));
            }
            """,
            captcha_text,
        )

        # 点击登录
        from selenium.webdriver.common.action_chains import ActionChains
        ActionChains(self.driver).pause(0.5).perform()
        self.login_button.click()

        # 等待登录结果
        import time
        time.sleep(3)

        return self.is_logged_in()

    def login_via_api(
        self, email: str, password: str,
        captcha_text: str | None = None,
        captcha_id: str | None = None,
    ) -> bool:
        """
        通过 API 直接登录（绕过 UI 点击，更可靠）

        Args:
            email: 邮箱
            password: 密码
            captcha_text: 验证码文字（None 则自动识别）
            captcha_id: 验证码 ID（和 captcha_text 匹配，None 则自动获取）

        Returns:
            True=登录成功, False=登录失败
        """
        import os
        self.open()
        self.wait_for_page_loaded()

        # 优先使用环境变量或预先传入的值
        captcha_id = captcha_id or os.environ.get("CAPTCHA_ID", "")
        captcha_text = captcha_text or os.environ.get("CAPTCHA_TEXT", "")

        if not captcha_id or not captcha_text:
            captcha_id, captcha_b64 = self.fetch_captcha()
            if not captcha_text:
                captcha_text = self.solve_captcha(captcha_b64)

        if not captcha_text:
            logger.error("[登录] 验证码识别失败")
            return False

        logger.info(
            f"[登录-API] captcha={captcha_text} (id={captcha_id[:8]}...)"
        )

        # 直接通过 fetch 调用登录 API
        result = self.driver.execute_script(
            f"""
            return fetch('/api/token', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{
                    username: '{email}',
                    password: '{password}',
                    captcha: '{captcha_text}',
                    captcha_id: '{captcha_id}'
                }})
            }})
            .then(r => r.json())
            .then(d => JSON.stringify(d))
            .catch(e => 'error: ' + e.toString());
            """
        )
        resp = json.loads(result)
        logger.info(f"[登录-API] 响应: code={resp.get('code')}, msg={resp.get('message')}")

        if resp.get("code") == 0:
            # 登录成功，存储 token
            token = ""
            if "data" in resp:
                if isinstance(resp["data"], dict):
                    token = resp["data"].get("token", "")
                elif isinstance(resp["data"], str):
                    token = resp["data"]

            if token:
                self.driver.execute_script(
                    f"localStorage.setItem('token', '{token}');"
                )
                logger.info(f"[登录] Token 已存储: {token[:20]}...")

            # SPA 需要刷新页面才能触发路由跳转
            import time
            self.driver.get("https://user.hxapp.vip/pc/#/")
            time.sleep(3)
            return True
        else:
            logger.error(f"[登录] 失败: {resp.get('message', '')}")
            if "验证码" in resp.get("message", ""):
                logger.warning("[登录] 验证码错误，尝试重新识别...")
            return False

    # ---------------------------------------------------------------
    # 登录状态检查
    # ---------------------------------------------------------------

    def is_logged_in(self) -> bool:
        """检查是否已登录（通过 URL 或 token）"""
        import time
        time.sleep(2)

        # 检查 URL 是否跳转
        current = self.driver.current_url
        if "/login" not in current and "#/login" not in current:
            logger.info(f"[登录] URL 已跳转: {current}")
            return True

        # 检查 token
        token = self.driver.execute_script(
            "return localStorage.getItem('token')"
        )
        if token:
            logger.info(f"[登录] 有 token: {token[:20]}...")
            return True

        return False

    def get_token(self) -> str:
        """获取登录 token"""
        return self.driver.execute_script(
            "return localStorage.getItem('token') || sessionStorage.getItem('token') || ''"
        ) or ""
