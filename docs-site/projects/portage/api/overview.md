---
title: API Overview
sidebar_position: 1
---

# API Overview

The Portage API is an **Express 5** REST API running on port 8016. All endpoints return JSON and require HTTPS.

## Base URL

```
https://localhost:8016        # Local development
https://portage-api.digitalharmonyai.com  # Production
```

## Authentication

Most endpoints require a JWT bearer token:

```
Authorization: Bearer <access_token>
```

See [Authentication](/portage/api/authentication) for login, registration, and token refresh flows.

## Request Format

- **Content-Type**: `application/json` for request bodies
- **File uploads**: `multipart/form-data` (image endpoints only)

## Response Format

All responses follow a consistent shape:

```json
// Success
{
  "items": [...],
  "total": 42
}

// Error
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Title is required",
    "details": ["title: Required"]
  }
}
```

## Endpoint Groups

| Group | Prefix | Description |
|-------|--------|-------------|
| [Authentication](/portage/api/authentication) | `/auth` | Login, register, refresh, profile |
| [Items](/portage/api/items) | `/items` | Inventory CRUD, comps, export |
| [Images](/portage/api/images) | `/images` | Upload, enhance, background removal |
| [Scan](/portage/api/scan) | `/scan` | AI item identification |
| [Listings](/portage/api/listings) | `/listings` | Marketplace listing management |
| [Orders](/portage/api/orders) | `/orders` | Order tracking and shipping |
| [Drafts](/portage/api/drafts) | `/drafts` | Listing draft persistence |
| [Shipping](/portage/api/shipping) | `/shipping` | Presets, rates, labels, providers |
| [Marketplace](/portage/api/marketplace) | `/marketplace` | OAuth and account management |
| [Porter](/portage/api/porter) | `/porter` | AI assistant chat |
| [Admin](/portage/api/admin) | `/admin` | System administration |

## Rate Limiting

Free-tier users have daily limits on AI scan requests. See the scan endpoint documentation for details.

## Error Handling

All errors use the `AppError` class with HTTP status codes and machine-readable error codes. See [Error Handling](/portage/api/error-handling) for the full error code reference.
