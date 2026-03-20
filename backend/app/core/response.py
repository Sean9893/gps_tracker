from typing import Any


def success(data: Any = None, msg: str = "success") -> dict:
    return {"code": 0, "msg": msg, "data": data}


def fail(msg: str = "error message", data: Any = None) -> dict:
    return {"code": 1, "msg": msg, "data": data}

