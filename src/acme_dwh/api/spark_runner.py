"""Trigger the containerized Spark jobs from the host (used by the /analytics API).

The Spark jobs run inside the `spark` service defined in docker-compose.yml. This
module shells out to ``docker compose exec`` to launch ``spark-submit`` for a job,
passing the target asset/source as environment variables (never interpolated into
a shell string — args are a list and shell=False — so user input cannot inject).
"""
from __future__ import annotations

import logging
import re
import subprocess
import time
from pathlib import Path

log = logging.getLogger(__name__)

# job key -> (script in /opt/jobs, whether it takes ASSET_ID/DATA_SOURCE_ID)
JOBS: dict[str, tuple[str, bool]] = {
    "aggregation": ("aggregation_job.py", False),
    "regression": ("regression_job.py", True),
}

_CONNECTOR = "com.datastax.spark:spark-cassandra-connector_2.12:3.5.1"
_ID_RE = re.compile(r"^[A-Za-z0-9._/\-]{1,64}$")
_DEFAULT_TIMEOUT = 600  # seconds


class SparkJobError(RuntimeError):
    """Raised when a Spark job cannot be launched or fails."""


def _project_root() -> Path:
    """Walk up from this file to the directory holding docker-compose.yml."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "docker-compose.yml").is_file():
            return parent
    raise SparkJobError("Could not locate docker-compose.yml (project root).")


def _validate_id(label: str, value: str) -> str:
    if not _ID_RE.match(value):
        raise SparkJobError(f"Invalid {label}: {value!r}")
    return value


def run_job(
    job: str,
    asset_id: str | None = None,
    data_source_id: str | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict:
    """Launch a Spark job and return a structured result dict."""
    if job not in JOBS:
        raise SparkJobError(f"Unknown job {job!r} (expected one of {sorted(JOBS)}).")
    script, takes_target = JOBS[job]

    env_flags: list[str] = []
    if takes_target:
        asset_id = _validate_id("assetId", asset_id or "BTCUSD")
        data_source_id = _validate_id("dataSourceId", data_source_id or "BITFINEX")
        env_flags = ["-e", f"ASSET_ID={asset_id}", "-e", f"DATA_SOURCE_ID={data_source_id}"]

    cmd = [
        "docker", "compose", "exec", "-T", *env_flags, "spark",
        "/opt/spark/bin/spark-submit", "--master", "local[*]",
        "--packages", _CONNECTOR,
        "--conf", "spark.jars.ivy=/tmp/.ivy2",
        "--conf", "spark.cassandra.connection.host=cassandra",
        "--conf", "spark.log.level=WARN",
        f"/opt/jobs/{script}",
    ]

    log.info("Launching Spark job %s (asset=%s source=%s)", job, asset_id, data_source_id)
    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd, cwd=_project_root(), capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        raise SparkJobError("Docker CLI not found on the host. Is Docker installed and on PATH?")
    except subprocess.TimeoutExpired:
        raise SparkJobError(f"Spark job {job!r} timed out after {timeout}s.")
    duration = round(time.monotonic() - started, 1)

    output = (proc.stdout or "") + (proc.stderr or "")
    tail = "\n".join(output.strip().splitlines()[-12:])

    if proc.returncode != 0:
        if "no such service" in output.lower() or "is not running" in output.lower():
            raise SparkJobError(
                "The 'spark' container is not running. Start it with "
                "`docker compose up -d spark` and try again."
            )
        raise SparkJobError(f"Spark job {job!r} failed (exit {proc.returncode}).\n{tail}")

    m = re.search(r"wrote\s+(\d+)", output)
    rows = int(m.group(1)) if m else None
    msg = f"{job} job completed in {duration}s"
    if rows is not None:
        msg += f" - wrote {rows} rows"

    return {
        "ok": True,
        "job": job,
        "assetId": asset_id if takes_target else None,
        "dataSourceId": data_source_id if takes_target else None,
        "rowsWritten": rows,
        "durationSeconds": duration,
        "message": msg,
        "logTail": tail,
    }
