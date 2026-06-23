"""
Reactive programming support with RxPy integration.

Provides observable streams for reactive data processing and
event-driven programming patterns.

For detailed information about reactive programming, see:
https://bvandewe.github.io/pyneuro/patterns/reactive-programming/
"""
from collections.abc import Callable
from typing import Any

import rx
from rx import operators as ops
from rx.core.observable.observable import Observable

# import asyncio


class AsyncRx:
    @staticmethod
    def subscribe(source: Observable, on_next: Callable[[Any], None]):
        return source.pipe(ops.map(lambda value: rx.from_future(on_next(value))), ops.concat()).subscribe(lambda e: None)
