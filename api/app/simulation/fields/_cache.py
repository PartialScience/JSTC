"""
A tiny LRU cache keyed on a stable geometry fingerprint.

The field basis fields are expensive (FEM) and too large to hand to the
client, so they are cached server-side. They cannot be cached on the coil
objects: a coil rebuilt from a request is not value-equal to a previous one
(the geometry classes compare by identity), so an object-keyed lru_cache
never hits across requests. Keying on the same geometry fingerprint the
matrix bundle uses makes the cache hit reliably - and deterministically,
which also removes the gmsh multithreading jitter from re-solving.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Callable, Hashable, TypeVar

T = TypeVar("T")


class GeometryLruCache:
    """Least-recently-used cache with a bounded size."""

    def __init__(self, maxsize: int = 6):
        self._store: "OrderedDict[Hashable, object]" = OrderedDict()
        self._maxsize = maxsize

    def get_or_compute(self, key: Hashable, factory: Callable[[], T]) -> T:
        hit = self._store.get(key)
        if hit is not None:
            self._store.move_to_end(key)
            return hit  # type: ignore[return-value]
        value = factory()
        self._store[key] = value
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)
        return value

    def clear(self) -> None:
        self._store.clear()
