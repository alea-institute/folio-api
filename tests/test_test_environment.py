"""Regression coverage for the test harness's controlled input boundaries."""

import gzip
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from tests.support import (
    FIXTURE_PATH,
    CANON_FIXTURE_PATH,
    load_canon_snapshot,
    isolated_environment,
    load_snapshot,
    make_test_config,
)


@pytest.mark.parametrize(
    "loader,snapshot_path,expected_bytes,name",
    [
        (load_snapshot, FIXTURE_PATH, 18_292_334, "FOLIO"),
        (load_canon_snapshot, CANON_FIXTURE_PATH, 13_821_006, "Canon"),
    ],
)
def test_snapshot_is_complete_owl(loader, snapshot_path, expected_bytes, name):
    text = loader(snapshot_path)
    assert len(text.encode()) == expected_bytes
    assert "owl:Class" in text
    assert "owl:ObjectProperty" in text


@pytest.mark.parametrize(
    "loader,snapshot_path,expected_bytes,name",
    [
        (load_snapshot, FIXTURE_PATH, 18_292_334, "FOLIO"),
        (load_canon_snapshot, CANON_FIXTURE_PATH, 13_821_006, "Canon"),
    ],
)
@pytest.mark.parametrize("damage", ["missing", "truncated", "wrong-digest"])
def test_bad_snapshot_fails_without_fallback(
    tmp_path, damage, loader, snapshot_path, expected_bytes, name
):
    path = tmp_path / snapshot_path.name
    if damage == "truncated":
        path.write_bytes(snapshot_path.read_bytes()[:100])
    elif damage == "wrong-digest":
        path.write_bytes(gzip.compress(b"not the pinned ontology", mtime=0))
    with pytest.raises(RuntimeError, match=f"{name} test snapshot"):
        loader(path)


def test_config_is_fresh_and_has_no_provider_key():
    first = make_test_config()
    first["llm"]["api_key"] = "test-only-placeholder"
    first["api"]["title"] = "changed"
    assert make_test_config()["llm"]["api_key"] is None
    assert make_test_config()["api"]["title"] != "changed"


def test_fresh_collection_does_not_read_runtime_config_or_ontology_cache():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import os
import sys
from pathlib import Path

attempts = []
config = Path('config.json').resolve()
cache = Path.home() / '.folio' / 'cache'
def guard(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes)):
        path = Path(os.fsdecode(args[0])).resolve()
        if path == config or path.is_relative_to(cache):
            attempts.append('runtime config or ontology cache')
            raise AssertionError('test collection must use controlled local inputs')
sys.addaudithook(guard)
os.environ['OPENAI_API_KEY'] = 'test-only-placeholder'
import pytest
status = pytest.main(['--collect-only', '-q', 'tests', '--no-cov'])
assert not attempts, attempts
raise SystemExit(status)
""",
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "tests collected" in result.stdout


def test_sync_http_attempt_is_recorded_even_when_caught():
    with pytest.raises(AssertionError, match="Unexpected external attempts: HTTPX GET"):
        with isolated_environment() as environment:
            with httpx.Client() as client:
                with pytest.raises(RuntimeError, match="External HTTPX request"):
                    client.get("https://example.invalid/never-connect")
            assert environment.attempts == ["HTTPX GET"]


@pytest.mark.asyncio
async def test_async_http_attempt_is_recorded_even_when_caught():
    with pytest.raises(AssertionError, match="Unexpected external attempts: HTTPX GET"):
        with isolated_environment() as environment:
            async with httpx.AsyncClient() as client:
                with pytest.raises(RuntimeError, match="External HTTPX request"):
                    await client.get("https://example.invalid/never-connect")
            assert environment.attempts == ["HTTPX GET"]


@pytest.mark.parametrize(
    "name",
    [
        "OpenAIModel",
        "AnthropicModel",
        "GoogleModel",
        "GrokModel",
        "VLLMModel",
        "OpenAICompatibleModel",
    ],
)
def test_provider_is_blocked_before_key_lookup(name, monkeypatch):
    import alea_llm_client

    provider = getattr(alea_llm_client, name)

    def forbidden_lookup(*args, **kwargs):
        pytest.fail("provider credential lookup must not run")

    monkeypatch.setattr(provider, "get_api_key", forbidden_lookup)
    with pytest.raises(AssertionError, match="Unexpected external attempts: provider"):
        with isolated_environment() as environment:
            with pytest.raises(RuntimeError, match="Provider construction"):
                provider(model="test-only-model")
            assert environment.attempts == [f"provider {name}"]


def test_shutdown_error_still_checks_attempts_and_restores_patches():
    original_transport = httpx.HTTPTransport.handle_request

    @contextmanager
    def failing_lifespan():
        try:
            yield
        finally:
            with pytest.raises(RuntimeError, match="External HTTPX request"):
                httpx.get("https://example.invalid/shutdown")
            raise ValueError("shutdown failed")

    with pytest.raises(AssertionError, match="Unexpected external attempts") as caught:
        with isolated_environment():
            with failing_lifespan():
                pass
    assert isinstance(caught.value.__context__, ValueError)
    assert str(caught.value.__context__) == "shutdown failed"
    assert httpx.HTTPTransport.handle_request is original_transport


def test_clean_shutdown_error_is_not_suppressed():
    original_transport = httpx.HTTPTransport.handle_request
    with pytest.raises(ValueError, match="shutdown failed"):
        with isolated_environment():
            raise ValueError("shutdown failed")
    assert httpx.HTTPTransport.handle_request is original_transport


def test_real_startup_uses_local_inputs_and_disables_llm(folio, _booted_app):
    from folio_mcp import server

    assert folio.llm is None
    assert folio.object_properties
    assert _booted_app.state.config == make_test_config()
    assert server._shared_backend.folio is folio


def test_dummy_provider_environment_does_not_enable_llm(monkeypatch):
    from folio_api.api import initialize_folio

    monkeypatch.setenv("OPENAI_API_KEY", "test-only-placeholder")
    config = make_test_config()
    with isolated_environment():
        ontology = initialize_folio(config["folio"], config["llm"])
    assert ontology.llm is None
    assert ontology.classes


def test_local_owl_dispatches_by_source_url():
    from folio import FOLIO
    from folio_api.ontologies import CANON_SOURCE_URL

    assert FOLIO.load_owl(source_type="http", http_url=CANON_SOURCE_URL) == load_canon_snapshot()
    assert FOLIO.load_owl(source_type="github") == load_snapshot()
