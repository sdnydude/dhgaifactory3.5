# dhg-pdf-renderer

Sibling service that renders Next.js print routes to PDF via Playwright/Chromium.
Only the Registry API should call this service; it is not exposed to users.

Endpoints:
- GET /health — liveness
- POST /render-sync — render a print URL to PDF and return the bytes
