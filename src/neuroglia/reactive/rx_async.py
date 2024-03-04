# import asyncio
from rx import operators as ops
from rx.core.observable.observable import Observable
from typing import Any, Callable

import rx


class AsyncRx:

    @staticmethod
    def subscribe(source: Observable, on_next: Callable[[Any], None]):
        return source.pipe(
            ops.map(lambda value: rx.from_future(on_next(value))),
            ops.concat()
        ).subscribe(lambda e: None)
