---
id: offerup-assisted-post
title: OfferUp Assisted Post
sidebar_position: 5
---

import ThemedImage from '@theme/ThemedImage';

# OfferUp Assisted Post

OfferUp is the third Portage marketplace and the first without an API. The
design (spec `docs/superpowers/specs/2026-10-03-offerup-assisted-post-design.md`,
v2.1) keeps every rule the other adapters enforce — one listing row per
marketplace, server-side truth, marketplace writes are never silent — while
moving the only possible write path into the seller's own browser.

## Components

<ThemedImage
  alt="OfferUp Assisted Post components: Portage web page ↔ Portage Assistant extension (content scripts, background, storage) ↔ offerup.com form; the page is the only API caller"
  sources={{light: '/portage/img/offerup-components.svg', dark: '/portage/img/offerup-components-dark.svg'}}
/>

*The Portage page is the only API caller. The extension stores no Portage
credential: it receives a prepared handoff from the page over a MessagePort,
fills OfferUp's own form, and queues reports the page later collects and
posts to the API. The caveat D1 states plainly: the bridge content script
runs on the Portage origin, so like any extension granted that origin it
could read the page's `localStorage` token or fetch same-origin — the
control is release integrity (the committed build, the release gate test,
the store listing), not a technical wall.*

- **API (`apps/api`)** — no `OfferUpAdapter`. The adapter registry
  (`src/marketplace/registry.ts`) owns `PUBLISHABLE_MARKETPLACES = ['ebay','reverb']`;
  `getAdapter(_, 'offerup')` throws `400 OFFERUP_HANDOFF`, and every sync,
  sweep and order loop filters on `isPublishable`. OfferUp-specific routes:
  `POST /listings/:id/offerup/handoff` (builds the payload the extension
  fills), `POST /listings/:id/offerup/posted` (id-only report-back, digits
  only — the server never fetches an OfferUp URL),
  `POST /marketplace/offerup/snapshot` (passive `/selling` reconcile),
  `POST|GET|DELETE /marketplace/offerup/{connect,status,disconnect}`,
  `GET /marketplace/offerup/taxonomy`. All behind `requireOfferUpAccess`
  (tier `beta-tester` or role `admin`).
- **Extension (`apps/extension`)** — Manifest V3, one source, built for Chrome
  and Safari. `permissions: ["storage"]`, host permission for `offerup.com`
  only, no MAIN-world scripts, no network observation. Pure modules
  (`handoff-schema`, `fill-engine`, `storage`, `selling-reader`,
  `background-core`) are unit-tested under jsdom; thin content scripts and a
  background bind them to the browser.
- **Web (`apps/web`)** — `lib/offerup-bridge.ts` is the page side of the
  protocol; `useOfferUpBridge` delivers extension reports to the API and acks
  them; `OfferUpConnectCard` (Settings), `OfferUpFieldsSection` (create
  sheet) and `OfferUpActions` (listing card) are the visible surface.

## Handoff sequence

<ThemedImage
  alt="Handoff sequence: Portage page → POST handoff → bridge → background stores by nonce → offerup.com tab → content script peeks, self-checks, fills, shows Ready → human presses Post item → id report-back"
  sources={{light: '/portage/img/offerup-handoff-sequence.svg', dark: '/portage/img/offerup-handoff-sequence-dark.svg'}}
/>

1. The page posts `discover` on `window`; the content script answers `hello`
   with a fresh `MessagePort` (repeatable, so client-side navigation and
   late-installed extensions both work).
2. The card calls `POST /listings/:id/offerup/handoff` (consent recorded,
   category picked by the model against the committed taxonomy, photos
   limited to the R2 public host, description stripped of links/emails/
   phone numbers per OfferUp's Posting Rules, title cut to 99 characters —
   the limit OfferUp's form enforces).
3. `sendHandoff` → the extension validates it again (host pinning, nonce
   shape, user match) → the background stores it under its nonce and opens
   or reuses an offerup.com tab with `#portage-handoff=<nonce>`.
4. The offerup.com content script **peeks** the handoff, runs a self-check of
   every anchor **before writing a field**, opens the modal, fills, walks the
   category picker, sets the ZIP, adds photos one at a time, reads the form
   back, and shows *Ready*. Only then is the handoff **consumed** — a Retry
   before that point re-reads it.
5. The human presses Post item. The id comes back by one of three tiers
   (page, `/selling` row or Share short link followed by opening a tab,
   pasted link) and lands via `POST /listings/:id/offerup/posted`.

## Photo path

<ThemedImage
  alt="Photo path: R2 public bucket → fetched by the offerup.com content script with credentials omitted, redirects refused, image/* only, ≤10 MB → OfferUp's file input; the server never touches photo bytes"
  sources={{light: '/portage/img/offerup-photo-path.svg', dark: '/portage/img/offerup-photo-path-dark.svg'}}
/>

*Photo bytes go R2 → browser → OfferUp. The handoff carries URLs on the R2
public host only; the extension refuses anything else before fetching.*

## Listing states

<ThemedImage
  alt="OfferUp listing states: draft → (handoff) → draft with lastHandoffAt → (posted report) → active ↔ archived via /selling snapshots; sold is terminal; manual sold in Portage"
  sources={{light: '/portage/img/offerup-listing-states.svg', dark: '/portage/img/offerup-listing-states-dark.svg'}}
/>

Status comes only from `/selling` snapshots the extension sends while the
seller views that page: rows are matched by normalised posted title + whole-
dollar price (or item id); ambiguous matches are refused and reported; sold is
terminal; archived ↔ active may flip; drafts never move. A seller may also
*Mark sold in Portage* (`PATCH /listings/:id { status: 'sold' }`, OfferUp
rows only — listing status and `soldAt`, never `items.status`). Archiving or
deleting in Portage never ends the OfferUp post (`OFFERUP_STILL_LIVE`).

## Data

`listings.marketplaceSpecificFields` for `marketplace = 'offerup'` holds
`{ categoryPath, condition, zip, postedTitle, postedPrice, offerupItemId,
postedVia, lastHandoffAt, lastSnapshotAt, consentVersion }`;
`items.marketplaceData.offerup` caches the model's category pick;
`marketplace_accounts` rows for OfferUp carry placeholder tokens, the
extension version in `marketplaceUserId`, and `consentAcceptedAt` /
`consentVersion`. A partial unique index keeps one OfferUp item id per user.

## Decisions (short)

| # | Decision | Over |
|---|---|---|
| D1 | Page is the only API caller; extension stores no credential (release integrity is the control) | Extension with its own token |
| D2 | Photos fetched by the offerup.com content script from R2 | Server proxying photo bytes |
| D6 | Category tree captured once and committed | Live crawl of the picker |
| D7 | Extension never presses Post / Save / Mark sold / Archive | Fully automated posting |
| D8 | Passive `/selling` snapshots when the seller views the page | Background polling / alarms |
| D13 | No MAIN-world code, open shadow root panel | Patching `fetch`/XHR to read OfferUp's API |
| D14 | Short links resolved by opening a tab in the user's browser | Server-side `fetch` of offerup.co |
| D16 | Manual *Mark sold in Portage* for OfferUp rows only | Treating sold as marketplace-reported everywhere |
| Q2 | Beta-tester / admin gate in this release | Open to every tier |

See the [API reference](/portage/api/offerup) and the
[runbook](/portage/operations/offerup-runbook).
