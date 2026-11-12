"""Local inputs for integration tests; the parser and app lifespans stay real."""

import gzip
import hashlib
import tempfile
import zlib
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch

import httpx

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "folio.owl.gz"
FIXTURE_SHA256 = "b6ed82e6d17b7cb1d468453e4111ec08ca091d72a6849be2b58dd37692cb6ef9"


CANON_FIXTURE_PATH = FIXTURE_PATH.with_name("canon.owl.gz")
CANON_FIXTURE_SHA256 = "add8b2b140273b197b759f8945b4f5aa66ecb1ec801fcc69431f1b4baaf59f24"


def load_snapshot(
    path: Path = FIXTURE_PATH, *, digest: str = FIXTURE_SHA256, name: str = "FOLIO"
) -> str:
    """Reject missing or damaged input instead of falling back to a download."""
    try:
        with gzip.open(path, "rb") as archive:
            raw = archive.read()
    except (OSError, EOFError, zlib.error) as exc:
        raise RuntimeError(
            f"Cannot read {name} test snapshot; see tests/fixtures/README.md"
        ) from exc
    if hashlib.sha256(raw).hexdigest() != digest:
        raise RuntimeError(
            f"{name} test snapshot SHA-256 mismatch; see tests/fixtures/README.md"
        )
    return raw.decode("utf-8")


def load_canon_snapshot(path: Path = CANON_FIXTURE_PATH) -> str:
    return load_snapshot(path, digest=CANON_FIXTURE_SHA256, name="Canon")


TEST_TELEMETRY_DIR = str(Path(tempfile.gettempdir()) / "folio-api-test-telemetry")


def make_test_config() -> dict:
    """Return a fresh nonsecret config without touching runtime configuration."""
    return {
        "api": {
            "title": "FOLIO API tests",
            "description": "Isolated integration tests",
            "version": "test",
            "terms_of_service": "https://example.invalid/terms",
            "contact": {},
            # Keep test runs' MCP telemetry out of the repo's logs/ directory.
            "mcp_telemetry_dir": TEST_TELEMETRY_DIR,
            "logging": {
                "version": 1,
                "disable_existing_loggers": False,
                "handlers": {"console": {"class": "logging.StreamHandler"}},
                "loggers": {
                    "folio_api": {
                        "handlers": ["console"],
                        "level": "WARNING",
                        "propagate": False,
                    }
                },
            },
        },
        "folio": {
            "source": "github",
            "repository": "alea-institute/FOLIO",
            "branch": "79f77449c8566d7ac2fc193bed50812cfd2e84cb",
        },
        "llm": {"type": "openai", "model": "test-only-model", "api_key": None},
    }


@dataclass
class ExternalAttempts:
    """Keep failures visible even when a dependency catches the exception."""

    attempts: list[str] = field(default_factory=list)

    def assert_clean(self):
        assert not self.attempts, "Unexpected external attempts: " + ", ".join(
            self.attempts
        )


@contextmanager
def isolated_environment():
    """Guard collection through teardown, without changing sockets or logging."""
    environment = ExternalAttempts()

    def reject_http(transport, request):
        environment.attempts.append(f"HTTPX {request.method}")
        raise RuntimeError("External HTTPX request disabled in isolated tests")

    async def reject_async_http(transport, request):
        return reject_http(transport, request)

    def reject_provider(instance, *args, **kwargs):
        environment.attempts.append(f"provider {type(instance).__name__}")
        raise RuntimeError("Provider construction disabled in isolated tests")

    with ExitStack() as patches:
        patches.enter_context(
            patch.object(httpx.HTTPTransport, "handle_request", reject_http)
        )
        patches.enter_context(
            patch.object(
                httpx.AsyncHTTPTransport, "handle_async_request", reject_async_http
            )
        )

        import alea_llm_client
        import folio.graph
        from folio_api import api_config

        for name in (
            "OpenAIModel",
            "AnthropicModel",
            "GoogleModel",
            "GrokModel",
            "VLLMModel",
            "OpenAICompatibleModel",
        ):
            patches.enter_context(
                patch.object(
                    getattr(alea_llm_client, name), "__init__", reject_provider
                )
            )
        # folio-python 0.3.6 otherwise constructs OpenAIModel when llm=None.
        patches.enter_context(patch.object(folio.graph, "alea_llm_client", None))
        patches.enter_context(patch.object(api_config, "load_config", make_test_config))

        def local_owl(**kwargs):
            from folio_api.ontologies import CANON_SOURCE_URL

            if kwargs.get("http_url") == CANON_SOURCE_URL:
                return load_canon_snapshot()
            return load_snapshot()

        patches.enter_context(
            patch.object(folio.graph.FOLIO, "load_owl", staticmethod(local_owl))
        )
        try:
            yield environment
        finally:
            environment.assert_clean()
