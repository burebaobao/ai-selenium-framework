#!/usr/bin/env python3
"""
scripts/get_captcha.py
获取验证码图片和 ID，保存到本地，用户查看后手动输入
"""

import argparse
import json
import base64
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="获取登录验证码")
    parser.add_argument("--output", "-o", default="reports/captcha/captcha.png",
                        help="验证码图片保存路径")
    parser.add_argument("--headless", action="store_true", default=True)
    args = parser.parse_args()

    options = Options()
    if args.headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get("https://user.hxapp.vip/pc/#/login")
        time.sleep(4)

        resp = driver.execute_script("""
            return fetch('/api/captcha', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            }).then(r => r.json()).then(d => JSON.stringify(d.data)).catch(e => 'error');
        """)
        data = json.loads(resp)

        img_data = base64.b64decode(data["captcha"].split(",")[1])
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(img_data)

        print(f"验证码图片: {out_path.resolve()}")
        print(f"Captcha ID: {data['id']}")
        print()
        print("使用方式:")
        print(f"  CAPTCHA_TEXT='<验证码>' CAPTCHA_ID='{data['id']}' pytest tests/")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
