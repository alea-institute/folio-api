# Pinned FOLIO test data

`folio.owl.gz` is the complete, unmodified FOLIO ontology from public commit
`79f77449c8566d7ac2fc193bed50812cfd2e84cb`, compressed with gzip (level 9, empty
filename, timestamp 0). Tests verify the decompressed SHA-256 before parsing.

- [Immutable source](https://raw.githubusercontent.com/alea-institute/FOLIO/79f77449c8566d7ac2fc193bed50812cfd2e84cb/FOLIO.owl)
- Raw size: 18,292,334 bytes
- Raw SHA-256: `b6ed82e6d17b7cb1d468453e4111ec08ca091d72a6849be2b58dd37692cb6ef9`
- Attribution: FOLIO, maintained by the ALEA Institute, originating from the
  SALI Alliance; [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  See [THIRD-PARTY.md](../../THIRD-PARTY.md).

The full corpus preserves the data selectors in the app-start and route tests.
It exercises the real FOLIO parser and indexes, including classes, properties,
curated roots, ancestor chains and pruned search branches. Missing or corrupt
data fails locally; tests never repair the fixture from a cache or download.

## Refreshing the snapshot

1. Select a reviewed public FOLIO commit and download its complete `FOLIO.owl`
   from the immutable raw URL outside pytest. Record its byte count and SHA-256.
2. Compress the bytes with Python's `gzip.GzipFile(filename="", mode="wb",
   fileobj=output, compresslevel=9, mtime=0)`. Preserve the previous fixture in
   Git before replacing it.
3. Update the source, digest and byte count here, the digest and branch in
   `tests/support.py`, and the byte-count check in `tests/test_test_environment.py`.
4. Run the full suite and report checker using the commands in the main README.
   Every existing assertion must run, with zero skips. Diagnose a corpus mismatch
   and choose a compatible complete revision; do not relax tests to fit the data.

Tests patch only raw OWL acquisition, configuration and optional provider
initialization. Default synchronous and asynchronous HTTPX transports reject
and record external attempts, including attempts whose errors get caught.
TestClient's in-process transport, sockets, event loops and logging remain real.
This is a guard on the current HTTPX callers, not a general network firewall.
