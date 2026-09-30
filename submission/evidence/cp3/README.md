# CP3 evidence provenance

Official workload was read from ignored `config/challenge.json` with the configured seed and `--challenge --concurrency 5`. The challenge file and its raw query payloads are not included here.

- `baseline`, `incident`, `recovered`: each contains output from the real load test, metrics snapshots before/after, and exported application logs for that phase. Request payload previews are omitted from exported logs to avoid duplicating challenge inputs; other fields are retained. The full local source is `data/logs.jsonl`.
- `summary.json`: phase-local aggregates from response logs, not cumulative `/metrics` percentiles. P95 uses nearest rank (with five requests, this is the maximum). Client latency comes from load-test output and includes queueing/network overhead.
- `incident-observations.json`: actual Langfuse Observations API v2 response filtered to the selected trace/time window. Metadata is allowlisted; SDK key/resource metadata and query preview have been removed.
- `project.json`: identity returned by the authenticated project API, matching the observations' project ID.
- `verification.txt`: final validators and health after disabling the incident.

`../12-incident-metric.png` is a chart of phase-local log metrics; `../13-incident-log.png` renders the actual selected response log; `../14-incident-trace.png` renders actual API observation timings. These are not UI screenshots. For strict screenshot submission, capture the selected log in a terminal and the same trace in the Langfuse UI.

Langfuse API reference: https://langfuse.com/docs/api-and-data-platform/features/public-api
