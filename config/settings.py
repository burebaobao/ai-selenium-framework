"""
config/settings.py
配置管理 —— 从文件和环境变量加载配置
"""

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """全局配置（环境变量覆盖 YAML 配置）"""

    # ---- AI ----
    ai_provider: Literal["claude", "openai", "local"] = "claude"
    ai_model: str = "claude-sonnet-4-20250514"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    local_model_url: str = "http://localhost:11434/v1"
    local_model_name: str = "qwen2.5:7b"

    # ---- 浏览器 ----
    browser: Literal["chrome", "firefox", "edge"] = "chrome"
    headless: bool = False
    implicit_wait: int = 5
    selenium_grid_url: str | None = None

    # ---- 自愈 ----
    heal_enabled: bool = True
    auto_approve_threshold: float = 0.85
    element_repo_path: str = "element_repository/elements.yaml"

    # ---- 路径 ----
    project_root: Path = Path(__file__).resolve().parent.parent

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()


def load_config() -> dict:
    """加载 config.yaml"""
    config_path = settings.project_root / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def get_api_key(provider: str) -> str | None:
    """获取对应 AI 提供商的 API Key"""
    if provider == "claude":
        return settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
    elif provider == "openai":
        return settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    return None
