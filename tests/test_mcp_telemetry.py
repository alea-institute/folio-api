"""Anonymized MCP telemetry: records what kind of call ran, never what the user typed."""

import json
from pathlib import Path

import pytest
from folio_mcp.observer import ToolCallEvent

from folio_api.mcp_telemetry import MCPTelemetry
from tests.support import TEST_TELEMETRY_DIR

CONTRACT_LAW = "https://folio.openlegalstandard.org/RCIPwpgRpMs1eVz4vPid0pV"
SECRET_WORDS = ["Quokkafell", "Zzqqv", "Bartholomew", "Elmstreet", "4711"]


def _event(tool, args, result, **kw):
    return ToolCallEvent(tool=tool, arguments=args, result_text=json.dumps(result), duration_s=0.2, client="Claude-AI", **kw)


@pytest.fixture
def telemetry(folio, tmp_path):
    return MCPTelemetry(tmp_path, lambda: folio)


def test_search_record_keeps_concept_and_branch_not_query(telemetry):
    query = "Bartholomew Quokkafell breach of contract at 4711 Elmstreet"
    rec = telemetry.record(_event("search_concepts", {"query": query, "limit": 5},
                                  [{"iri": CONTRACT_LAW, "label": "Contract Law"}]))
    assert rec["tool"] == "search_concepts" and rec["client"] == "claude-ai"
    assert rec["outcome"] == "ok" and rec["results"] == "1-5" and rec["latency"] == "0.1-0.5s"
    assert rec["query_words"] == "8+"
    assert rec["concept"] == "Contract Law" and rec["branch"] == "areas_of_law"
    assert len(rec["hour"]) == 13  # YYYY-MM-DDTHH: hour precision only
    blob = json.dumps(rec)
    assert not any(w.lower() in blob.lower() for w in SECRET_WORDS), blob


def test_concept_lookup_resolves_ontology_label(telemetry):
    rec = telemetry.record(_event("get_children", {"iri": "RCIPwpgRpMs1eVz4vPid0pV"}, [{"iri": "x", "label": "y"}]))
    assert rec["concept"] == "Contract Law" and rec["branch"] == "areas_of_law"


def test_unknown_concept_and_free_text_are_dropped(telemetry):
    rec = telemetry.record(_event("get_concept", {"iri": "Bartholomew Quokkafell"}, {"error": "Concept not found"}))
    assert rec["outcome"] == "invalid_input"
    assert "concept" not in rec and "Quokkafell" not in json.dumps(rec)


def test_extract_concepts_counts_branches_only(telemetry):
    text = "Bartholomew Quokkafell, tenant at 4711 Elmstreet, was evicted by the landlord. " * 20
    result = {"count": 2, "concepts": [{"iri": "a", "label": "Tenant", "branch": "actors_players"},
                                       {"iri": "b", "label": "Landlord", "branch": "actors_players"}]}
    rec = telemetry.record(_event("extract_concepts", {"text": text}, result))
    assert rec["text_chars"] == "500-2k" and rec["branches"] == {"actors_players": 2}
    assert not any(w.lower() in json.dumps(rec).lower() for w in SECRET_WORDS)


def test_error_and_branch_filter(telemetry):
    rec = telemetry.record(ToolCallEvent(tool="query_concepts", arguments={"label": "Zzqqv", "branch": "Areas of Law"},
                                         error="ToolError", client=None))
    assert rec["outcome"] == "error" and rec["client"] == "unknown" and rec["branch_filter"] == "areas_of_law"


def test_unwritable_directory_disables_quietly(folio, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("not a directory")
    t = MCPTelemetry(blocker / "sub", lambda: folio)
    t.observe(_event("list_branches", {}, {"areas_of_law": 1}))  # must not raise
    assert t.enabled is False


def _post(client, body, session_id=None):
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
               "Host": "folio.openlegalstandard.org"}
    if session_id:
        headers["mcp-session-id"] = session_id
    return client.post("/mcp", headers=headers, json=body)


def test_end_to_end_mcp_calls_write_anonymized_lines(started_client, _booted_app):
    telemetry = _booted_app.state.mcp_telemetry
    assert telemetry is not None and str(telemetry.directory) == TEST_TELEMETRY_DIR
    for f in Path(TEST_TELEMETRY_DIR).glob("mcp-*.jsonl"):
        f.unlink()

    init = _post(started_client, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "Telemetry-Probe", "version": "0"}}})
    sid = init.headers["mcp-session-id"]
    _post(started_client, {"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
    calls = [
        ("search_concepts", {"query": "Bartholomew Quokkafell contract law", "limit": 3}),
        ("extract_concepts", {"text": "Bartholomew Quokkafell, tenant at 4711 Elmstreet, sued the landlord."}),
        ("get_parents", {"iri": "RCIPwpgRpMs1eVz4vPid0pV"}),
        ("search_concepts", {"query": "   "}),
    ]
    for i, (tool, args) in enumerate(calls, start=2):
        r = _post(started_client, {"jsonrpc": "2.0", "id": i, "method": "tools/call",
                                   "params": {"name": tool, "arguments": args}}, sid)
        assert r.status_code == 200, r.text

    lines = [json.loads(line) for f in Path(TEST_TELEMETRY_DIR).glob("mcp-*.jsonl") for line in f.read_text().splitlines()]
    assert [x["tool"] for x in lines] == [c[0] for c in calls]
    assert {x["client"] for x in lines} == {"telemetry-probe"}
    assert lines[0]["outcome"] == "ok" and lines[0].get("branch")
    assert lines[1]["text_chars"] == "<500" and lines[1]["branches"]
    assert lines[2]["concept"] == "Contract Law"
    assert lines[3]["outcome"] == "invalid_input"
    raw = "".join(f.read_text() for f in Path(TEST_TELEMETRY_DIR).glob("mcp-*.jsonl")).lower()
    assert not any(w.lower() in raw for w in SECRET_WORDS), raw
    assert "ip" not in {k for x in lines for k in x}
