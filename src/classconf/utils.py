from dataclasses import is_dataclass


def is_configclass_type(tp: type) -> bool:
    if not is_dataclass(tp):
        return False
    return hasattr(tp, "__config__") and hasattr(tp, "__dataclass_fields__")
