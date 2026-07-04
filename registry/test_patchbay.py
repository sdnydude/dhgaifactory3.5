"""
Patchbay Status Tests
=====================
Unit tests for patchbay_service.py — TCP service probes with TTL cache.

Run with: pytest registry/test_patchbay.py -v
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_probe_ports_maps_up_and_down():
    import patchbay_service as svc

    async def fake_probe(host, port):
        return port == 3001  # only grafana's port answers

    services = {"grafana": 3001, "logo-maker": 8012}
    with patch.object(svc, "_probe", new=fake_probe):
        result = asyncio.run(svc.probe_services(services))

    assert result["grafana"] == "up"
    assert result["logo-maker"] == "down"


def test_get_status_uses_cache_within_ttl():
    import patchbay_service as svc

    svc._cache["data"] = None
    svc._cache["at"] = 0.0
    calls = {"n": 0}

    async def counting_probe(services):
        calls["n"] += 1
        return {k: "up" for k in services}

    with patch.object(svc, "probe_services", new=counting_probe), \
         patch.object(svc, "SERVICES", {"grafana": 3001}), \
         patch.object(svc, "_now", side_effect=[100.0, 105.0]):
        first = asyncio.run(svc.get_status())   # _now=100 → probes (call 1)
        second = asyncio.run(svc.get_status())  # _now=105, within 10s TTL → cached
    assert first["services"] == {"grafana": "up"}
    assert second["services"] == {"grafana": "up"}
    assert calls["n"] == 1  # second call served from cache
