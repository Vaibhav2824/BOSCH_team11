"""All endpoints and knobs in one place. Override any of them with env vars."""
import os

PROM_URL = os.getenv("PROM_URL", "http://localhost:9090")
# Jaeger v2 in the demo serves its UI and API under /jaeger/ui behind the frontend proxy
JAEGER_URL = os.getenv("JAEGER_URL", "http://localhost:8080/jaeger/ui")
# OpenSearch has no fixed host port in the demo; leave empty to auto-detect via Docker
OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "")
LOG_INDEX = os.getenv("LOG_INDEX", "otel-logs-*")

# Any litellm model string: "gpt-4o-mini", "anthropic/claude-sonnet-4-5", "gemini/gemini-2.0-flash", ...
MODEL = os.getenv("AGENT_MODEL", "gpt-4o-mini")
MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "8"))
ESCALATE_BELOW = float(os.getenv("AGENT_ESCALATE_BELOW", "0.55"))

# Services whose telemetry is noise for diagnosis (Locust's own spans)
IGNORE_SERVICES = set(os.getenv("IGNORE_SERVICES", "load-generator").split(","))
BASELINE_FILE = os.getenv("BASELINE_FILE", "baseline.json")
RUNS_DIR = os.getenv("RUNS_DIR", "runs")
