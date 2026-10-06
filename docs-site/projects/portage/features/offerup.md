---
id: offerup
title: OfferUp (Assisted Post)
sidebar_position: 2
---

# OfferUp — Assisted Post

*Beta · 2026-10 · beta testers and admins only*

OfferUp has no public API. Portage posts there the only way its Terms allow
a person to: **you** press Post item on offerup.com. What Portage adds is the
**Portage Assistant** browser extension, which fills OfferUp's *Post an item*
form from your Portage listing — title, description, price, condition,
category, location and up to 12 photos — in your own logged-in browser, then
stops and waits for you.

## What it does — and does not do

| Portage Assistant does | Portage Assistant never does |
|---|---|
| Fills OfferUp's form from a listing you prepared in Portage | Presses **Post item**, **Save**, **Mark sold** or **Archive** on OfferUp |
| Reads the *My items* page **while you are looking at it** and sends titles, prices, statuses and item ids to your Portage account | Poll OfferUp in the background, open tabs on a timer, or read pages you did not open |
| Fetches your listing photos from Portage's own image host into the form | Hold any Portage password or token (the Portage page talks to the API; the extension only talks to the page) |
| Helps find the new item's id after you post (page, Share link, or paste) | Fetch any offerup.com URL from Portage's servers |

:::caution OfferUp's Terms of Service
OfferUp's Terms (§7) and Posting Rules prohibit third-party posting tools.
Using Portage Assistant may lead OfferUp to suspend your account, listings and
conversations. You accept this in the extension and on the Portage Connect
card before the first handoff. Portage is not affiliated with OfferUp.
:::

## Install

**Chrome (and Chromium browsers):** install Portage Assistant from the Chrome
Web Store (unlisted link on *Settings → Marketplace → OfferUp*), then open
Portage and reload the tab. The extension needs no permission beyond site
access to `offerup.com`.

**Safari (macOS):** this release ships an unsigned local build — see the
[runbook](/portage/operations/offerup-runbook). After installing: Safari →
Settings → Extensions → Portage Assistant → **Always Allow** on offerup.com
*and* on the Portage site, then reload the Portage tab. Safari cannot tell
Portage whether the extension is missing or merely not allowed, so the card
shows both instructions.

**iPhone / iPad:** not in this release. If you opened Portage as a Home Screen
app the card says *Open Portage in Safari to use OfferUp*; Home Screen apps run
no browser extensions at all.

## Connect

*Settings → Marketplace → OfferUp.* With the extension reaching the page, the
card shows the consent text; tick *I understand* and press **Connect OfferUp**.
Connecting records the consent version and the extension version against your
account and counts as one marketplace connection on the free plan. Disconnect
any time; your listings stay.

## Post

1. On an item, **List on another marketplace → OfferUp**. The sheet shows the
   OfferUp condition (defaults from the item), the category Portage will pick
   (or **Change category** to choose from OfferUp's own tree), your ship-from
   ZIP from the seller profile, the description as OfferUp will receive it
   (links, emails and phone numbers removed, your seller footer added), and
   the photo count (first 12 Portage-hosted photos). **Save Draft**.
2. On the listing card, **Post on OfferUp**. The first time you accept the
   terms sheet; then Portage builds the handoff and the extension opens
   offerup.com, fills the form and shows its panel: *Ready — review and press
   OfferUp's Post item button*, with a checklist of what it filled and what
   you still need to do by hand (category or location when OfferUp's picker
   refused, photos it could not fetch).
3. **You press Post item** on OfferUp.

If the panel says *OfferUp changed its form — update Portage Assistant, or
fill this listing by hand*, nothing was touched; Portage will ship a fixed
extension.

## Confirm the link (which OfferUp item is this?)

OfferUp does not tell Portage what it just created, so after you post Portage
needs the item id once. Three ways, strongest first:

1. **Automatic** — if OfferUp shows the new item's link right after posting,
   the extension reports it and the card flips to *View on OfferUp*.
2. **Find my listing** — press *I pressed Post — find my listing* on the
   panel; the extension opens *My items*, highlights your row and reads the
   id from it (or from the row's Share link, which it resolves by opening a
   tab — never by fetching from Portage).
3. **Paste** — on the card, *Confirm OfferUp link*: paste the item link
   (`offerup.com/item/detail/…`) or the short link from Share.

## Status

Portage learns OfferUp status only from *My items*: every time you view that
page with the extension installed, the tab you are looking at is sent to
Portage as a snapshot and matched to your listings by title + price (or item
id). Sold is final; archived can come back to active; drafts never change
from a snapshot. *Refresh OfferUp status* on the card simply opens that page.

- **Update on OfferUp** — Portage builds an edit handoff; the extension opens
  *My items*, presses OfferUp's **Edit** on your row, fills only what changed,
  and stops at **Save** for you.
- **Mark sold on OfferUp / Archive on OfferUp** — open *My items* with the row
  highlighted; you press OfferUp's button.
- **Mark sold in Portage** — when the OfferUp side is already done (or you
  sold in person): records the sale in Portage only.
- Archiving or deleting an OfferUp listing in Portage never ends the OfferUp
  post — the card tells you it is still live there.
- A sold OfferUp listing whose item is still active on eBay or Reverb shows
  *End on eBay?* pointing at that card; ending it is your click.

## Troubleshooting

| You see | Do |
|---|---|
| The card offers *Get it on the Chrome Web Store* although it is installed | Reload the Portage tab (tabs opened before install have no bridge). |
| Safari: nothing happens | Extension popover → **Always Allow** on this site and offerup.com → reload. |
| Panel: *Log in to OfferUp, then press Retry* | Log in on offerup.com in that tab, press **Retry**. |
| Panel: *OfferUp changed its form* | Nothing was filled. Post by hand this time; update the extension when prompted. |
| *Accept the consent in the extension popup first* | Open the extension's toolbar popup and accept. |
| *Update Portage Assistant — this version isn't recognised yet* | Update from the store (or reload the unpacked build). |
| Status never changes | Open *My items* on offerup.com in the browser with the extension and look at the right tab (Active / Sold / Archived). |
| No extension at all | The card's manual kit copies title, description and price and downloads the photos; post by hand, then paste the link. |

## Privacy

What leaves your browser: the listing you hand off (to offerup.com, by your
action), your OfferUp *My items* rows (titles, prices, statuses, item ids — to
your Portage account only), and the extension version + consent version at
connect. What never leaves: your OfferUp session, OfferUp pages you did not
hand off from, and anything from sites other than offerup.com and Portage.
The extension's diagnostics file contains versions and the last form self-check
result, never page content.
