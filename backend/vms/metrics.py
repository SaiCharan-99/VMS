"""Prometheus metrics.

Request latency is recorded per API process. Queue sizes are read from the jobs table at
scrape time, so they are correct however many workers run. Analysis durations are recorded
by each worker, which serves them on `VMS_WORKER_METRICS_PORT` when that is set.
"""

from collections.abc import Iterator

from prometheus_client import CollectorRegistry, Histogram
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector
from sqlalchemy import func, select

from vms.db.models import Job, JobStatus

# Separate registries: every worker would otherwise also report the (shared) queue gauges.
API_REGISTRY = CollectorRegistry(auto_describe=True)
WORKER_REGISTRY = CollectorRegistry(auto_describe=True)

REQUEST_LATENCY = Histogram(
    "vms_http_request_duration_seconds",
    "API request latency",
    ["method", "route", "status"],
    registry=API_REGISTRY,
)
ANALYSIS_DURATION = Histogram(
    "vms_analysis_duration_seconds",
    "Wall time of one video analysis in the worker",
    ["process_type", "outcome"],
    buckets=(5, 10, 20, 30, 45, 60, 90, 120, 180, 300, 600, 1200),
    registry=WORKER_REGISTRY,
)


class JobQueueCollector(Collector):
    def collect(self) -> Iterator[GaugeMetricFamily]:
        from vms.db import session_scope

        gauge = GaugeMetricFamily("vms_jobs", "Jobs by status", labels=["status"])
        try:
            with session_scope() as s:
                counts = dict(
                    s.execute(select(Job.status, func.count()).group_by(Job.status)).all()
                )
        except Exception:  # noqa: BLE001 - a scrape must not fail because the DB is down
            return
        for status in JobStatus:
            gauge.add_metric([status.value], counts.get(status, 0))
        yield gauge


API_REGISTRY.register(JobQueueCollector())
