"""Phase 12.2 — uvloop runtime at the server entry point."""
import asyncio

import uvloop

from backend.server_entry import install_uvloop


def test_install_uvloop_sets_uvloop_policy():
    """install_uvloop() makes the active asyncio policy uvloop's."""
    original = asyncio.get_event_loop_policy()
    try:
        install_uvloop()
        assert isinstance(asyncio.get_event_loop_policy(), uvloop.EventLoopPolicy)
    finally:
        asyncio.set_event_loop_policy(original)
