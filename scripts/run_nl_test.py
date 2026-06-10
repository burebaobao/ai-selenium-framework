#!/usr/bin/env python3
"""
scripts/run_nl_test.py

自然语言 Web 自动化测试 — 一句话驱动浏览器执行测试

用法:
  # 直接描述操作
  python scripts/run_nl_test.py "打开百度，搜索AI测试，验证标题"

  # 描述更复杂的场景
  python scripts/run_nl_test.py "打开登录页，输入用户名admin，输入密码123456，点击登录，验证跳转"

  # 指定浏览器
  python scripts/run_nl_test.py "打开百度" --browser firefox

  # 显示浏览器界面（不 headless）
  python scripts/run_nl_test.py "打开百度" --show

  # 先发现元素再运行（交互式排查）
  python scripts/run_nl_test.py --discover "https://user.hxapp.vip/pc/#/login" "登录按钮,邮箱输入框,密码输入框"

  # 直接执行已生成的测试文件
  python scripts/run_nl_test.py --run tests/ai_generated/ --headless
"""

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

# 确保能找到项目根目录
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def cmd_discover(args):
    """发现模式：打开页面，AI 分析并定位元素"""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service

    from core.ai_locator import AIElementLocator

    options = Options()
    if not args.show:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=zh-CN")
    options.add_argument("--window-size=1280,800")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        locator = AIElementLocator(provider=args.ai_provider)

        elements = [e.strip() for e in args.discover.split(",") if e.strip()]
        targets = [(e, e) for e in elements]

        print(f"\n🔍 正在打开: {args.url}")
        print(f"🎯 目标元素: {', '.join(elements)}\n")

        if len(elements) == 1:
            result = locator.discover_element(driver, args.url, elements[0])
            _print_result(elements[0], result)
        else:
            results = locator.discover_multiple(driver, args.url, targets)
            for name, result in results.items():
                _print_result(name, result)
                print()

    finally:
        driver.quit()


def cmd_run(args):
    """执行模式：运行自然语言描述的测试"""
    from core.ai_generator import AITestGenerator

    description = args.description
    print(f"\n📝 自然语言描述: {description}\n")

    # 生成测试
    gen = AITestGenerator(provider=args.ai_provider)
    result = gen.generate_sync(description)

    print(f"\n📄 生成测试文件: {result.filepath}")
    print(f"📋 解析步骤 ({len(result.steps)} 步):")
    for i, step in enumerate(result.steps, 1):
        icon = {
            "open": "🌐", "click": "👆", "type": "⌨️",
            "assert_text": "✅", "assert_title": "✅",
            "wait": "⏳", "screenshot": "📸",
        }.get(step.action, "➡️")
        desc = step.description or f"{step.action} {step.element_desc or step.value}"
        print(f"  {icon} 步骤{i}: {desc}")

    # 执行测试
    print(f"\n{'='*50}")
    print("▶️  正在执行测试...")
    print(f"{'='*50}\n")

    cmd = [
        sys.executable, "-m", "pytest", result.filepath,
        "-v", "--tb=short",
    ]
    if args.headless:
        cmd.append("--headless")
    if args.browser:
        cmd.extend(["--browser", args.browser])

    exit_code = subprocess.run(cmd).returncode

    print(f"\n{'='*50}")
    if exit_code == 0:
        print("✅ 测试全部通过！")
    else:
        print("❌ 测试有失败项，请查看上面的详细输出")
    print(f"{'='*50}")

    return exit_code


def _print_result(name: str, result):
    """打印定位结果"""
    from core.ai_locator import LocatorResult

    if result.found:
        print(f"  ✅ [{name}]")
        print(f"     定位方式: {result.locator_type}")
        print(f"     定位值:   {result.locator_value}")
        print(f"     置信度:   {result.confidence:.0%}")
        if result.reasoning:
            print(f"     说明:     {result.reasoning}")
    else:
        print(f"  ❌ [{name}] 未找到")
        print(f"     原因: {result.reasoning}")

    if result.fallback_strategies:
        print(f"     备选方案:")
        for fb in result.fallback_strategies[:2]:
            print(f"       · {fb.get('type')}={fb.get('value')}")


def main():
    parser = argparse.ArgumentParser(
        description="🤖 AI + Selenium 自然语言测试工具",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  # 一句话执行测试
  python scripts/run_nl_test.py "打开百度，输入AI测试，点击搜索"

  # 打开登录页，登录后验证
  python scripts/run_nl_test.py "打开登录页，输入用户名admin，输入密码123456，点击登录"

  # 非 headless 模式观察浏览器行为
  python scripts/run_nl_test.py "打开百度" --show

  # 发现页面元素（排查定位问题）
  python scripts/run_nl_test.py --discover "https://example.com" "登录按钮,搜索框"
        """,
    )

    # 主参数
    parser.add_argument("description", nargs="?", default="",
                        help='自然语言测试描述，如: 打开百度搜索AI测试')

    # 发现模式
    parser.add_argument("--discover", nargs="*", default=None,
                        metavar=("URL", "ELEMENTS"),
                        help='发现模式: --discover <URL> "<元素1>,<元素2>..."')

    # 通用参数
    parser.add_argument("--browser", choices=["chrome", "firefox", "edge"],
                        default="chrome", help="浏览器类型")
    parser.add_argument("--show", action="store_true", default=False,
                        help="显示浏览器窗口（默认无头模式）")
    parser.add_argument("--headless", action="store_true", default=True,
                        help="无头模式运行")
    parser.add_argument("--ai-provider", choices=["claude", "openai", "local"],
                        default="claude", help="AI 模型供应商")
    parser.add_argument("--run", action="store_true", default=False,
                        help="运行已生成的测试文件目录")

    args = parser.parse_args()

    # 发现模式
    if args.discover is not None:
        discover_args = args.discover
        if len(discover_args) == 0:
            url = input("请输入页面 URL: ")
            elements_str = input("请输入要查找的元素（逗号分隔，如: 登录按钮,搜索框）: ")
        elif len(discover_args) == 1:
            url = discover_args[0]
            elements_str = args.description or input("请输入要查找的元素: ")
        else:
            url = discover_args[0]
            elements_str = discover_args[1]

        return cmd_discover(
            argparse.Namespace(
                discover=elements_str,
                url=url,
                show=args.show,
                ai_provider=args.ai_provider,
            )
        )

    # 执行已生成的测试文件
    if args.run:
        test_dir = args.description or "tests/ai_generated"
        cmd = [
            sys.executable, "-m", "pytest", test_dir,
            "-v", "--tb=short",
        ]
        if args.headless:
            cmd.append("--headless")
        return subprocess.run(cmd).returncode

    # 执行模式
    if args.description:
        return cmd_run(args)

    # 没有参数，进入交互模式
    parser.print_help()
    print()
    description = input("请输入测试描述（例如：打开百度搜索AI测试）: ")
    if description.strip():
        args.description = description
        return cmd_run(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
