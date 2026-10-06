---
id: offerup
title: OfferUp
sidebar_position: 9
---

# OfferUp

OfferUp has no public API; these endpoints serve the **Portage Assistant**
browser extension flow (see [Architecture → OfferUp Assisted Post](/portage/architecture/offerup-assisted-post)).
All require a bearer token **and** pass `requireOfferUpAccess` — tier
`beta-tester` or role `admin` — else `403 OFFERUP_BETA_ONLY`.

## Connection

### `POST /marketplace/offerup/connect`

Records that the extension is installed in this user's browser and that the
§8.1 consent was accepted. Rate limit 5 / 15 min. `consentVersion` must be
the current text's version (`OFFERUP_CONSENT_VERSION`), else 400. A
re-connect with the same consent version only refreshes `extensionVersion`
— `consentAcceptedAt` is the original acceptance. Admins never count against
the free-tier marketplace limit (beta-testers are unlimited).

```json
{ "extensionVersion": "0.1.0", "consentVersion": "2026-10-03" }
```

| Status | Code | Meaning |
|---|---|---|
| 200 | — | `{ "connected": true }` (insert or refresh) |
| 400 | `VALIDATION_ERROR` | `consentVersion` is not the current consent text |
| 403 | `MARKETPLACE_LIMIT_REACHED` | Free plan already has its one marketplace (not applied to admins) |
| 409 | `OFFERUP_VERSION_UNKNOWN` | `extensionVersion` not in `OFFERUP_EXTENSION_VERSIONS` |

### `GET /marketplace/offerup/status`

`{ connected, connectedAt, extensionVersion, consentAcceptedAt, consentVersion }`
— `connected: false` with nulls when there is no account row.

### `DELETE /marketplace/offerup/disconnect`

Removes the account row only; listings keep their rows. `{ "disconnected": true }`.
After it, `/handoff`, `/posted` and `/snapshot` answer `409 OFFERUP_NOT_CONNECTED`
until the next connect; the web page also tells the extension to forget
consent, the remembered user and queued reports.

### `extensionVersion` on every call

`/listings/:id/offerup/handoff`, `/listings/:id/offerup/posted` and
`/marketplace/offerup/snapshot` accept an optional `extensionVersion` (the
page sends the bridge hello's version). A value not in
`OFFERUP_EXTENSION_VERSIONS` → `409 OFFERUP_VERSION_UNKNOWN`, so a build
removed from the allowlist stops posting and reporting, not only connecting.

### `GET /marketplace/offerup/taxonomy`

The committed OfferUp category tree `{ capturedAt, source, roots: [{ label, children }] }`
(14 roots, 1110 leaves, captured 2026-10-04) for the web category picker.

## Listings

### `POST /listings` with `marketplace: "offerup"`

Draft only. `publishMode` other than `draft` or `publishImmediately: true` →
`400 OFFERUP_DRAFT_ONLY`. `marketplaceSpecificFields` may carry
`{ condition, categoryPath }`; the server-owned keys (`postedTitle`,
`postedPrice`, `offerupItemId`, `postedVia`, `zip`, `consentVersion`,
`lastHandoffAt`, `lastSnapshotAt`) are stripped from client input on create
and on `PATCH /listings/:id`.

### `POST /listings/:id/offerup/handoff`

Builds the payload the extension fills into OfferUp's form and records the
disclaimer acceptance.

```json
{ "mode": "post", "disclaimerAccepted": true, "suppress7d": false,
  "categoryPath": ["Home & Garden", "Furniture"], "condition": "USED" }
```

Response: the `OfferUpHandoff` (`v: 1`, `nonce`, `portageUserId`,
`listingId`, `mode`, `title` ≤ 99 chars (Posting-Rules strip applied to the
title too), stripped `description`, whole-dollar `price`, `condition`,
`categoryPath`, 5-digit `zip` (a ZIP+4 profile value is cut to 5), up to 12
R2-hosted `photos`, `skippedPhotos`, `expiresAt` 30 min; in `mode: "edit"`
also `changed[]` and `posted { title, price }` — the row key the extension
matches on `/selling`). Side effects (one atomic JSONB merge):
`marketplaceSpecificFields` gains `categoryPath`, `condition`, `zip`,
`consentVersion`, `lastHandoffAt`, and — **post mode only** — `postedTitle`,
`postedPrice` (what OfferUp will show; an edit handoff never rewrites them,
the next `/selling` snapshot does). `items.marketplaceData.offerup` caches a
real category pick; a fallback pick (LLM error) is used once and not cached.
The disclaimer acceptance row is written for post mode only, in the same
transaction.

| Status | Code | Meaning |
|---|---|---|
| 400 | `WRONG_MARKETPLACE` | Not an OfferUp listing |
| 404 | `NOT_FOUND` | Unknown listing, or an id that is not a UUID |
| 409 | `OFFERUP_ALREADY_POSTED` | `mode: post` on a row that already has an item id |
| 409 | `OFFERUP_INVALID_STATE` | `mode: post` on a row that is not a draft |
| 409 | `OFFERUP_VERSION_UNKNOWN` | `extensionVersion` not allowlisted |
| 409 | `OFFERUP_NOT_POSTED` | `mode: edit` on a row that is not active / has no id |
| 409 | `OFFERUP_NOT_CONNECTED` | No OfferUp account row with consent |
| 422 | `OFFERUP_ZIP_REQUIRED` | Seller profile has no ship-from ZIP |
| 422 | `OFFERUP_PHOTOS_INVALID` | No Portage-hosted photo on the item |
| 422 | `OFFERUP_CATEGORY_INVALID` | `categoryPath` is not a path in the committed tree |

### `POST /listings/:id/offerup/posted`

Id-only report-back after the human posted. The server never fetches an
OfferUp URL; the body carries digits only.

```json
{ "offerupItemId": "1234567890", "via": "dom" }
```

`via` ∈ `dom` (seen on the page), `selling` (read from *My items* / a Share
short link the extension followed), `manual` (pasted). Draft → `active`,
`marketplaceListingId` set, `publishedAt` stamped, a `publish` sync-log row
with `source: extension`. Same id again → 200 no-op. The UPDATE is guarded
(`status = 'draft' AND marketplace_listing_id IS NULL`): two concurrent
reports with different ids cannot both attach. Every refusal below writes a
`publish` sync-log row with `status: failure` and
`errors: { source, via, reportedId, code }` — a second OfferUp id for a
linked row is a live duplicate the seller must see.

| Status | Code | Meaning |
|---|---|---|
| 400 | `WRONG_MARKETPLACE` | Not an OfferUp listing (an eBay/Reverb row never takes an OfferUp id) |
| 404 | `NOT_FOUND` | Unknown listing, or an id that is not a UUID |
| 409 | `OFFERUP_ALREADY_POSTED` | Row already carries a different id, or lost the attach race |
| 409 | `OFFERUP_INVALID_STATE` | Row is not a draft |
| 409 | `OFFERUP_ID_IN_USE` | Another listing of this user already has that id (checked, and again on the unique index) |
| 409 | `OFFERUP_NOT_CONNECTED` | No OfferUp account row (disconnected) |
| 409 | `OFFERUP_VERSION_UNKNOWN` | `extensionVersion` not allowlisted |

### `PATCH /listings/:id { "status": … }` — OfferUp state machine

`sold` is accepted for OfferUp rows only (`400 VALIDATION_ERROR` otherwise):
listing `status` + `soldAt` (kept if already set), never `items.status`;
sync-log `listing_edit` with `{ source: "portage", action: "mark_sold" }`.
For OfferUp rows every status change is checked against the reconcile state
machine (spec §4.5, D15/D16) and refused with `409 OFFERUP_INVALID_STATE`
otherwise:

| from | allowed `status` |
|---|---|
| `draft` | `archived` |
| `active` | `archived`, `sold` |
| `archived` (posted, has an id) | `active`, `sold` |
| `archived` (never posted) | `draft` |
| `sold` | — (terminal) |

`active` is never granted by PATCH — only `/posted` does, with the id.

### Lifecycle without an adapter

Archive, delete and bulk archive/delete skip the adapter for OfferUp rows and
answer with `warning: "OFFERUP_STILL_LIVE"` (bulk: `offerupStillLive: [ids]`).
A price edit on a live OfferUp row saves locally with
`warning: "Saved in Portage — update the price on OfferUp from the listing card"`.
An item edit with a live OfferUp listing adds the `syncWarnings` string
`"OfferUp: update this listing on OfferUp from the listing card"` instead of an
outbox job.

## Snapshots

### `POST /marketplace/offerup/snapshot`

The extension sends the *My items* tab the seller is viewing. Rate limit 6 /
min per user; identical row sets within 10 min answer `{ "deduped": true }`
(the hash is remembered only after a successful apply, so a 5xx retry is
processed). Requires a connected account (`409 OFFERUP_NOT_CONNECTED`); every
row's `status` must equal `tab` (400 otherwise).

```json
{ "capturedAt": "2026-10-04T04:00:00.000Z", "tab": "sold",
  "rows": [{ "title": "Fender Bar Stools", "price": 25, "status": "sold", "offerupItemId": "1234567890" }] }
```

Response `{ matched, changed: [{ listingId, from, to }], ambiguous: [{ key, listingIds }], unmatched }`.
Matching: item id first, then normalised title + rounded price — but a row
that carries an id nobody owns may key-match only listings with **no** id
(a different OfferUp item must never mark a linked listing sold); more than
one candidate either way → ambiguous, nothing written. Transitions: active →
sold | archived; archived → active | sold; sold and draft never change. All
writes run in one transaction through the atomic JSONB merge: **every**
matched row gets `marketplaceSpecificFields.lastSnapshotAt` plus
`postedTitle`/`postedPrice` as OfferUp shows them; a planned change also
writes `status` (guarded on the planned `from` — a manual Mark sold that
landed meanwhile wins) and, for sold, `soldAt`. One `status_sweep` sync-log
row per snapshot that changed anything, and a `status_sweep` **failure** row
whenever `ambiguous` is non-empty.

## Admin

`GET /admin/marketplace/health` includes an `offerup` bucket
`{ total, healthy, expiring, expired }` (always healthy — no token to expire).
OfferUp account rows are returned with `tokenExpiresAt: null` here, in
`/admin/users/:id.marketplaceConnections` and in
`/users/me/marketplace-accounts` (which also exposes `extensionVersion`) —
the stored 2099 placeholder is not a token.
