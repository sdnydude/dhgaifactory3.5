from medkb.metrics import QUERY_REQUESTS, QUERY_LATENCY, QUERY_ERRORS


def test_query_requests_counter_exists():
    assert QUERY_REQUESTS._name == "medkb_query_requests"


def test_query_latency_histogram_exists():
    assert QUERY_LATENCY._name == "medkb_query_latency_seconds"


def test_query_errors_counter_exists():
    assert QUERY_ERRORS._name == "medkb_query_errors"
