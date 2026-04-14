from __future__ import annotations

from dataclasses import dataclass, field

from playwright.async_api import async_playwright


@dataclass(frozen=True)
class RenderRequest:
    url: str
    wait_for_selectors: list[str] = field(default_factory=list)
    timeout_ms: int = 30_000
    extra_http_headers: dict[str, str] = field(default_factory=dict)


async def render_pdf(request: RenderRequest) -> bytes:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        try:
            context = await browser.new_context(
                extra_http_headers=request.extra_http_headers
            )
            page = await context.new_page()
            await page.goto(request.url, wait_until="domcontentloaded", timeout=request.timeout_ms)
            for selector in request.wait_for_selectors:
                await page.wait_for_selector(selector, timeout=request.timeout_ms)
            # Wait for any element declaring it is still loading to finish
            await page.wait_for_function(
                "() => document.querySelectorAll('[data-loading=\"true\"]').length === 0",
                timeout=request.timeout_ms,
            )
            return await page.pdf(
                format="Letter",
                margin={"top": "0.75in", "bottom": "0.75in", "left": "0.75in", "right": "0.75in"},
                print_background=True,
            )
        finally:
            await browser.close()
