# -*- coding: utf-8 -*-
"""Small helpers for consistent JSON tool responses."""
import json
from typing import Any


def tool_error(error_code: str, message: str, *, retryable: bool = False, source: str = "tool", **extra: Any) -> str:
    payload = {
        "ok": False,
        "error_code": error_code,
        "message": message,
        "retryable": retryable,
        "source": source,
    }
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False)


def tool_success(data: Any = None, **extra: Any) -> str:
    payload = {
        "ok": True,
        "data": data,
    }
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False)
