"""Anonymized MCP usage telemetry: what *kinds* of queries are run, not what they were.

One JSON line per MCP tool call, appended to ``<dir>/mcp-YYYY-MM-DD.jsonl``
(UTC). Records never contain query text, pasted text, IRIs typed by the
user, IP addresses or exact timestamps. They hold only:

* ``hour`` (UTC, hour precision), ``tool``, ``client`` (the MCP client's
  self-reported ``clientInfo.name``, e.g. "claude-ai"), ``outcome``
  (ok / empty / invalid_input / error), and ``latency`` / ``results``
  buckets;
* for searches: a word-count bucket of the query, and the FOLIO **branch**
  and **concept label** of the top result (ontology data, not user data);
* for concept lookups: the looked-up concept's label and branch;
* for ``extract_concepts`` / ``extract_citations``: a text-length bucket,
  result counts, and counts by FOLIO branch or citation kind.

Config (``api`` block): ``mcp_telemetry`` (default true) and
``mcp_telemetry_dir`` (default ``<app root>/logs/telemetry``). Writing is
best-effort: any failure is logged once and telemetry turns itself off; it
can never affect a tool call.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger("folio_api.mcp_telemetry")
DEFAULT_DIR = Path(__file__).resolve().parent.parent / "logs" / "telemetry"
FOLIO_PREFIX = "https://folio.openlegalstandard.org/"

SEARCH_TOOLS = {"search_concepts", "search_definitions", "search_expanded", "query_concepts", "query_properties"}
CONCEPT_ARG = {
    "get_concept": "iri",
    "export_concept": "iri",
    "get_children": "iri",
    "get_parents": "iri",
    "find_connections": "subject_iri",
}
QUERY_ARGS = ("query", "label", "definition", "any_text", "alt_label", "example")


def _bucket(value: float, edges: list[tuple[float, str]], top: str) -> str:
    for edge, name in edges:
        if value < edge:
            return name
    return top


def latency_bucket(seconds: float) -> str:
    return _bucket(seconds, [(0.1, "<0.1s"), (0.5, "0.1-0.5s"), (2, "0.5-2s"), (5, "2-5s")], ">5s")


def count_bucket(n: int) -> str:
    return _bucket(n, [(1, "0"), (6, "1-5"), (21, "6-20"), (101, "21-100")], "100+")


def words_bucket(n: int) -> str:
    return _bucket(n, [(1, "0"), (2, "1"), (4, "2-3"), (8, "4-7")], "8+")


def chars_bucket(n: int) -> str:
    return _bucket(n, [(500, "<500"), (2000, "500-2k"), (10000, "2k-10k")], "10k+")


def _client(name: str | None) -> str:
    cleaned = re.sub(r"[^a-z0-9._ -]", "", (name or "").lower()).strip()[:40]
    return cleaned or "unknown"


def _items(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("results", "concepts", "citations"):
            if isinstance(payload.get(key), list):
                return [x for x in payload[key] if isinstance(x, dict)]
    return []


class MCPTelemetry:
    """Builds anonymized records from folio-mcp ToolCallEvents and appends them."""

    def __init__(self, directory: Path | str, folio_getter: Callable[[], Any]):
        self.directory = Path(directory)
        self._folio_getter = folio_getter
        self._branch_by_iri: dict[str, str] | None = None
        self.enabled = True

    # ---- ontology helpers (ontology data only) ---------------------------------------
    def _branch_map(self) -> dict[str, str]:
        if self._branch_by_iri is None:
            from folio_mcp.backends._branch_data import BRANCH_ROOT_IDS

            folio = self._folio_getter()
            mapping: dict[str, str] = {}
            if folio is not None:
                for branch, root_id in BRANCH_ROOT_IDS.items():
                    mapping.setdefault(FOLIO_PREFIX + root_id, branch)
                    for cls in folio.get_children(FOLIO_PREFIX + root_id, max_depth=64):
                        mapping.setdefault(cls.iri, branch)
            self._branch_by_iri = mapping
        return self._branch_by_iri

    def _branch(self, iri: str | None) -> str | None:
        if not iri:
            return None
        if not iri.startswith("http"):
            iri = FOLIO_PREFIX + iri.rsplit("/", 1)[-1]
        return self._branch_map().get(iri)

    def _concept(self, iri_or_id: Any) -> tuple[str | None, str | None]:
        """(label, branch) of an existing FOLIO concept; (None, None) otherwise."""
        folio = self._folio_getter()
        if folio is None or not isinstance(iri_or_id, str) or not iri_or_id.strip():
            return None, None
        try:
            cls = folio[iri_or_id.strip()]
        except Exception:  # noqa: BLE001
            cls = None
        if cls is None:
            return None, None
        return cls.label, self._branch(cls.iri)

    # ---- record ----------------------------------------------------------------------
    def record(self, event: Any) -> dict:
        args = event.arguments or {}
        try:
            payload = json.loads(event.result_text) if event.result_text else None
        except ValueError:
            payload = None
        items = _items(payload)

        returns_list = isinstance(payload, list) or (
            isinstance(payload, dict)
            and any(isinstance(payload.get(k), list) for k in ("results", "concepts", "citations"))
        )
        if event.error:
            outcome = "error"
        elif isinstance(payload, dict) and "error" in payload:
            outcome = "invalid_input"
        elif returns_list and not items:
            outcome = "empty"
        else:
            outcome = "ok"

        rec: dict[str, Any] = {
            "v": 1,
            "hour": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H"),
            "tool": event.tool,
            "client": _client(event.client),
            "outcome": outcome,
            "latency": latency_bucket(event.duration_s),
            "results": count_bucket(len(items)),
        }

        if event.tool in SEARCH_TOOLS:
            text = next((args[k] for k in QUERY_ARGS if isinstance(args.get(k), str) and args[k].strip()), "")
            rec["query_words"] = words_bucket(len(text.split()))
            if items:
                top = items[0]
                rec["concept"] = top.get("label") if isinstance(top.get("label"), str) else None
                rec["branch"] = self._branch(top.get("iri"))
            if event.tool == "search_expanded" and isinstance(payload, dict):
                rec["expansions"] = len(payload.get("expansions") or [])
                rec["expansion_source"] = payload.get("expansion_source")

        if event.tool in CONCEPT_ARG:
            label, branch = self._concept(args.get(CONCEPT_ARG[event.tool]))
            rec["concept"], rec["branch"] = label, branch

        if event.tool in ("get_taxonomy_branch", "query_concepts") or "branch" in args or "branch_name" in args:
            from folio_mcp.backends._branch_data import resolve_branch_name

            raw = args.get("branch_name", args.get("branch"))
            canonical = resolve_branch_name(raw) if isinstance(raw, str) else None
            if canonical:
                rec["branch_filter"] = canonical

        if event.tool in ("extract_concepts", "extract_citations"):
            text = args.get("text") if isinstance(args.get("text"), str) else ""
            rec["text_chars"] = chars_bucket(len(text))
            if event.tool == "extract_concepts":
                branches = Counter(str(x.get("branch")) for x in items if x.get("branch"))
                rec["branches"] = dict(branches.most_common(5))
            else:
                kinds = Counter(str(x.get("kind")) for x in items if x.get("kind"))
                rec["citation_kinds"] = dict(kinds.most_common(8))

        return {k: v for k, v in rec.items() if v is not None}

    # ---- sink ------------------------------------------------------------------------
    def observe(self, event: Any) -> None:
        """folio-mcp tool observer: never raises; disables itself on write failure."""
        if not self.enabled:
            return
        try:
            rec = self.record(event)
            self.directory.mkdir(parents=True, exist_ok=True)
            path = self.directory / f"mcp-{rec['hour'][:10]}.jsonl"
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, separators=(",", ":"), ensure_ascii=False) + "\n")
        except OSError:
            self.enabled = False
            LOGGER.warning("MCP telemetry disabled: cannot write to %s", self.directory, exc_info=True)
        except Exception:  # noqa: BLE001
            LOGGER.warning("MCP telemetry record failed", exc_info=True)
