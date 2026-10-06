---
id: offerup-runbook
title: OfferUp Assistant Runbook
sidebar_position: 10
---

# OfferUp Assistant Runbook

Operating notes for **Portage Assistant**, the browser extension that fills
OfferUp's *Post an item* form from a Portage listing (spec
`docs/superpowers/specs/2026-10-03-offerup-assisted-post-design.md`). OfferUp
has no API; nothing on the server ever talks to offerup.com. Status flows back
only from the user's own browser.

:::caution OfferUp Terms of Service
OfferUp's ToS §7 and Posting Rules prohibit third-party posting tools. The
feature is **beta-tester / admin only** (`403 OFFERUP_BETA_ONLY`), shows the
§8.1 consent before the first handoff, and never presses Post item, Save,
Mark sold or Archive. Operator decision 2026-10-03 (spec §12 Q1/Q2).
:::

## Builds

| Command | Output | Use |
|---|---|---|
| `npm run build:dev -w apps/extension` | `apps/extension/dist/{chrome,safari}` with sourcemaps, dev Portage origins, Learn toolbar | local development, Phase 0 captures |
| `npm run build -w apps/extension` | minified, no dev origins, no Learn code | release; the gate test proves the surface |
| CI `Extension` workflow | `portage-assistant-{chrome,safari}.zip` + sha256 | what gets uploaded to a store |

Every released version must be appended to `OFFERUP_EXTENSION_VERSIONS`
(`packages/shared/src/offerup.ts`) **before** users install it, or
`POST /marketplace/offerup/connect` answers `409 OFFERUP_VERSION_UNKNOWN`.

## Chrome

1. Dev: `chrome://extensions` → Developer mode → *Load unpacked* →
   `apps/extension/dist/chrome`.
2. Release: upload the CI `portage-assistant-chrome.zip` to the Chrome Web
   Store developer dashboard (item id and publisher name recorded in
   `apps/extension/README.md` once P0-9 is done). Visibility **Unlisted**.
   Privacy practices to declare: location (ZIP code), user-generated content
   (listing title/description/photos), personally identifiable information
   (OfferUp item ids tied to the Portage user). Single purpose statement:
   "Fills OfferUp's listing form with a listing the user prepared in Portage
   and reports the resulting item id back to Portage."

## Safari (macOS, unsigned — this version)

Apple Developer Program membership does not exist yet (operator, 2026-10-03,
"skipping apple for now"; registry deferred item `16c39f43`). Until it does,
Safari runs the **unsigned local** build only; there is no App Store or
TestFlight channel and no iOS build.

On the Mac:

```bash
# from the repo root, after npm run build -w apps/extension
xcrun safari-web-extension-packager apps/extension/dist/safari \
  --project-location /tmp/portage-assistant-safari \
  --app-name "Portage Assistant" \
  --bundle-identifier com.digitalharmony.portage.assistant \
  --copy-resources --no-open --no-prompt
```

The generated Xcode project is a local convenience and is **not committed**
(spec D10). Then:

1. Open `/tmp/portage-assistant-safari/Portage Assistant.xcodeproj` in Xcode,
   select the macOS target, **Run** once (this registers the extension with
   Safari).
2. Safari → Settings → Developer → *Allow unsigned extensions* (re-enable after
   every Safari restart).
3. Safari → Settings → Extensions → Portage Assistant → enable; set
   **Always Allow** for `offerup.com` and the Portage origin.
4. Verify in the popup: both sites show "Allowed on …".

Safari differences to expect:

- The manifest declares both `background.service_worker` (Chrome) and
  `background.scripts` (Safari). Safari uses the latter.
- `storage.local` promises are read through `browser.storage.local` when
  present (`apps/extension/src/storage.ts`).
- **P0-8 (R2 CORS):** if Safari's content-script `fetch` to the R2 public host
  is refused (no page origin sent), Plan 2 Task 12 Step 4's photo relay
  through the background is the fix. Record the observation in
  `docs/research/2026-10-03-offerup-phase0-results.md` under `## P0-8`
  before building the relay.

### Safari iOS (deferred)

Blocked on an Apple Developer Program membership: App Store Connect, the
Safari Web Extension Packager upload, internal TestFlight (90-day builds) and
every iOS measurement (P0-1 modal presence, P0-2 extension behaviour). When
the membership exists, resume at Plan 2 Task 12 Steps 2–3. Note Apple
guideline 5.2.2: no App Store or external TestFlight distribution without
OfferUp's written consent (spec §12 Q5).

## Releasing a new extension version

1. Bump `apps/extension/package.json` `version` **and** `src/manifest.base.json`.
2. Append the version to `OFFERUP_EXTENSION_VERSIONS` in
   `packages/shared/src/offerup.ts` (the API refuses unknown versions at
   connect) and rebuild `packages/shared`.
3. `npm run test -w apps/extension` (release gate) → merge → the `Extension`
   workflow produces the zips and checksums.
4. Chrome Web Store: upload the chrome zip to the existing item; keep
   visibility Unlisted. Safari: regenerate the Xcode project with the
   packager command above (macOS unsigned) — TestFlight re-uploads (builds
   expire after 90 days) wait on the Apple membership.

## R2 CORS (P0-8 — set 2026-10-04)

Photos are fetched by the offerup.com content script from the public bucket
with `mode: 'cors'`. The bucket has two rules: `portage-web-get` (Portage
origins) and `offerup-ext-get` (`https://offerup.com`, `https://www.offerup.com`;
`GET`/`HEAD`). Re-verify from any shell:

```bash
curl -sI -H 'Origin: https://offerup.com' \
  https://portage-images.digitalharmonyai.com/<any-existing-key> | grep -i access-control-allow-origin
```

No header → re-apply with the scope-C `CF_OPS_TOKEN`
(`PUT /client/v4/accounts/<CF_ACCOUNT_ID>/r2/buckets/portage-images/cors`,
keep both rules). Until it is set, every photo fails with a CORS `TypeError`
and the panel's checklist shows `Photos (0 of n)`.

## Drift triage from a diagnostics file

A seller's "OfferUp changed its form" report comes with the popup's
*Download diagnostics* JSON: `version`, `formMapVersion`, `userAgent`,
`lastSelfCheck.missing` (anchor names — never page content). Map the missing
names to `apps/extension/src/form-map.json`:

| missing | anchor | first thing to check |
|---|---|---|
| `header.postButton` | header Post ▾ | logged out, or OfferUp renamed the button |
| `title` / `description` / `price` / `file` | `fields.*` selectors | ids renamed |
| `condition.*` | `data-testid="PostItemForm.ConditionField.*"` | chip testids changed |
| `category.open` / `location.open` | `PostItemForm.CategoryField` / `LocationField` containers | field testids changed |
| `submit` | button text "Post item" | copy change |

Recapture with the dev build's Learn bar (**Capture fixture**), update the
map, keep `tests/fill-engine.test.ts` green against the new fixture, release.

## Phase 0 captures (Learn toolbar, dev build only)

On offerup.com with the dev build, a dark **LEARN (dev)** bar appears bottom-
left. Each button downloads a file; nothing is posted:

| Button | Produces | Feeds |
|---|---|---|
| Capture fixture | `fixture-<path>.html` (scripts/styles/images/long text stripped) | `apps/extension/tests/fixtures/` (replaces the hand-built ones) |
| Capture taxonomy | `offerup-taxonomy.json` (`capturedAt`, `roots`) | `apps/api/src/marketplace/offerup-taxonomy.json` (P0-6) |
| Probe limits | `limits.json` (title/description/price typed vs kept, maxlength, helper text) | `OFFERUP_TITLE_MAX` (P0-3) |
| Probe photo input | `photo-input.json` (`mode: append | replace`) | `form-map.json` `photos.mode` (P0-3) |
| Capture after post | `after-post.json` (url, item links, dialog titles) | P0-4 (where the new id shows) |

Each capture ends with a dated `## P0-n` entry in
`docs/research/2026-10-03-offerup-phase0-results.md`.

## When OfferUp changes its form

The extension runs a **self-check before touching any field**. A missing
anchor shows "OfferUp changed its form — update Portage Assistant, or fill
this listing by hand" and records the missing anchor names (popup → Download
diagnostics → `lastSelfCheck.missing`). Fix: re-capture the fixture, update
`apps/extension/src/form-map.json`, keep `tests/fill-engine.test.ts` green,
bump the version, append it to `OFFERUP_EXTENSION_VERSIONS`, release.

## Consent, revocation and what the extension keeps

- Consent (spec §8.1) gates **every** path that reads offerup.com for Portage
  or sends anything back — handoffs, "find my listing", short-link follows
  and the `/selling` snapshots — not only the first handoff.
- Revocation: Portage **Disconnect** (Settings → Marketplaces) deletes the
  account row *and* tells the extension to forget consent, the remembered
  user and queued reports; the popup's **Withdraw consent** does the
  browser half alone. After a disconnect the API answers
  `409 OFFERUP_NOT_CONNECTED` to handoffs, reports and snapshots.
- The remembered user (`lastUserId`) expires 24 h after the last handoff /
  "find my listing"; `/selling` snapshots collapse to the newest per tab and
  expire after 24 h; posted ids are never swept.
- Short links are followed only for `offerup.co` / `offerup.app.link`
  (path required, query dropped) in a tab the background opened; only that
  tab may resolve the lookup or be closed. A Share dialog that shows a full
  `offerup.com/item/detail/<id>` link reports the id directly.
- Photos: `jpeg`/`png`/`webp` only — OfferUp's own input declares exactly
  that `accept` list (P0-3, 2026-10-04); the input **appends**.

## Reconciliation and manual sold

- Status comes from `/selling` snapshots the extension sends while the user
  views that page (`POST /marketplace/offerup/snapshot`): matched by
  normalised posted title + whole-dollar price, ambiguous matches are refused
  and reported, sold is terminal, archived ↔ active may flip.
- No snapshot for a sold item? The seller presses **Mark sold in Portage** on
  the listing card (`PATCH /listings/:id { status: 'sold' }`, OfferUp rows
  only; drafts cannot be sold, sold is terminal — `409 OFFERUP_INVALID_STATE`).
  Archiving or deleting in Portage never ends the OfferUp post — the card,
  the delete confirm and the bulk bar all say "still live on OfferUp".
- Two listings with the same title and whole-dollar price cannot be told
  apart on `/selling`: the snapshot leaves both untouched, logs a
  `status_sweep` failure row, and the item page shows a notice — give them
  distinct titles, or mark sold by hand.
- Sync log rows: `trigger: publish` with `errors.source: extension` for
  report-backs, `status_sweep` for snapshots, `listing_edit` with
  `action: mark_sold` for manual sold.
