# Architecture: implemented foundation versus target

## Implemented foundation

`CSV bytes -> deterministic rules -> SQLite snapshots/findings -> explicit CLI review`.

The fixed synthetic questionnaire contains record_id, adults, children and household_size.
Counts must be integers from 0 to 100. This is a demonstration policy, not an NBS/WFP
questionnaire specification. The first five finding types are missing_id, duplicate_id,
missing_count, invalid_count and component_total. Schema/size/parser violations reject
the import. Missing/invalid prerequisites make the component-total check non-evaluable.

The prototype accepts UTF-8/UTF-8-BOM, at most 1 MiB and 2,000 records. Duplicate headers,
wrong field counts and unknown columns are rejected. Blank CSV lines follow the standard
CSV reader's behaviour; row_number identifies a parsed record, not its physical line.

Stored source bytes are immutable through application operations, addressed by SHA-256
and checked before a new validation. Runs are immutable evidence snapshots. Findings
have independent internal IDs, because survey IDs can be duplicated or missing.
Review events store prior/new status, reason in the payload, revision, request ID and
UTC time. SQL statements use bound data parameters. Local filesystem access can still
alter the database; this is not a certified or tamper-proof audit trail.

`validate_batch` uses an idempotent request ID, while a new request creates a new run.
Decisions do not silently transfer to a fresh run. Summaries separate total findings,
affected records, non-evaluable checks and unresolved review findings. Pagination
includes total_matching and next_offset; a page is not the whole batch.

## Adapter included, not yet executed end-to-end

The optional MCP SDK v2 adapter exposes only validate_batch, list_findings and
get_review_summary over Streamable HTTP. It only accepts previously registered batch
IDs, never arbitrary filenames. Review writes remain outside MCP on the trusted CLI.

LocalGuard validates a strong local token, exact loopback Host values and allowed
browser Origins, rejecting duplicate security headers. Unit tests exercise the guard
itself; they do not establish complete MCP transport security. The SDK ASGI lifespan
is forwarded, not mounted without its startup hook. The transport body limit is 64 KiB.

This is a single-user development boundary, not multi-tenant isolation or public OAuth.
An authorised MCP client can read the registered synthetic batches. There is no cloud
fallback, shell tool, SQL tool, arbitrary file accessor or outbound fetch tool.

## Still to implement/verify

Complete the real HTTP test and lock dependencies, then build a Streamlit interface,
a bounded local-model controller, explicit UI approvals and exports. The interface
must call the real MCP client, not bypass it with direct validation imports. Model
responses remain separate from authoritative calculations. Real model inference,
latency, Windows behaviour and full offline operation must be measured, not inferred.

## Primary implementation references checked on 27 September 2026

- MCP SDK server API: https://py.sdk.modelcontextprotocol.io/run/asgi/
- MCP SDK client API: https://py.sdk.modelcontextprotocol.io/client/
- MCP SDK HTTP client configuration: https://py.sdk.modelcontextprotocol.io/client/transports/
- MCP 2025-11-25 transport requirements: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports

These references guided the unverified adapter; they are not proof it ran in this environment.
