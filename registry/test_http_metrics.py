"""
HTTP Request Metrics Tests
==========================
Verifies that the registry API exposes RED (Rate / Errors / Duration) metrics
for every HTTP route via prometheus-fastapi-instrumentator, and that the
`handler` label carries the route *template* rather than the concrete request
path (which would produce unbounded cardinality from ids and slugs).

Run with: pytest registry/test_http_metrics.py -v
"""

TEMPLATED_ROUTE = "/api/v1/agents/{service_id}"
CONCRETE_PATH = "/api/v1/agents/metrics-probe-id"


def _exercise_route(client, mock_db):
    """Hit a templated GET route that returns a deterministic 404."""
    mock_db.query.return_value.filter.return_value.first.return_value = None
    response = client.get(CONCRETE_PATH)
    assert response.status_code == 404
    return response


def _metrics_lines(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    return response.text.splitlines()


class TestHttpRequestsTotal:
    def test_http_requests_total_is_exposed(self, client, mock_db):
        _exercise_route(client, mock_db)
        samples = [ln for ln in _metrics_lines(client) if ln.startswith("http_requests_total{")]
        assert samples, "no http_requests_total samples in /metrics exposition"

    def test_http_requests_total_has_handler_and_status_labels(self, client, mock_db):
        _exercise_route(client, mock_db)
        samples = [ln for ln in _metrics_lines(client) if ln.startswith("http_requests_total{")]
        assert any('handler="' in ln and 'status="404"' in ln for ln in samples), (
            f"http_requests_total missing handler/ungrouped-status labels: {samples[:5]}"
        )


class TestHttpRequestDuration:
    def test_duration_histogram_is_exposed_with_db_latency_buckets(self, client, mock_db):
        _exercise_route(client, mock_db)
        samples = [
            ln for ln in _metrics_lines(client)
            if ln.startswith("http_request_duration_seconds_bucket{")
        ]
        assert samples, "no http_request_duration_seconds_bucket samples in /metrics exposition"
        for edge in ("0.005", "0.05", "0.1", "0.25", "0.5", "1.0", "2.5", "5.0"):
            assert any(f'le="{edge}"' in ln for ln in samples), (
                f"histogram bucket le={edge} missing from http_request_duration_seconds"
            )


class TestHandlerLabelCardinality:
    def test_handler_label_is_route_template_not_raw_path(self, client, mock_db):
        _exercise_route(client, mock_db)
        lines = _metrics_lines(client)
        samples = [ln for ln in lines if ln.startswith("http_requests_total{")]
        assert any(f'handler="{TEMPLATED_ROUTE}"' in ln for ln in samples), (
            f"expected handler='{TEMPLATED_ROUTE}' in exposition, got: {samples[:10]}"
        )
        offenders = [ln for ln in lines if CONCRETE_PATH in ln]
        assert not offenders, (
            f"raw request path leaked into metric labels (cardinality risk): {offenders[:5]}"
        )


class TestExcludedHandlers:
    def test_scrape_endpoints_are_not_instrumented(self, client, mock_db):
        _exercise_route(client, mock_db)
        client.get("/healthz")
        samples = [ln for ln in _metrics_lines(client) if ln.startswith("http_requests_total{")]
        assert not any('handler="/metrics"' in ln for ln in samples), (
            "/metrics scrape endpoint should be excluded from HTTP metrics"
        )
        assert not any('handler="/healthz"' in ln for ln in samples), (
            "/healthz should be excluded from HTTP metrics"
        )
