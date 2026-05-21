"""Centralized Prometheus metrics for the registry API.

Every endpoint module imports from here instead of declaring its own.
This prevents duplicate-timeseries errors when multiple modules are
imported in the same process (e.g., during pytest collection).
"""
from prometheus_client import Counter, Histogram

registry_write_latency = Histogram(
    "registry_write_latency",
    "Database write latency in milliseconds",
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000],
)

registry_read_latency = Histogram(
    "registry_read_latency",
    "Database read latency in milliseconds",
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
)

registry_write_operations = Counter(
    "registry_write_operations",
    "Total number of write operations",
    ["operation"],
)

registry_read_operations = Counter(
    "registry_read_operations",
    "Total number of read operations",
    ["operation"],
)

registry_errors = Counter(
    "registry_errors",
    "Total number of registry errors",
    ["error_type"],
)

registry_db_errors = Counter(
    "registry_db_errors",
    "Total number of database connection errors",
)
