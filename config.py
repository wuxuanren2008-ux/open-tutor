"""配置管理：provider 切换 + 密钥安全。

设计原则：
- 密钥只从环境变量或本地 config.json 读取，绝不写进代码、日志或仓库。
- 前端展示一律脱敏。
- 三种模型来源：offline（离线兜底）/ openai（OpenAI 兼容 API，含本地中转）/ ollama（本地模型）。
"""
import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "data", "config.json")

DEFAULTS = {
    "provider": "offline",          # offline | openai | ollama
    "base_url": "https://api.deepseek.com/v1",
    "api_key": "",                  # 建议用环境变量 OPEN_TUTOR_API_KEY
    "model": "deepseek-chat",
    "temperature": 0.7,
    "timeout": 60,
    "ollama_base_url": "http://127.0.0.1:11434",
    "ollama_model": "qwen2.5",
}

PROVIDERS = ("offline", "openai", "ollama")


def _load_file():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def get_config():
    """环境变量优先于本地文件；密钥优先取 OPEN_TUTOR_API_KEY。"""
    cfg = dict(DEFAULTS)
    cfg.update(_load_file())
    env_key = os.environ.get("OPEN_TUTOR_API_KEY")
    if env_key:
        cfg["api_key"] = env_key
    env_provider = os.environ.get("OPEN_TUTOR_PROVIDER")
    if env_provider:
        cfg["provider"] = env_provider
    if cfg["provider"] not in PROVIDERS:
        cfg["provider"] = "offline"
    return cfg


def save_config(patch):
    """合并写入本地 config.json。传 api_key 为空字符串表示保留原值。"""
    cfg = get_config()
    for key in DEFAULTS:
        if key in patch and patch[key] not in (None, ""):
            cfg[key] = patch[key]
        elif key in patch and patch[key] == "" and key != "api_key":
            cfg[key] = ""
    if cfg["provider"] not in PROVIDERS:
        cfg["provider"] = "offline"
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return cfg


def public_config():
    """给前端的配置，密钥脱敏。"""
    cfg = get_config()
    key = cfg.get("api_key", "")
    if key:
        cfg["api_key"] = key[:4] + "*" * max(0, len(key) - 8) + key[-4:]
        cfg["api_key_set"] = True
    else:
        cfg["api_key"] = ""
        cfg["api_key_set"] = False
    return cfg
