"""Serve the real app with checked local inputs: python -m browser_tests.app."""

import asyncio
import signal
from contextlib import asynccontextmanager

import uvicorn

from tests.support import isolated_environment


def main():
    with isolated_environment():
        # Isolation must precede application imports and outlive server teardown.
        from folio_api.api import app

        original_lifespan = app.router.lifespan_context

        @asynccontextmanager
        async def ready_lifespan(application):
            async with original_lifespan(application):
                await asyncio.wait_for(
                    application.state.ontologies.wait_until_settled(), timeout=60
                )
                if application.state.ontologies.canon_state != "ready":
                    raise RuntimeError("Browser fixture Canon failed to initialize")
                yield

        app.router.lifespan_context = ready_lifespan
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=9616, lifespan="on")
        )
        # Uvicorn handles shutdown, then replays SIGTERM. Let the replay return
        # so isolation checks run and a clean shutdown has a zero exit status.
        previous = signal.signal(signal.SIGTERM, lambda *_: None)
        try:
            server.run()
            if not server.started or server.lifespan.shutdown_failed:
                raise RuntimeError("Browser fixture server did not complete cleanly")
        finally:
            signal.signal(signal.SIGTERM, previous)


if __name__ == "__main__":
    main()
