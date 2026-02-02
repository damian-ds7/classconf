from typing import TypeVar

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


class _Registry[_KT, _VT](dict[_KT, _VT]):  # noqa: UP049
    def register(self, name: _KT, t: _VT) -> None:
        self[name] = t

    def get_all_registered(self) -> list[_VT]:
        return list(self.values())

    def is_registered(self, config_class: _KT) -> bool:
        return config_class in self
