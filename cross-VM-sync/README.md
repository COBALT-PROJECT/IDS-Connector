# Cross-VM IDS Sync Service

Standalone service that keeps a TRUE Connector **provider** (`tc-provider`) and **consumer** (`tc-consumer`) in sync when they run on separate VMs/nodes instead of the same cluster. It polls the provider's catalog over its NodePort, diffs it against what it has already seen, and relays new resources to the consumer. It exposes a small HTTP health/metrics endpoint (default port `8080`).

Deploy this **after** `IDS_connector_SDT` is up.

## `docker/` — the real, deployed service

This is the canonical source. Building and running the actual pod uses only this folder:

| File | Purpose |
|---|---|
| `ids_sync_service.py` | The sync service entry point that actually runs in the container/pod. |
| `Dockerfile` | Builds the image, copying in `ids_sync_service.py` and `requirements.txt`. |
| `docker-compose.yml` | Runs the image locally with Docker Compose (hardcoded env vars) — useful for testing the container before deploying it as a pod. |
| `crossVM_ids_sync_service.yml` | Kubernetes manifest (Deployment + Secret + Service + ConfigMap) — **this is what gets `kubectl apply`'d** to run the sync service as a pod in the cluster. |
| `requirements.txt` | Python dependencies for the image. |
| `run_pod_instructions.txt` | One-line deploy/log instructions: `kubectl apply -f crossVM_ids_sync_service.yml`, run after `IDS_connector_SDT` is deployed. |
| `logs/` | Log directory mounted into the running container/pod. |

## Root-level files — earlier test/dev iterations, kept for history

These predate the dockerized pod and were used while developing the sync logic before it was finalized. **They are not used to build or run the pod** — `docker/ids_sync_service.py` is canonical and should be edited instead of these.

| File | Purpose |
|---|---|
| `crossvm-ids-sync.py` | First working version of the sync service (Dec 16, 2025), run directly with `python3` for early local testing before containerizing. |
| `cross-ids-sync2.py` | Second, enhanced iteration (Dec 23, 2025, "v2.0") adding a `/resources` debug endpoint and misc. fixes. This became `docker/ids_sync_service.py` once finalized — the two files are byte-identical. |
| `test-extraction.py` | One-off diagnostic script used to inspect `tc-provider`'s `/api/selfDescription/` response and figure out the correct `ids:resourceCatalog` / `ids:offeredResource` JSON structure before writing the sync/parsing logic. |
| `config.env` | Reference env vars for running the scripts above directly with `python3` during local development. Not read by the Docker build — the pod gets its configuration from `crossVM_ids_sync_service.yml` (or `docker-compose.yml` for local container runs) instead. |
| `logs/` | Log output from running the scripts above locally. |

## Configuration

Environment variables (set in `crossVM_ids_sync_service.yml` for the pod, or `docker-compose.yml` / `config.env` for local runs):

| Variable | Description |
|---|---|
| `PROVIDER_URL` | NodePort URL of `tc-provider` on the remote VM, e.g. `https://ai-target-of-evaluation.cobalt.local:30578`. |
| `CONSUMER_URL` | URL of `tc-consumer`, e.g. `https://tc-consumer:8444` (in-cluster service name) or a direct IP for local testing. |
| `IDS_USERNAME` / `IDS_PASSWORD` | Basic auth credentials for both connectors (pulled from the `ids-sync-credentials` Secret in the pod). |
| `POLL_INTERVAL_SECONDS` | How often to poll the provider's catalog. |
| `MAX_RETRIES` / `RETRY_BACKOFF_SECONDS` | Retry behaviour on connection failure. |
| `LOG_LEVEL` / `LOG_DIR` | Logging verbosity and output directory. |
| `HEALTH_PORT` | Port for the `/health` and `/metrics` endpoints (default `8080`). |

## Health & metrics endpoints

- `GET /health` — status, uptime, sync counters, last error, provider/consumer URLs.
- `GET /metrics` — plain-text metrics.
- `GET /resources` — tracked resource IDs (added in the `cross-ids-sync2.py` / `ids_sync_service.py` version only).

## Deployment

```bash
kubectl apply -f docker/crossVM_ids_sync_service.yml

# View logs
kubectl logs <ids-sync-service pod name>
```
