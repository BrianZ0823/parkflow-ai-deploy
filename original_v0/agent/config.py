# -*- coding: utf-8 -*-
"""LLM API 配置（阿里百炼 DashScope）"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def _read_api_key():
    key = os.getenv("DASHSCOPE_API_KEY")
    if key:
        return key
    key_file = os.path.join(BASE_DIR, "api_key.txt")
    if os.path.exists(key_file):
        with open(key_file, "r", encoding="utf-8") as f:
            key = f.read().strip()
        if key:
            return key
    raise ValueError("请设置 DASHSCOPE_API_KEY 环境变量或在 api_key.txt 中填入 API Key")


LLM_CONFIG = {
    "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "api_key": _read_api_key(),
    "model": "qwen-plus",
    "temperature": 0.9,
    "max_tokens": 4096,
    "timeout": float(os.getenv("LLM_TIMEOUT_SECONDS", "45")),
    "max_retries": int(os.getenv("LLM_MAX_RETRIES", "2")),
}

# 表达层模型：用于生成用户可见的最终回复，角色人设还原能力更强
CHARACTER_MODEL_CONFIG = {
    "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "api_key": _read_api_key(),
    "model": "qwen-plus-character",
    "temperature": 0.9,
    "max_tokens": 4096,
    "timeout": float(os.getenv("LLM_TIMEOUT_SECONDS", "45")),
    "max_retries": int(os.getenv("LLM_MAX_RETRIES", "2")),
}
