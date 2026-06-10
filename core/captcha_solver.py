"""
core/captcha_solver.py

验证码识别模块
支持多策略：Tesseract OCR → 人工输入 → API 服务（预留）
"""

import base64
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

logger = logging.getLogger(__name__)


class CaptchaSolver:
    """验证码识别器"""

    def __init__(self, strategy: str = "auto", project_dir: str = ""):
        """
        Args:
            strategy: auto | manual | api
            project_dir: 项目根目录（用于保存临时文件）
        """
        self.strategy = strategy
        self.project_dir = project_dir or os.getcwd()
        self._tesseract_ok = self._check_tesseract()

    # ---------------------------------------------------------------
    # 公共接口
    # ---------------------------------------------------------------

    def solve(self, base64_image: str) -> str:
        """
        识别验证码

        Args:
            base64_image: data:image/png;base64,... 格式的图片数据

        Returns:
            验证码文本，空字符串表示识别失败
        """
        # 策略 0: 优先使用环境变量（支持自动化运行）
        env_captcha = os.environ.get("CAPTCHA_TEXT", "")
        if env_captcha:
            logger.info(f"[Captcha] 使用环境变量: {env_captcha}")
            return env_captcha

        img_data = base64.b64decode(base64_image.split(",")[1])
        img_path = self._save_image(img_data)

        text = ""

        # 策略 1: Tesseract OCR
        if self.strategy in ("auto", "tesseract") and self._tesseract_ok:
            text = self._ocr_tesseract(img_path)
            if text:
                logger.info(f"[Captcha] OCR 识别: {text}")
                return text

        # 策略 2: 人工输入
        if self.strategy in ("auto", "manual"):
            text = self._manual_input(img_path)
            if text:
                return text

        logger.warning("[Captcha] 所有识别策略均失败")
        return ""

    # ---------------------------------------------------------------
    # Tesseract OCR
    # ---------------------------------------------------------------

    def _check_tesseract(self) -> bool:
        try:
            r = subprocess.run(
                ["tesseract", "--version"],
                capture_output=True, timeout=5,
            )
            return r.returncode == 0
        except Exception:
            return False

    def _ocr_tesseract(self, img_path: str) -> str:
        """使用 Tesseract 进行 OCR"""
        try:
            img = Image.open(img_path)

            # 多策略预处理后分别尝试，取第一个非空结果
            strategies = [
                lambda i: i.convert("RGB"),                          # 原始 RGB
                lambda i: i.convert("RGB").resize((480, 160), Image.LANCZOS),  # 放大
                lambda i: ImageEnhance.Contrast(
                    i.convert("RGB")
                ).enhance(2.0).resize((480, 160), Image.LANCZOS),    # 增强对比
            ]

            for idx, prep in enumerate(strategies):
                try:
                    processed = prep(img)
                    tmp_path = img_path.replace(".png", f"_p{idx}.png")
                    # 安全保存
                    if processed.mode == "L":
                        processed = processed.convert("RGB")
                    processed.save(tmp_path)

                    result = subprocess.run(
                        ["tesseract", tmp_path, tmp_path.replace(".png", "")],
                        capture_output=True, timeout=10,
                    )
                    out_file = tmp_path.replace(".png", ".txt")
                    if os.path.exists(out_file):
                        with open(out_file) as f:
                            text = re.sub(
                                r"[^a-zA-Z0-9]", "",
                                f.read().strip()
                            )
                        os.unlink(out_file)
                        if text:
                            return text
                except Exception:
                    continue
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

            return ""
        except Exception as e:
            logger.debug(f"[Captcha] OCR 异常: {e}")
            return ""

    # ---------------------------------------------------------------
    # 人工输入
    # ---------------------------------------------------------------

    def _manual_input(self, img_path: str) -> str:
        """弹出验证码图片并等待用户输入"""
        screenshot_dir = Path(self.project_dir) / "reports" / "captcha"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        dest = str(screenshot_dir / "captcha_input.png")
        try:
            img = Image.open(img_path)
            img.save(dest)
        except Exception:
            import shutil
            shutil.copy(img_path, dest)

        logger.info(f"\n{'='*50}")
        logger.info(f"  验证码图片已保存: {dest}")
        logger.info(f"  请打开该图片查看验证码，然后在此输入")
        logger.info(f"{'='*50}")

        text = input("请输入验证码: ").strip()
        return text

    # ---------------------------------------------------------------
    # 工具方法
    # ---------------------------------------------------------------

    def _save_image(self, img_data: bytes) -> str:
        """保存图片到临时文件"""
        tmp_dir = Path(self.project_dir) / "reports" / "captcha"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        path = str(tmp_dir / "captcha_latest.png")
        with open(path, "wb") as f:
            f.write(img_data)
        return path
