"""cassandra-driver compatibility for Windows + CPython >= 3.12.

Kept here so the rest of the DAL stays clean. Two issues:

1. Import-time reactor guard: cassandra.cluster picks a default reactor at import
   from {gevent, eventlet, libev, asyncore}; on Windows none exist (no libev wheel;
   asyncore removed in 3.12), so importing the module itself raises. We register a
   minimal fake `asyncore` purely to satisfy that guard — the asyncore reactor is
   never used (we force the asyncio reactor). gevent is unsuitable: deprecated in
   3.30 and requires full monkey-patching, which would break our asyncio process.

2. Windows event loop: the asyncio reactor calls loop.remove_reader/writer on close,
   which the default Windows ProactorEventLoop does not implement, so we hand the
   driver's own background loop a SelectorEventLoop. Scoped to that loop only — it
   never touches the process policy or uvicorn.
"""
from __future__ import annotations

import sys
import types

_shim_applied = False


def apply() -> None:
    global _shim_applied
    if _shim_applied or "asyncore" in sys.modules:
        _shim_applied = True
        return
    try:
        import asyncore  # noqa: F401
    except ModuleNotFoundError:
        stub = types.ModuleType("asyncore")

        class _Dispatcher:
            def __init__(self, *a, **k):
                pass

        stub.dispatcher = _Dispatcher
        stub.loop = lambda *a, **k: None
        stub.socket_map = {}
        stub.close_all = lambda *a, **k: None
        sys.modules["asyncore"] = stub
    _shim_applied = True


def ensure_windows_selector_loop() -> None:
    if sys.platform != "win32":
        return
    import asyncio

    from cassandra.io.asyncioreactor import AsyncioConnection

    if AsyncioConnection._loop is None:
        AsyncioConnection._loop = asyncio.SelectorEventLoop()
