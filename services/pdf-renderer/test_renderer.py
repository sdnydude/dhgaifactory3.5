import asyncio

import pytest

from renderer import RenderRequest, render_pdf


@pytest.mark.asyncio
async def test_render_about_blank_returns_pdf_bytes() -> None:
    request = RenderRequest(
        url="about:blank",
        wait_for_selectors=[],
        timeout_ms=10_000,
    )
    pdf = await render_pdf(request)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1024
