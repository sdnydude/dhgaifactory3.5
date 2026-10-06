---
id: marketplace-landscape-v2
title: Marketplace Landscape v2 — routes around the blockers
sidebar_position: 2
sidebar_label: Marketplace Landscape v2
---


**Research run:** 2026-10-04 (ET), version 2. **Scope:** North America and Asia-Pacific, with Japan and South Korea in depth. **Status:** research only; nothing built. Version 1 (catalogue, per-marketplace tables, scores): `docs/research/2026-10-04-marketplace-landscape-na-apac.md`. Proposed registry schema: `docs/research/marketplace-registry-schema.md`.

## The answer

Every large used-goods marketplace in both regions is blocked by some combination of three things:
- no seller API;
- terms that ban bots, third-party apps or add-ons;
- for Japan and Korea, residency and identity rules.

Competitors mostly ignore the second blocker. Vendoo, Flyp, Crosslist, List Perfectly and Sell The Flip all fill the marketplace's web form from a browser extension inside the user's own session. I found no lawsuit or cease-and-desist against any of them; enforcement has been behavioural instead: rate limits, and Poshmark's 60-day relist rule.

The divergent pass produced 21 distinct routes. They converge on five moves:

1. **Use routes the marketplaces already sanction before building anything new.**
   - Meta integrates eBay inventory into Facebook Marketplace: "Earlier this year, we began integrating eBay inventory into Marketplace followed by Poshmark… when you're ready to buy, you'll be taken to the partner's site for checkout" ([Meta, 2025-11-13](https://about.fb.com/news/2025/11/facebook-marketplace-gets-a-glow-up/)). Portage already publishes to eBay, so its listings may already reach Facebook buyers with no extension and no ToS exposure (R1). Confirm it on one live listing.
   - Etsy's Seller App is approved "within minutes, with no manual review queue" for your own shop (R10).
   - The Nextdoor Share Plugin needs no approval (R7).
2. **Make the person the one who posts, in the marketplace's own app.** A share-sheet handoff (R4) and a copy kit (R5) work on every marketplace in every region, including Japan and Korea, where tools are banned outright. They trade convenience for zero automation.
3. **Keep the extension, but risk-tier it.** OfferUp has two rules against it: its ToS ("without OfferUp's prior written consent") and its Posting Rules, updated 2026-10-03 ("Don't use emulators or third-party sites to post on OfferUp"). The extension should run only where a marketplace's terms do not name tools, or where consent exists, and should have a remote kill switch per marketplace (R20). Ask OfferUp for written consent (R6).
4. **Own the buyer endpoint as a long-term moat.** Give each item a Portage storefront page, distributed through Google free listings, Facebook's Marketplace Partnership Program and agentic-commerce feeds (R2, R7, R8, R9). Buyers then come to Portage regardless of which marketplace blocks tools next.
5. **Reach Asia from the buyer side first.** A US seller cannot list on Mercari JP, Yahoo!オークション or Rakuma: all three require residence in Japan. Sell into Japan and Korea through internationally ready eBay listings now (R15). Build a resident Portage (R16) only if that demand shows up. Karrot's terms (version 2026-01-02) also ban automated posting and profit or promotional use, so even a resident product would be copy kit and share-sheet only there.

The roadmap at the end turns these moves into a sequence. The first column costs days, not weeks.

## What changed since version 1

- **Competitors do fill OfferUp's form.** Version 1 said no competitor did; that was wrong. Sell The Flip "posts through your own logged-in OfferUp session via the browser extension" ([source](https://selltheflip.com/marketplaces/offerup)). Underpriced AI's extension targets `offerup.com/post*`, and its site also describes a paste-in-the-app flow. Neither claims OfferUp's consent, and I found no OfferUp enforcement against either.
- **OfferUp tightened its Posting Rules** on 2026-10-03 at 23:21 UTC, the night PR #386 merged ([help article JSON](https://help.offerup.com/api/v2/help_center/en-us/articles/360031988292.json)).
- **Facebook Marketplace has a sanctioned partner route** (eBay, Poshmark) and a Partnership Program for eligible partners ([Meta developers](https://developers.facebook.com/docs/marketplace/partnerships)).
- **Ownership changes.** Reverb is no longer Etsy's: Reverb Partners LLC, an affiliate of Servco Pacific, closed the purchase on 2025-06-02 (Etsy 8-K). Depop belongs to eBay since 2026-07-30.
- **Karrot** has no web posting found, and its ToS bans automated posting and commercial use.
- **Scale data.** Version 1 had seller counts for 4 marketplaces. Version 2 has a user, seller or GMV figure for 49 of the 63 marketplaces in the scale table, plus App Store rating counts for the main apps in 13 country stores.

## Scale — the gaps closed

How to read the table:
- **Definitions differ.** Every figure keeps its own definition, period and source, so read across a row, not down a column.
- **iOS rating counts** come from Apple's public iTunes Search API on 2026-10-04. They compare apps within one country store, never across countries. They track how hard an app asks for ratings as much as how big it is: in Korea, Bunjang has 161K ratings against Karrot's 40K, although Karrot has four times Bunjang's monthly users. Korea and India are mostly Android, so iOS counts understate both.
- **Sellers stay unpublished** for Facebook Marketplace, OfferUp, Mercari (US and JP), Poshmark, Craigslist, Karrot and Bunjang. The agents checked filings, IR datasheets, press and DART for each.

### North America

| Marketplace | Users / buyers / traffic | Sellers | GMV | iOS ratings (store) |
|---|---|---|---|---|
| Facebook Marketplace | [430 million items listed per month (listings, 2026 (announced 2026-07-24))](https://about.fb.com/news/2026/07/introducing-seller-app-facebook-marketplace/) | not published | not published | Seller app 10,772 (Facebook app n/a) (US) |
| OfferUp | [40M+ 'active users' (undefined); 20%+ of adults in top markets monthly; 30M+ annual transactions million (MAU,…](https://about.offerup.com/) | not published | not published | 4,445,342 (US) |
| eBay | [135 million (active_buyers, end of 2025)](https://www.sec.gov/Archives/edgar/data/1065088/000106508826000027/ebay-20251231.htm) | not published | not published | 4,969,223 (US) |
| Etsy | [86.5 million (active_buyers, as of 2025-12-31)](https://www.sec.gov/Archives/edgar/data/1370637/000137063726000019/etsy-20251231.htm) | [5.6 million (active_sellers, as of 2025-12-31)](https://www.sec.gov/Archives/edgar/data/1370637/000137063726000019/etsy-20251231.htm) | not published | 7,311,790 (US) |
| Mercari US | [4.20 million (MAU, FY2026.6 Q4 (Apr-Jun 2026))](https://pj.mercari.com/impact-report/FY2026_6_ImpactReport_EN.pdf) | not published | [US$810 (+11.2% YoY; JPY125.3B) USD million (GMV, FY2026.6 (ended 2026-06-30))](https://pdf.irpocket.com/C4385/xoA3/ieAo/YOsY/N4E3.pdf) | 1,953,769 (US) |
| Poshmark | [8.2 million (active_buyers, TTM ended 2022-09-30 (last SEC-reported before Naver acquisition; STALE))](https://www.sec.gov/Archives/edgar/data/1825480/000095017022024463/posh-20220930.htm) | not published | [475.6 (quarter) USD million (GMV, Q3 2022 (STALE))](https://www.sec.gov/Archives/edgar/data/1825480/000095017022024463/posh-20220930.htm) | 1,085,330 (US) |
| Depop | [55.6 million (registered_users, as of 2025-12-31)](https://www.sec.gov/Archives/edgar/data/1370637/000137063726000019/etsy-20251231.htm) | [3.2 million (active_sellers, as of 2025-12-31)](https://www.sec.gov/Archives/edgar/data/1370637/000137063726000019/etsy-20251231.htm) | not published | 1,029,356 (US) |
| Whatnot | [20 million new accounts (registered_users, created in CY2025)](https://sports.yahoo.com/articles/whatnot-doubled-sales-more-8-183000855.html) | not published | [8 USD billion (GMV, CY2025 (doubled vs 2024))](https://sports.yahoo.com/articles/whatnot-doubled-sales-more-8-183000855.html) | 1,047,261 (US) |
| Vinted (US) | not published | not published | [10.8 EUR billion (GMV, CY2025 (+47% YoY; 2024 EUR 7.3bn))](https://company.vinted.com/newsroom/financial-results-2025) | 395,930 (US) |
| Nextdoor | [21.0 (Platform WAU, all Nextdoor features; For Sale & Free not broken out) million weekly active users (WAU (n…](https://www.sec.gov/Archives/edgar/data/1846069/000184606926000023/kind-20251231.htm) | not published | not published | 2,155,495 (US) |
| Craigslist | [560 million visits/month (monthly_visits, 2023)](https://en.wikipedia.org/wiki/Craigslist) | not published | not published | 558,125 (US) |
| Kijiji | not published | not published | not published | 696,356 (CA) |
| Mercado Libre | [121 (whole company, all countries; Mexico split NOT in 10-K) million (active_buyers, FY2025)](https://www.sec.gov/Archives/edgar/data/1099590/000109959026000006/meli-20251231.htm) | not published | [65,037 (group, all countries) USD million (GMV, FY2025)](https://www.sec.gov/Archives/edgar/data/1099590/000109959026000006/meli-20251231.htm) | 3,370,302 (MX) |
| Reverb | [785 thousand (active_buyers, as of 2024-12-31 (last Etsy-reported))](https://www.sec.gov/Archives/edgar/data/1370637/000137063725000017/etsy-20241231.htm) | [221 thousand (active_sellers, as of 2024-12-31 (last Etsy-reported))](https://www.sec.gov/Archives/edgar/data/1370637/000137063725000017/etsy-20241231.htm) | not published | 201,356 (US) |
| Karrot US/CA | [40M+ MAU, global (no US/CA split) (MAU, page read 2026-10-04)](https://about.daangn.com/) | not published | not published | 5,909 / 23,935 (US / CA) |
| 5miles | not published | not published | not published | 189,602 (US) |
| VarageSale | not published | not published | not published | 70,874 / 112,738 (US / CA) |
| Grailed | not published | not published | not published | 127,565 (US) |
| StockX | not published | not published | not published | 1,300,035 (US) |
| ThredUp | [1.7 million (active_buyers, FY2025)](https://www.sec.gov/Archives/edgar/data/1484778/000148477826000007/tdup-20251231.htm) | not published | not published | 305,205 (US) |
| The RealReal | [1,056 thousand (over 1 million) (active_buyers, FY2025)](https://www.sec.gov/Archives/edgar/data/1573221/000157322126000010/real-20251231.htm) | not published | not published | 87,462 (US) |
| Discogs | [3 million (registered_users, 2015)](https://en.wikipedia.org/wiki/Discogs) | not published | not published | 67,059 (US) |
| Chrono24 | not published | not published | not published | 69,243 (US) |
| Back Market | not published | not published | not published | 69,153 (US) |
| SidelineSwap | not published | not published | not published | 59,308 (US) |
| Chairish | not published | not published | not published | 39,692 (US) |
| TCGplayer | not published | not published | not published | 15,892 (US) |
| 1stDibs | [~60,700 buyers (active_buyers, FY2025)](https://www.sec.gov/Archives/edgar/data/1600641/000160064126000007/dibs-20251231.htm) | not published | not published | 9,917 (US) |
| Swappa | not published | not published | [92 (seller proceeds 2018); 300 cumulative since 2010 USD million (GMV, 2018)](https://en.wikipedia.org/wiki/Swappa) | 2,294 (US) |
| Delcampe | [85 million items for sale (listings, page read 2026-10-04)](https://www.delcampe.net/en_US/) | not published | not published | — |

### Japan

| Marketplace | Users / buyers / traffic | Sellers | GMV | iOS ratings (store) |
|---|---|---|---|---|
| Mercari | [24.19 million (MAU, Q4 FY2026.6 (Apr-Jun 2026))](https://pdf.irpocket.com/C4385/xoA3/ieAo/YOsY/Kz3T.csv) | not published | [1,285,675 JPY million (GMV, FY2026.6 (Jul 2025-Jun 2026))](https://pdf.irpocket.com/C4385/xoA3/ieAo/YOsY/Kz3T.csv) | 5,554,909 (JP) |
| Yahoo!オークション + Yahoo!フリマ | not published | not published | [1,098.9 (FY2025); 296.4 (FY2026 Q1, +18.4% YoY) JPY billion (GMV, FY2025 (Apr 2025-Mar 2026); FY2026 Q1)](https://www.lycorp.co.jp/ja/ir/library/indicator/main/05/teaserItems1/03/linkList/00/link/jp2026q1_datasheet.xlsx) | 1,886,676 / 1,334,724 (JP) |
| Rakuma | not published | not published | not published | 539,864 (JP) |
| Jimoty | [approx. 10 million (company-stated, undefined 'users per month') users/month (MAU, 2026 (live site, Oct 2026))](https://jmty.co.jp/) | not published | not published | 488,716 (JP) |
| Amazon.co.jp | [68 million+ average monthly users (Nielsen, 2025 avg; all Amazon.co.jp customers, not sellers) users/month (MA…](https://sell.amazon.co.jp/) | not published | not published | 717,172 (JP) |
| Rakuten Ichiba | not published | [55,408 merchants (Q2/26); 55,001 (Q2/25) merchants (出店店舗数) (active_sellers, Q2 2026 (Jun 2026))](https://corp.rakuten.co.jp/investors/assets/doc/documents/26Q2Datasheet.xlsx) | [1,532.2 (Q2/26 domestic EC GMS, +5.3% YoY; group domestic EC incl. Travel, Books, Fashion etc., NOT Ichiba alo…](https://corp.rakuten.co.jp/investors/assets/doc/documents/26Q2Datasheet.xlsx) | 5,162,416 (JP) |
| SNKRDUNK | [6 million+ (monthly users, company boilerplate) users/month (MAU, as of May 2026)](https://prtimes.jp/main/html/rd/p/000000017.000078952.html) | not published | not published | 35,629 (JP) |
| Suruga-ya | [approx. 30 million SKUs (Suruga-ya catalogue SKU data in Mercari alliance; not marketplace-only) (listings, Se…](https://netshop.impress.co.jp/n/2026/09/25/16772) | not published | not published | 198 (JP) |
| Japan C2C market (METI) | not published | not published | [2,526.9 (JPY billion; 2兆5,269億円, +1.82% YoY) CtoC-EC market size estimate (GMV, calendar 2024)](https://www.meti.go.jp/press/2025/08/20250826005/20250826005.html) | — |

### South Korea

| Marketplace | Users / buyers / traffic | Sellers | GMV | iOS ratings (store) |
|---|---|---|---|---|
| Karrot (당근) | [23.19 million (Android+iOS app MAU, monthly average) users/month (MAU, Q1 2026)](https://www.edaily.co.kr/News/Read?newsId=03729366645421040) | not published | not published | 40,165 (KR) |
| Bunjang | [5.2 million (Android+iOS app MAU, monthly average) users/month (MAU, Q1 2026)](https://www.edaily.co.kr/News/Read?newsId=03729366645421040) | not published | [KRW 91.5 billion escrow (안전결제) GMV in March 2026 (+10% YoY; monthly record). Escrow-only, not total GMV KRW bi…](https://www.etnews.com/20260421000091) | 161,075 (KR) |
| Joonggonara | [2.09 million (Android+iOS app MAU, monthly average) users/month (MAU, Q1 2026)](https://www.edaily.co.kr/News/Read?newsId=03729366645421040) | not published | not published | 13,676 (KR) |
| Coupang | [24.7 million Product Commerce Active Customers (Q2 2026, +3% YoY); 24.6M Q4 2025; 23.9M Q2 2025 customers (qua…](https://www.sec.gov/Archives/edgar/data/1834584/000183458426000073/cpng-20260630.htm) | not published | not published | 31,142 (KR) |
| Gmarket / Auction | not published | [660,000 sellers (+5% YoY) as of 1 July 2026; 17,000 sellers on global (SE Asia) program sellers (Gmarket platf…](https://biz.chosun.com/distribution/channel/2026/07/09/4626NMRTDZGMXNVVLTEF7T6WJ4/) | not published | 64,338 (KR) |
| KREAM | [2.2 million (Android+iOS app MAU, monthly average) users/month (MAU, Q1 2026)](https://www.edaily.co.kr/News/Read?newsId=03729366645421040) | not published | not published | 311,594 (KR) |
| FruitsFamily | [1.8 million users/month (MAU, Sep 2025)](https://zdnet.co.kr/view/?no=20250925171807) | not published | [KRW 200bn cumulative GMV as of Jul 2025; monthly GMV KRW 10bn (GMV, Jul 2025)](https://zdnet.co.kr/view/?no=20250925171807) | 53,941 (KR) |
| Musinsa Used | not published | not published | not published | 52,619 (Musinsa app) (KR) |
| Naver Smart Store | not published | not published | not published | — |
| Korea used-goods market (KISA) | not published | not published | [KRW 43 trillion estimated (2025) KRW trillion (GMV, 2025)](https://daily.hankooki.com/news/articleView.html?idxno=1360243) | — |

### Asia-Pacific (other)

| Marketplace | Users / buyers / traffic | Sellers | GMV | iOS ratings (store) |
|---|---|---|---|---|
| Shopee | [~400 million active buyers (active_buyers, 2025)](https://www.sec.gov/Archives/edgar/data/1703399/000119312526088151/d106475dex991.htm) | [~20 million sellers (active_sellers, 2025)](https://www.sec.gov/Archives/edgar/data/1703399/000119312526088151/d106475dex991.htm) | [US$127.4 billion (GMV, FY2025)](https://www.sec.gov/Archives/edgar/data/1703399/000119312526088151/d106475dex991.htm) | 1,365,202 / 981,399 / 1,780,388 (TH / MY / VN) |
| Lazada | [~160,000,000 active users (active_buyers, 2024-07)](https://press.carousell.com/2024/07/30/carousell-and-lazada-launches-first-of-its-kind-seamless-online-iphone-trade-in-feature-in-singapore/) | [1,000,000+ actively-selling sellers per month (active_sellers, 2024-07)](https://press.carousell.com/2024/07/30/carousell-and-lazada-launches-first-of-its-kind-seamless-online-iphone-trade-in-feature-in-singapore/) | not published | 2,537,744 / 586,435 (TH / ID) |
| Tokopedia + TikTok Shop ID | [~100,000,000 (Tokopedia); TikTok ID users ~125M monthly active users (MAU, 2024-04)](https://www.kompas.id/artikel/tuntas-integrasi-jumlah-gabungan-mitra-penjual-di-tokopedia-dan-tiktok-shop-tembus-lebih-dari-21-juta) | [21,000,000+ (registered seller partners, combined Tokopedia + TikTok Shop ID) registered seller partners (NOT …](https://www.kompas.id/artikel/tuntas-integrasi-jumlah-gabungan-mitra-penjual-di-tokopedia-dan-tiktok-shop-tembus-lebih-dari-21-juta) | not published | 652,141 (ID) |
| Meesho | [264.29 million annual transacting users (active_buyers, FY26)](https://files.tijorifinance.com/insight/india/59535/Annual%20Report/AR-26.pdf) | [961000 sellers (active_sellers, FY26 (year ended 2026-03-31))](https://files.tijorifinance.com/insight/india/59535/Annual%20Report/AR-26.pdf) | not published | — |
| Flipkart | not published | [~1,400,000 sellers (active_sellers, 2026-10)](https://www.business-standard.com/companies/people/ecommerce-platform-flipkart-doubles-active-seller-base-in-15-months-126100400410_1.html) | not published | 7,149,365 (IN) |
| Amazon India | not published | [2,000,000 (20 lakh) sellers (active_sellers, 2026-09)](https://www.aboutamazon.in/news/small-business/5-reasons-to-start-selling-on-amazon-in-this-festive-season) | not published | 755,892 (IN) |
| OLX India | [35,000,000+ monthly active users (MAU, 2024-06)](https://retail.economictimes.indiatimes.com/news/e-commerce/e-tailing/post-acquisition-olx-focused-on-growing-core-biz-md/110864492) | not published | not published | 1,538,598 (IN) |
| Carousell (group) | [80,000,000 new listings per year (listings, 2023)](https://press.carousell.com/2023/09/22/launch-of-carousell-campus-leading-the-future-of-secondhand-with-recommerce-cultivating-talent-and-contributing-back-to-the-startup-ecosystem/) | not published | [not disclosed; FY25 revenue US$141M (+18% YoY, EBITDA-positive); recommerce 45% of revenue revenue (SGD/USD as…](https://press.carousell.com/2026/07/07/carousell-group-reaches-ebitda-profitability-milestone-as-recommerce-scales-sets-ai-priorities-for-fy26/) | 281,600 / 190,315 (SG / MY) |
| Chợ Tốt | [10,000,000+ monthly users (MAU, 2022-11)](https://press.carousell.com/2022/11/30/cho-tot-cung-tap-doan-me-carousell-cong-bo-tac-dong-cua-viec-mua-ban-do-cu-doi-voi-phat-trien-ben-vung-trong-10-nam-qua/) | not published | not published | 44,260 (VN) |
| Gumtree AU | [over 8 million (Gumtree Group: Gumtree + CarsGuide + Autotrader) monthly reach, consumers (MAU, 2026-03 snapsh…](https://web.archive.org/web/20260314013732/https://www.gumtreegroup.com.au/) | not published | not published | — |
| Ruten | [11,000,000+ monthly visitors (瀏覽人數) (monthly_visits, 2024-08)](https://www.bnext.com.tw/article/79964/cyberbiz-ruten) | not published | [revenue NT$681M (2023); operating profit NT$80M; ~30% of transactions are hobby/collectible items revenue (NOT…](https://today.line.me/tw/v3/article/qoJJp6W) | — |
| Yahoo拍賣 (TW) | not published | not published | not published | 25,440 (TW) |
| Trade Me | [5,000,000 'active members' (April 2021); 690,000 visits/day members / daily visits (registered_users, 2021-04)](https://en.wikipedia.org/wiki/Trade_Me) | not published | not published | 65,355 (NZ) |
| Kaidee | [4,000,000+ monthly users (Kaidee Auto vertical) (MAU, ~2024-10 (Wayback snapshot 20241009))](https://web.archive.org/web/20241009100849/https://www.kaidee.com/about-us) | not published | not published | — |



What the numbers settle:

- **Facebook Marketplace is the largest used-goods surface in North America:** 430 million items listed per month (Meta, 2026-07). That makes the eBay bridge (R1) the highest-value item on the list.
- **Mercari US is smaller than its brand suggests:** 4.20M MAU in Q4 FY2026.6, down from about 4.9M two years earlier (Mercari IR datasheet). Its GMV is US$810M a year.
- **Japan is concentrated and large.**
  - Mercari has 24.19M MAU and ¥1,285.7bn GMV.
  - Yahoo!オークション plus Yahoo!フリマ, and BEENOS, the third business in the same reported line, had ¥1,098.9bn of "Reuse" GMV in FY2025.
  - Japan's whole C2C e-commerce market was ¥2.53tn in 2024 (METI).
  - All three big C2C platforms are closed to non-residents.
- **Korea's C2C audience is Karrot's:** 23.19M app MAU against Bunjang's 5.2M and Joonggonara's 2.09M (WISEAPP Q1 2026, via edaily). Posting is app-only, and the terms forbid automation.
- **India's scale is in business channels:** Meesho has 961K active sellers, Amazon India 2.0M sellers, Flipkart about 1.4M. All are business-registration channels.

## Blockers, with how competitors handle each

| # | Blocker | Where | Why it blocks Portage | How competitors handle it | Routes |
|---|---|---|---|---|---|
| B1 | No public seller API | Facebook Marketplace, OfferUp, Mercari US, Poshmark, Craigslist, Kijiji, Vinted, Grailed, Karrot, Bunjang, Carousell, Gumtree | Portage cannot publish, update or end a listing server-side | Extension inside the user's session (Vendoo 70k, Flyp 40k, Crosslist 20k Chrome users); cloud replay of a captured session (Nifty, PrimeLister); copy-paste (Underpriced AI) | R1 eBay→Facebook bridge · R2 Partnership Program · R4 share-sheet · R5 copy kit · R7 storefront link · R8 Google free listings · R9 agentic feed |
| B2 | ToS bans bots, third-party apps or add-ons | OfferUp (ToS + Posting Rules 2026-10-03), Nextdoor (browser plugins), Vinted (external software tools), Craigslist, Poshmark, Gumtree AU, Carousell, Shopee, Trade Me, Karrot, Bunjang, all Japanese C2C | Account suspension for the user; legal exposure if the marketplace sends notice and blocks | Disclaim endorsement and proceed; no lawsuit or cease-and-desist against a crosslister found. Enforcement is behavioural (Poshmark 60-day relist rule, rate limits). Rakuma (2021) acted against tool vendors | R6 written consent · R20 risk tiers + kill switch · R4 / R5 (the user acts in the official client) |
| B3 | Partner-only, gated or closed APIs | Depop, Whatnot, TCGplayer, Mercari Shops, Nextdoor, Facebook (allow-list), Etsy commercial, Trade Me (in-trade only) | An official channel exists, but Portage is not in it | Nifty on the Depop API; Vendoo, Nifty, PrimeLister on Etsy; BigSeller on Shopee / Lazada / TikTok Shop | R10 Etsy Seller App · R11 Nextdoor API · R12 Depop via eBay · R13 Whatnot via Shopify · R2 |
| B4 | Residency and identity | Mercari JP, Yahoo!オークション, Rakuma (residents only); Korean C2C (본인인증 via Korean carrier) | A US seller cannot open the account at all | Japanese tools serve residents only; no crosslister serves Korean C2C | R15 sell into Asia via eBay · R16 resident Portage · R17 Japan entity |
| B5 | App-only posting | Joonggonara (since 2025-09-22), Karrot (no web posting found), SNKRDUNK, Vestiaire | No web form for an extension to fill | None found | R4 share-sheet · R5 copy kit |
| B6 | Business-only channels | Amazon (Professional plan), Coupang, Naver, Rakuten, Flipkart, Shopee / Lazada in some markets | Personal-effects sellers are individuals | B2B multichannel tools (Next Engine, Sabangnet, PlayAuto, BigSeller) | R18 seller-owned keys · R19 Portage Pro for small dealers |
| B7 | Missing scale data | Seller counts almost everywhere; Facebook Marketplace users; OfferUp sellers | Prioritisation rests on uneven numbers | No crosslister publishes per-marketplace sell-through | R21 measured sell-through · App Store rating counts as a consistent in-country proxy · paid app-intelligence data |
| B8 | Consignment and buy-out verticals | The RealReal, ThredUp, MPB, KEH, TPC, Kaiyo, 1stDibs, Fanatics Collect | Nothing to list: the vertical takes the item | Not integrated by crosslisters | R14 best-exit engine |
| B9 | Bot checks on web forms | Mercari US sell page (interstitial) | Extension fill can be interrupted | Extensions run in the user's real browser at human pace | R5 copy kit fallback · R20 |


## Divergent pass — every route considered

Each route was scored 1–5 on five criteria:
- **Reach:** how many buyers it reaches.
- **Safety:** ToS and legal safety; 5 means the marketplace sanctions it.
- **Cost:** 5 means already built or trivial.
- **Speed:** time to the first live listing.
- **Moat:** how hard it is for a competitor to copy.

The total is out of 25. Routes marked **new** are not used by any competitor I found.

| # | Route | Blockers | Reach | Safety | Cost | Speed | Moat | Total | New? | How it works · precedent |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 | eBay → Facebook bridge | B1, B2 | 5 | 5 | 5 | 5 | 2 | **22** | new | Keep publishing to eBay through the API Portage already runs. Meta integrates eBay inventory into the US Marketplace feed; buyers click through to eBay to check out. · Meta newsroom 2025-11-13: 'we began integrating eBay inventory into Marketplace followed by Poshmark'. ([source](https://about.fb.com/news/2025/11/facebook-marketplace-gets-a-glow-up/)) |
| R6 | Written consent from OfferUp | B2 | 4 | 5 | 4 | 2 | 5 | **20** | new | The ToS clause itself names the remedy: 'without OfferUp's prior written consent'. Pitch Portage as a quality-supply partner (AI-verified condition, real photos, fewer disputes). · None found: OfferUp has no partner program. ([source](https://offerup.com/terms)) |
| R21 | Measured sell-through as the scale metric | B7 | 3 | 5 | 4 | 3 | 5 | **20** | new | Portage records time-to-sale and price per marketplace from its own users; that is the number that matters, and it becomes a product feature ('where this item sells fastest'). · None among crosslisters found publishing per-marketplace sell-through. |
| R5 | Copy kit | B1, B2, B4, B5, B9 | 3 | 5 | 5 | 5 | 1 | **19** | competitor | Per-marketplace formatted fields with one-tap copy and a saved photo set; the user pastes. · Underpriced AI: 'open the app to paste and post it yourself' for Poshmark, Mercari, Facebook, Depop, Vinted, OfferUp. ([source](https://underpricedai.com/features/crosslisting)) |
| R8 | Google free listings for the storefront | B1 | 4 | 5 | 3 | 3 | 4 | **19** | new | Feed storefront items into Google Merchant Center free listings (condition attribute supports used). · Google: free listings appear 'on Google Search, Google Maps, Gemini, YouTube, the Shopping tab'. ([source](https://support.google.com/merchants/answer/9199328)) |
| R2 | Facebook Marketplace Partnership Program | B1, B3 | 5 | 5 | 2 | 1 | 5 | **18** | new | Portage becomes a Marketplace partner: Portage-hosted listings distributed into Marketplace, checkout on Portage (Stripe). · Meta developer page: 'enable eligible third-party partners to distribute listings on Facebook Marketplace'; eBay and Poshmark are the known partners. ([source](https://developers.facebook.com/docs/marketplace/partnerships)) |
| R4 | Share-sheet handoff into the official app | B1, B2, B5 | 4 | 4 | 4 | 4 | 2 | **18** | new | Portage (PWA Web Share API with files, later a native share extension) hands photos to the marketplace app and puts the listing text on the clipboard; the user finishes in the official app. · Android documents ACTION_SEND for apps receiving shared images; whether each marketplace app registers it is unverified (Low). No crosslister ships this route. ([source](https://developer.android.com/training/sharing/receive)) |
| R10 | Etsy Seller App now; Commercial Access next | B3 | 3 | 5 | 4 | 4 | 2 | **18** | competitor | Restore the parked adapter (tag etsy-parked-2026-07) for the operator's shop with a Seller App; apply for Commercial Access in parallel. · Etsy: 'approved within minutes, with no manual review queue'; Vendoo, Nifty, PrimeLister run on the Etsy API. ([source](https://developers.etsy.com/documentation/)) |
| R11 | Nextdoor Publishing API | B3 | 4 | 5 | 3 | 2 | 4 | **18** | new | Apply to the closed beta: create, edit, delete and mark-sold For Sale & Free posts. · Nextdoor developer docs; 21.0M platform weekly active users (Q4 2025 10-K). ([source](https://developer.nextdoor.com/reference/applying-for-access.md)) |
| R14 | Best-exit engine | B8 | 3 | 5 | 3 | 3 | 4 | **18** | new | For each item Portage compares net proceeds: list yourself vs consign vs instant buy-out, and routes the user with referral links. · Consignment verticals publish take rates (The RealReal 37.7% take rate, $594 AOV). ([source](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=realreal&type=10-K)) |
| R15 | Sell into Japan and Korea from the US via eBay | B4 | 3 | 5 | 4 | 4 | 2 | **18** | new | Make Portage eBay listings international-ready (shipping, translated titles) so Japanese and Korean buyers on eBay find them; no residency needed. · Mercari Global App runs the opposite direction (Japan sellers to US buyers, US launch 2026-06-17), showing cross-border demand. ([source](https://about.mercari.com/en/press/news/articles/20260618globalapp/)) |
| R7 | Portage storefront + share link | B1, B3 | 3 | 4 | 3 | 3 | 4 | **17** | new | Each item gets a public Portage page with Stripe checkout; the user shares the link, or Portage uses the Nextdoor Share Plugin. · Nextdoor: 'The Nextdoor Share Plugin is an open offering and you are free to integrate it without Nextdoor approval.' ([source](https://developer.nextdoor.com/reference/sharing-availability.md)) |
| R20 | Risk tiers + remote kill switch | B2 | 3 | 4 | 4 | 4 | 2 | **17** | new | Per-marketplace tier from its ToS wording; extension only in tiers without a named tool ban unless consent exists; a remote form-map flag turns a marketplace off within minutes. · Portage form-map.json already versioned and hot-fixable (spec D9). |
| R9 | Agentic-commerce feed | B1 | 2 | 5 | 2 | 2 | 5 | **16** | new | Expose storefront inventory through the Agentic Commerce Protocol (OpenAI + Stripe) so AI shopping agents can buy. · ACP spec 'maintained by OpenAI and Stripe and is currently in beta'. ([source](https://github.com/agentic-commerce-protocol/agentic-commerce-protocol)) |
| R13 | Whatnot through Shopify | B3 | 3 | 5 | 3 | 3 | 2 | **16** | new | Whatnot's Seller API is closed, but its Shopify plug-in imports products; Portage pushes to a user's Shopify store. · Shopify App Store: Whatnot app. ([source](https://apps.shopify.com/whatnot)) |
| R19 | Craigslist dealer bulk interface for Portage Pro | B2, B6 | 3 | 5 | 3 | 2 | 3 | **16** | new | Small used-goods businesses (estate sales, thrift) post in 'for sale by dealer' through a licensed bulk feed. · Craigslist bulk posting interface: case-by-case for high-volume posters; by-dealer posts are paid. ([source](https://www.craigslist.org/about/bulk_posting_interface)) |
| R3 | Assisted-post extension (current) | B1 | 4 | 2 | 4 | 4 | 1 | **15** | competitor | Extension fills the logged-in web form; the user presses Post. No stored credentials. · Industry standard: Vendoo 70,000, Flyp 40,000, Crosslist 20,000 Chrome users; Sell The Flip posts to OfferUp this way. No lawsuit or cease-and-desist against a crosslister found. ([source](https://selltheflip.com/marketplaces/offerup)) |
| R12 | Depop through the eBay relationship | B3 | 3 | 5 | 3 | 1 | 3 | **15** | new | Depop is eBay-owned since 2026-07-30 and its private Selling API is meant for 'cross-listing tools'; ask via eBay developer relations as an existing eBay API integrator. · Nifty 'uses the Depop API'. ([source](https://partnerapi.depop.com/api-docs/)) |
| R16 | Portage for Japan and Korea residents | B4, B2 | 5 | 4 | 1 | 1 | 4 | **15** | new | Localised Portage for resident sellers; posting only via share-sheet or copy kit, because Japanese and Korean C2C rules ban tools (Rakuma has acted against tool vendors). · Rakuma 2021: tool users restricted immediately, action taken against tool vendors. ([source](https://fril.jp/magazine/2021-01-21-150008/)) |
| R17 | Japan entity + 古物商許可 consignment | B4, B6 | 4 | 4 | 1 | 1 | 5 | **15** | new | Portage KK holds a secondhand-dealer permit, receives US items, and lists them through business channels with APIs. · Kobutsu Business Act art. 3: permit from the prefectural public safety commission. ([source](https://elaws.e-gov.go.jp/api/1/lawdata/324AC0000000108)) |
| R18 | Seller-owned API keys | B3, B6 | 2 | 3 | 3 | 4 | 2 | **14** | new | Where only own-shop apps are open, each user registers their own app and Portage orchestrates with the user's key. · Flipkart self-access apps are 'strictly for self seller use'; Etsy Seller App is own-shop only. ([source](https://seller.flipkart.com/api-docs/FMSAPI.html)) |


**Routes considered and rejected:**
- **Cloud bots that replay a captured marketplace session** (the Nifty and PrimeLister model). They move Portage from "the user's browser acts" to "Portage's servers act as the user". That is the fact pattern of Facebook v. Power Ventures and Craigslist v. 3Taps.
- **Android accessibility-service automation.** It is automation, which every Japanese and Korean C2C ruleset bans.
- **A concierge that lists for the user.** OfferUp's Posting Rules require "You must be the owner of your item".
- **Buying a small tool for its access.** None of the tools found holds sanctioned access to a blocked marketplace beyond Depop (Nifty).

![scatter diagram](/portage/img/marketplace-landscape/scatter.svg)

*Ease against reach. Orange dots are routes the marketplace sanctions (safety 5). The top-right corner is R1 (the eBay→Facebook bridge) and R5 (the copy kit).*

## Convergence — the route ladder

For each marketplace, Portage should use the highest rung available and drop a rung only when the one above is closed.

![ladder diagram](/portage/img/marketplace-landscape/ladder.svg)

### Facebook Marketplace — four routes compared

![facebook diagram](/portage/img/marketplace-landscape/facebook.svg)

*The eBay route needs nothing new and sits inside Meta's sanctioned partner program. The extension route is what competitors do, and it is the one Facebook's terms forbid.*

### Route per marketplace

| Marketplace | Region | Blocker | Now | Next | Avoid | What competitors do |
|---|---|---|---|---|---|---|
| Facebook Marketplace | NA | No listing API; allow-list Partnership Program | R1 eBay → Facebook partner listings (already publishing to eBay) | R4 share-sheet into the Facebook / Seller app; R2 Partnership Program BD | Extension on facebook.com (ToS: automated access without permission) | Vendoo, List Perfectly, Crosslist, Underpriced AI: extension in the user's desktop session |
| OfferUp | NA | No API; ToS bars third-party applications without written consent; Posting Rules bar third-party sites (2026-10-03) | Keep the extension beta-only, disclose both clauses in consent; R5 copy kit as the default | R6 written consent; R4 share-sheet into the OfferUp app | Any background or scheduled action | Sell The Flip and Underpriced AI post via extension in the user's session; no OfferUp enforcement found |
| Mercari US | NA | Partner-only access; bot-check interstitial on the sell page | R5 copy kit | R4 share-sheet; extension only after a logged-in form test | Cloud bot replaying sessions (Nifty model) | Vendoo, Crosslist, List Perfectly extension; Nifty cloud session |
| Poshmark | NA | No API; ToS bans automated systems; 60-day relist rule | R5 copy kit | R3 extension, create-only (no sharing or relisting automation) | Share / relist automation (Poshmark suspends for it) | Every crosslister by extension; PrimeLister / Nifty cloud bots for sharing |
| Etsy | NA | Commercial access gated | R10 Seller App for the operator's shop (approved within minutes) | Commercial Access application for all users | Scraping (Etsy API terms) | Vendoo, Nifty, PrimeLister on the Etsy API |
| Nextdoor | NA | Closed-beta Publishing API; Member Agreement bans browser plugins | R7 Share Plugin (open, no approval) | R11 Publishing API application | Extension (explicit add-on ban) | None found |
| Depop | NA | Private partner API | R5 copy kit | R12 partner API request through the eBay relationship | — | Nifty on the Depop API; others by extension |
| Whatnot | NA | Seller API closed to new applicants | — | R13 via Shopify plug-in | — | Vendoo beta (mechanism unstated); Nifty session hand-off |
| Craigslist | NA | ToS bars interoperating software without a written licence | R5 copy kit | R19 dealer bulk feed for Portage Pro | Extension (ToS: only the app, browsers and email clients) | Small extensions only (Ahlam, 9 users) |
| Kijiji | NA | No API; ToS bans automated access | R5 copy kit | R3 extension after a logged-in form test | — | K+ Reposter (783 users) |
| Discogs · HipStamp · Delcampe · Reverb · Mercado Libre MX | NA | None material (open or gated APIs) | Adapters in order of Portage inventory fit | — | Discogs: using the API to circumvent the marketplace | List Perfectly (Reverb beta) |
| Mercari JP · Yahoo!オークション · Rakuma | Japan | Residents only; tool bans (Rakuma acted against tool vendors) | R15 sell into Japan via eBay (US sellers) | R16 resident Portage with share-sheet / copy kit only | Any automation (explicit bans) | Torima, Fuma tools, eコンビニ automate despite the bans |
| Yahoo!フリマ · Jimoty | Japan | Tool ban (Yahoo!フリマ); residency unverified | R15 | R16 | Automation | Torima, Fuma tools |
| Mercari Shops · Amazon JP · Rakuten · BASE | Japan | Business / partner APIs | — | R17 Japan entity with 古物商許可 | — | Next Engine, CROSS MALL (B2B) |
| Karrot · Bunjang · Joonggonara | Korea | No APIs; posting app-only (Karrot, Joonggonara); Karrot ToS (2026-01-02) bans automated posting and profit or promotional use; 본인인증; Bunjang escalating bans | R15 sell into Korea via eBay | R16 resident Portage with share-sheet / copy kit | Automation (Bunjang escalating bans) | None found for Korean C2C |
| Coupang · Naver · 11st · Gmarket | Korea | Business registration; overseas sellers restricted (secondary) | — | Only with a Korean entity | — | Sabangnet, PlayAuto (B2B) |
| Carousell · Gumtree AU · Chợ Tốt · OLX | APAC | No APIs; ToS bans bots and automated means | R5 copy kit | R4 share-sheet; extension only with consent | Automation | None found |
| Trade Me | APAC | API closed to personal sellers since 2026-04-10 | R5 copy kit | API for in-trade Portage Pro sellers | Unauthorised automated means (site terms 3.3) | None found |
| Shopee · Lazada · Flipkart · Amazon India · Meesho | APAC | Business registration; individual API access restricted | — | Only for business sellers (R18 seller-owned keys where allowed) | Sharing self-access apps (Flipkart warns of bans) | BigSeller on official Open Platform APIs |


## How competitors actually do it

Mechanisms come from each tool's help center, the extension manifest in its current Chrome Web Store build, and its store listing.

| Tool | Marketplaces | Mechanism | Chrome users | Credentials | Conf. | Source |
|---|---|---|---|---|---|---|
| Vendoo | Poshmark | browser extension filling the web form in the user's session (hidden tab copy-paste) | 70,000 users | none stored | High | [source](https://help.vendoo.co/en/articles/6260307-is-the-vendoo-website-secure-is-vendoo-safe) |
| Vendoo | Poshmark (sharing/offers automation) | extension-run browser automation on a schedule (Marketplace Sharing, up to 6,000 shares/day, 1-4 s between act… | 70,000 users | none stored | Medium | [source](https://help.vendoo.co/en/articles/11003940-marketplace-sharing-tool-for-poshmark-depop-and-grailed) |
| Vendoo | Mercari | browser extension filling the web form in the user's session | 70,000 users | none stored | High | [source](https://help.vendoo.co/en/articles/6778905-i-can-t-connect-my-mercari-account) |
| Vendoo | Depop | browser extension in the user's session (desktop); mobile app uses a 'Magic Link' flow (not documented in deta… | 70,000 users | none stored | Medium | [source](https://help.vendoo.co/en/articles/6817458-i-can-t-connect-my-depop-account) |
| Vendoo | Facebook Marketplace | browser extension in the user's session (desktop Chrome only; personal Marketplace, not Facebook Shops; not in… | 70,000 users | none stored | High | [source](https://help.vendoo.co/en/articles/6817352-i-can-t-connect-my-facebook-store) |
| Vendoo | Grailed | browser extension in the user's session | 70,000 users | none stored | Medium | [source](https://help.vendoo.co/en/articles/6778989-i-can-t-connect-my-grailed-account) |
| Vendoo | eBay | official eBay API (OAuth access token stored; Business Policies required) | 70,000 users | stored token | High | [source](https://help.vendoo.co/en/articles/6260307-is-the-vendoo-website-secure-is-vendoo-safe) |
| Vendoo | Etsy | official Etsy Open API (OAuth access token stored) | 70,000 users | stored token | High | [source](https://help.vendoo.co/en/articles/6260307-is-the-vendoo-website-secure-is-vendoo-safe) |
| Vendoo | Whatnot (BETA) | not verified (help does not name mechanism); sale detection requires the computer on and connected to Vendoo, … | 70,000 users | not stated | Low | [source](https://help.vendoo.co/en/articles/9210620-how-do-i-use-whatnot-with-vendoo) |
| Crosslist | eBay | official API (API-first), Business Policies required for third-party apps on eBay's API | 20,000 users | not stated | Medium | [source](https://crosslist.com/) |
| Crosslist | Poshmark, Mercari, Depop, Grailed, Facebook Marketplace, Vinted, Whatn… | browser extension filling/driving the marketplace web UI in the user's browser when no API exists (per-marketp… | 20,000 users | not stated | Medium | [source](https://crosslist.com/) |
| Crosslist | Etsy / Shopify | official API (API-first) | 20,000 users | not stated | Low | [source](https://crosslist.com/) |
| Nifty | Poshmark | cloud automation with stored marketplace session (connected via extension session hand-off or username+passwor… | 20,000 users | none stored | High | [source](https://docs.nifty.ai/connections/connecting-poshmark) |
| Nifty | Mercari | cloud automation with stored session (extension session hand-off or username+password used once) | 20,000 users | none stored | High | [source](https://docs.nifty.ai/connections/connecting-mercari) |
| Nifty | Whatnot | extension session hand-off to Nifty cloud (extension is the only connection method) | 20,000 users | none stored | High | [source](https://docs.nifty.ai/connections/connecting-whatnot) |
| Nifty | Depop | official Depop API via OAuth (consent on Depop; connection lasts 12 months) | 20,000 users | stored token | High | [source](https://docs.nifty.ai/connections/connecting-depop) |
| Nifty | eBay | official eBay API via OAuth (about 18 months) | 20,000 users | stored token | High | [source](https://docs.nifty.ai/connections/connecting-ebay) |
| Nifty | Etsy | official Etsy API via OAuth (about 3 months) | 20,000 users | stored token | High | [source](https://docs.nifty.ai/connections/connecting-etsy) |
| List Perfectly | eBay, Poshmark, Mercari, Depop, Etsy, Facebook Marketplace, Grailed, V… | browser extension (Chrome/Edge) opens marketplace tabs and fills forms; user reviews and publishes; 2026 beta … | not verified | none stored | High | [source](https://help.listperfectly.com/en/articles/11106089-what-can-you-list-or-crosslist-with-list-perfectly) |
| List Perfectly | (all) | extension; Poshmark share/follow/offer automation in Pro / Pro Plus plans | not verified | none stored | Medium | [source](https://help.listperfectly.com/en/articles/12263571-do-you-charge-extra-for-poshmark-tools-are-they-unlimited) |
| List Perfectly | Reverb (beta) | not verified (Reverb has an open JSON API; LP help does not say whether API or extension) | not verified | not stated | Low | [source](https://help.listperfectly.com/en/articles/17318042-new-in-beta-reverb-and-background-update) |
| Flyp | Poshmark, Mercari, Depop, Vinted, eBay, Facebook | browser extension (Crosslister by Flyp) with cookies + scripting permissions; separate Poshmark Bot Sharer ext… | — | not stated | Medium | [source](https://www.joinflyp.com/poshmark-bot) |
| OneShop | Poshmark, Mercari, Depop, Tradesy | browser extension (cookies permission) plus site 'bots' for relisting, bumping, sharing; OneShop is also a mar… | 1,000 users | not stated | Medium | [source](https://www.oneshop.com/) |
| PrimeLister | Poshmark, Mercari, eBay, Etsy, Facebook, Depop, Grailed, Instagram | browser extension for cross-listing; Cloud Cross-Listing (beta) replays from servers using the logged-in sessi… | 9,000 users | none stored | High | [source](https://docs.primelister.com/features/cross-lister-tool/the-ultimate-guide-to-cloud-cross-listing.md) |
| PrimeLister | Poshmark (automation) | 100% cloud bot (no app, no extension): shares, follows, offers; $25/mo per closet | 9,000 users | none stored | High | [source](https://www.primelister.com/poshmark-bot) |
| PrimeLister | eBay (automation) / Etsy / Poshmark CA | eBay: official API (footer "uses the eBay API"), cloud automation; Etsy: official API (footer) | 9,000 users | stored token | Medium | [source](https://docs.primelister.com/faq/pricing) |
| SellerAider | Poshmark, Depop, Vinted, eBay, Etsy, Facebook, Grailed, Mercari, Whatn… | browser extension (Crosslister - SellerAider, 6,000 users) with cookies permission; optional tabs/scripting/we… | 4,000 users | not stated | Medium | [source](https://chromewebstore.google.com/detail/hoadkegncldcimofoogeljainpjpblpk) |
| Closo | Poshmark, Mercari, Depop, Vinted (all EU domains), eBay, Shopify | browser extension with cookies, webRequestExtraHeaders, scripting; websocket link to app.closo.co | 1,000 users | not stated | Medium | [source](https://chromewebstore.google.com/detail/aipjhdapgmimfdfcjmlpeoopbdldcfke) |
| Listelf (formerly Crosslist Ma… | Poshmark, Facebook Marketplace, Vinted, Shopify, Vestiaire, Depop, eBa… | browser extension with content scripts on create-listing pages (poshmark.com/create-listing, facebook.com/mark… | 4,000 users | not stated | Medium | [source](https://chromewebstore.google.com/detail/lkjldebnppchfbcgbeelhpjplklnjfbk) |
| Hammoq (Infinity AI) | eBay, ShopGoodwill | browser extension with side panel (533 users); content scripts on ebay.com / ebay.co.uk / sellerportal.shopgoo… | — | not stated | Low | [source](https://chromewebstore.google.com/detail/bemfglnkeaeomabmdoopjpbcbacpnfne) |
| 3Dsellers | eBay | official eBay API (self-described eBay Silver solution provider); Chrome extensions only for importing source … | 131 users | stored token | Medium | [source](https://www.3dsellers.com/) |
| 3Dsellers | Facebook / Instagram / TikTok | not verified (named as integrations; mechanism not stated) | 131 users | not stated | Low | [source](https://www.3dsellers.com/) |
| Underpriced AI | eBay, Bonanza | official API publish from the app | 172 users | stored token | High | [source](https://underpricedai.com/faq) |
| Underpriced AI | Facebook Marketplace, Poshmark, Mercari, Depop, Vinted, Whatnot, Offer… | browser extension fills the marketplace's own create-listing form; user picks category and clicks Post; phone … | 172 users | none stored | High | [source](https://underpricedai.com/features/crosslisting) |
| Sell The Flip | OfferUp | browser extension posts through the user's own logged-in OfferUp session; imports listings; pulls archived sol… | 187 users | none stored | High | [source](https://selltheflip.com/marketplaces/offerup) |
| Sell The Flip | eBay | official API via OAuth | 187 users | stored token | High | [source](https://selltheflip.com/privacy) |
| Sell The Flip | Poshmark, Mercari, Depop, Facebook Marketplace, Whatnot, Grailed, Vint… | browser extension (187 users); permissions include cookies, scripting, tabs; Poshmark Sharer automation and Li… | 187 users | not stated | Medium | [source](https://chromewebstore.google.com/detail/cnldmcpgoipcimgjjklpbnhikcnglmhm) |
| Ahlam Auto-Poster | OfferUp, Craigslist, Facebook Marketplace, eBay | browser extension content scripts on offerup.com/post/*, offerup.com/sell/*, craigslist.org, facebook.com/mark… | 9 users | not stated | Low | [source](https://chromewebstore.google.com/detail/fpiebljechdcjfjhfbmbnkjjmoinobkj) |
| K+ Reposter | Kijiji | browser extension (783 users) with cookies + alarms for scheduled reposting on kijiji.ca | 783 users | not stated | Low | [source](https://chromewebstore.google.com/detail/lmcjgogfikgdnjnecljihnoncllgebcg) |
| Kijiji to Marketplace | Kijiji - Facebook Marketplace | browser extension copies a Kijiji ad into facebook.com/marketplace/create/* | 9 users | not stated | Low | [source](https://chromewebstore.google.com/detail/ijmonbgcgokccaalihpeeidiblbncnan) |
| Nifty / (cross-listing OAuth t… | Depop | official Depop Selling API, OAuth 2.0 + PKCE for 'third-party applications (such as cross-listing tools)'; pri… | 20,000 users | stored token | High | [source](https://partnerapi.depop.com/api-docs/concepts/authentication/) |
| eコンビニ (e-Conveni) | Yahoo! Auctions (JP) | historically official Yahoo Auctions listing API (2013); Yahoo ended its Auctions Web API in Jan 2020, current… | — | not stated | Medium | [source](https://www.e-conveni.net/) |
| eコンビニ (e-Conveni) | Mercari, Rakuma, Yahoo!フリマ, Mercari Shops (JP) | web-based management screen (browser, OS-independent); posting mechanism for C2C sites not stated | — | not stated | Low | [source](https://torima.jp/articles/compare-furima-doujishuppin-tools/) |
| Torima (トリマ) | Mercari, Yahoo!フリマ, ヤフオク, Rakuma, Mercari Shops | native desktop app (Windows/Mac) automating the sites; inventory sync only works while the PC app is running a… | — | not stated | High | [source](https://torima.jp/) |
| Fuma King / Fuma Assist / Furi… | Mercari, Rakuma, Yahoo!フリマ, ヤフオク | Chrome extensions on a Windows/Mac PC (free, free, 980 yen + usage) | — | not stated | Medium | [source](https://torima.jp/articles/compare-furima-doujishuppin-tools/) |
| BigSeller | Shopee, Lazada, TikTok Shop (APAC) | official marketplace Open Platform APIs (ERP/OMS) | — | stored token | Medium | [source](https://www.bigseller.com/en_US/index.htm) |


### Enforcement record

| Marketplace | Date | Action | Conf. | Source |
|---|---|---|---|---|
| Poshmark | 2025-04-30 (reported 2025-05-02) | New policy: no repeated remove/relist of same items within 60 days and no mass listing removals 'manually or through automation'; 6-day suspension, permanent limits in severe cases | Medium | [source](https://www.modernretail.co/operations/i-followed-their-rules-and-was-hit-anyway-poshmark-sellers-voice-frustrations-with-new-excessive-listing-policy/) |
| Poshmark | 2025-11 to 2025-12 | Bulk-share option removed (2025-11-07) then restored after seller pushback (2025-12-09); mass listing deletions in error causing account suspensions (2025-11-16) | Low | [source](https://news.google.com/rss/search?q=Poshmark+bulk+share+removed) |
| Poshmark | 2025-10-20 | Native 'Smart Sell' feature reported to make paid resale tools obsolete; July 2025 Lifehacker: hidden native Bulk Actions reduce PrimeLister need | Low | [source](https://news.google.com/rss/search?q=Poshmark+Smart+Sell+Lifehacker) |
| Poshmark | ToS (Last Updated June 3rd 2025 banner; … | ToS prohibits scraping and automated systems | High | [source](https://poshmark.com/terms) |
| Poshmark / Facebook Marketplace (via too… | undated (help articles) | Temporary listing blocks when listing too fast/too many; tools tell users to slow down | Medium | [source](https://help.vendoo.co/en/articles/6812493-i-can-t-list-on-poshmark) |
| Poshmark | undated (PrimeLister troubleshooting ind… | Error states documented: 'Your Account Has Been Temporarily Suspended', 'Poshmark does not allow you to make more shares because you have made too many shares today', 'Previously Violated Our Terms of… | Low | [source](https://docs.primelister.com/troubleshooting) |
| Rakuma (JP) | 2021-01-21 | Declared auto-tools banned since launch; accounts using tools restricted immediately; warnings and shutdown actions against tool-vendor sites; stronger detection and cooperation with investigators | High | [source](https://fril.jp/magazine/2021-01-21-150008/) |
| Yahoo! Auctions (JP) | current guideline | Seller prohibition on auto-listing tools unless Yahoo specifically approves | High | [source](https://guide-ec.yahoo.co.jp/notice/rules/auc/detailed_regulations.html) |
| Yahoo! Flea Market (JP) | guideline revised 2026-08-27 (per prior … | Same prohibition on auto-listing tools | High | [source](https://paypayfleamarket.yahoo.co.jp/guide/guideline/detail/) |
| Yahoo! Auctions (JP) | 2019-10-10 notice (shutdown Jan 2020) | Official Auctions Web API discontinued | High | [source](https://developer.yahoo.co.jp/changelog/auctions.html) |
| Mercari (JP) | ToS rev. 2025-10-22 (prior run) | Prohibits accessing the service by a method other than Mercari's interface | High | [source](https://help.jp.mercari.com/guide/articles/900/) |
| OfferUp | current ToS | Prohibits third-party applications that interact with OfferUp without prior written consent, and automated means not provided by OfferUp | High | [source](https://offerup.com/terms) |
| Etsy | current API terms | Apps must not sidestep the API to retrieve or post Etsy data; screen-scraping not allowed | High | [source](https://developers.etsy.com/documentation/) |
| eBay | 2026-01-20 to 2026-01-22 | User Agreement bans robots/scrapers/automated means including buy-for-me agents, LLM-driven bots, and end-to-end flows placing orders without human review | High | [source](https://www.ebay.com/help/policies/member-behaviour-policies/user-agreement?id=4259) |
| Vinted | current ToS | Prohibits external software tools (bots, scraping, crawling) when using the Site/Services | High | [source](https://www.vinted.com/terms-and-conditions) |
| Craigslist | current ToS | Bans copying/collecting content via robots/scripts; posting only via App/browsers (prior run); bulk posting interface limited to high-volume paid categories | High | [source](https://www.craigslist.org/about/terms.of.use) |
| Whatnot | current docs | Seller API in Developer Preview and closed to new applicants | High | [source](https://developers.whatnot.com/docs/getting-started/introduction) |
| Shopee | 2024-11-18 (per GitHub issue) | Customer Service app category closed to individual third parties and third-party partner platforms | Low | [source](https://github.com/EcomPHP/shopee-php/issues/66) |
| Depop | 2026-07-30 | eBay completed acquisition of Depop from Etsy; partner API policy under new owner not yet stated | Medium | [source](https://news.google.com/rss/search?q=eBay+completes+acquisition+of+Depop) |
| Facebook (precedent) | 2008-2016 litigation | Facebook v. Power Ventures: CFAA, CAN-SPAM, DMCA claims against a third-party aggregator using user credentials | Medium | [source](https://en.wikipedia.org/wiki/Facebook,_Inc._v._Power_Ventures,_Inc.) |
| Craigslist (precedent) | 2013 | Craigslist v. 3Taps: cease-and-desist plus IP block is sufficient notice for CFAA claim | Medium | [source](https://en.wikipedia.org/wiki/Craigslist_Inc._v._3Taps_Inc.) |
| eBay (precedent) | 2000 | eBay v. Bidder's Edge: trespass to chattels injunction against crawler | Medium | [source](https://en.wikipedia.org/wiki/EBay_v._Bidder%27s_Edge) |
| (all) | searched 2026-10-04 | No marketplace lawsuit or cease-and-desist against Vendoo, List Perfectly, Crosslist, Flyp, Nifty, PrimeLister, OneShop, SellerAider, Closo, Sell The Flip, or Underpriced AI was found | Low | [source](https://news.google.com/rss/search) |


Nothing found suggests marketplaces sue crosslisters that act inside the user's own session. The lawsuits on record were against aggregators that used credentials or crawled at scale and kept going after notice:
- eBay v. Bidder's Edge (2000)
- Craigslist v. 3Taps (2013)
- Facebook v. Power Ventures (2008–2016)

That is absence of evidence, not a safe harbour. It is why the recommendation keeps Portage on the "user's browser, user presses Post, no stored credentials" side and adds consent requests.

## Japan and Korea — three ways in

![asia diagram](/portage/img/marketplace-landscape/asia.svg)

**Now: sell into Asia from the US.**
- A US seller can't hold a Mercari JP, Yahoo!オークション or Rakuma account.
- Demand runs both ways: Mercari launched its Global App in the United States on 2026-06-17 so overseas buyers can buy from Japanese sellers ([Mercari](https://about.mercari.com/en/press/news/articles/20260618globalapp/)).
- The US-to-Asia direction runs through eBay, which Portage already publishes to. The work is international-ready listings: shipping options and clear titles (R15).

**Next: Portage for resident sellers.**
- The market is large: Mercari 24.19M MAU, Karrot 23.19M.
- Every Japanese and Korean C2C platform bans tools:
  - Mercari: no access by a method other than its interface.
  - Yahoo: no auto-listing tools.
  - Rakuma: no BOTs or tools it hasn't permitted, and it has acted against tool vendors.
  - Bunjang: no auto-access programs, with escalating bans.
  - Karrot: no automated posting.
- A resident product would therefore be AI listing preparation plus share-sheet and copy kit. The posting itself would stay manual.

**Later: a Japanese entity.** A Portage KK with a 古物商許可 (secondhand dealer licence, Kobutsu Business Act article 3) could take US items on consignment and list them through business channels that have APIs: Mercari Shops (partner contract), Amazon JP, Rakuten. This is capital-heavy and only makes sense if the resident product proves demand.

## Roadmap

![roadmap diagram](/portage/img/marketplace-landscape/roadmap.svg)

| Phase | Item | First check (cheap, before any build) |
|---|---|---|
| Now | R1 eBay → Facebook | Search Facebook Marketplace for one live Portage eBay listing; note whether the partner icon shows |
| Now | OfferUp consent copy | Add both OfferUp clauses to the extension's consent screen text (build item, needs a go) |
| Now | R5 copy kit | None: lowest-risk route everywhere |
| Now | R10 Etsy Seller App | Register a Seller App in the Etsy developer portal for the operator's shop |
| Now | R20 risk tiers | Tier each marketplace from the ToS quotes already collected |
| 30 days | R6 OfferUp consent | Find a partnerships contact; send a one-page request |
| 30 days | R11 Nextdoor API | Submit the access form |
| 30 days | R4 share-sheet | On iPhone and Android, share a photo into the OfferUp, Mercari, Poshmark, Facebook, Karrot and Bunjang apps; record which accept it |
| 30 days | R15 international eBay | Check which Portage categories ship internationally today |
| 30 days | R21 sell-through | Already derivable from the orders and listings tables |
| 90 days | R7 / R8 storefront | Decide whether Portage or the user is merchant of record |
| 90 days | R12 / R13 | Ask eBay developer relations about Depop; test Whatnot's Shopify app |
| 6–12 months | R2, R9, R16, R17, R19 | Business development and market tests |

## Decisions for you

1. **OfferUp.** Two OfferUp rules now cover the extension. Keep it beta-only with disclosure and ask for consent (recommended)? Or switch OfferUp to copy kit and share-sheet until consent arrives?
2. **eBay → Facebook (R1).** Can you check one live Portage eBay listing on Facebook Marketplace? It's a two-minute check that could reframe the Facebook strategy.
3. **Storefront (R7 / R8 / R2).** Should Portage hold the buyer relationship, with its own listing pages and checkout? That decides merchant of record, payments and support, and it is the precondition for Facebook's Partnership Program and Google free listings.
4. **Asia.** Approve sell-into-Asia via eBay now (R15) and park the resident product until there's demand evidence? The recommendation is yes.
5. **Etsy.** Restore the parked adapter for your own shop on a Seller App now?
6. **Search cap.** The session's 200-search limit ran out, so later passes used RSS feeds and direct fetches. Raising `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION` would allow a fuller pass on the remaining gaps (Rakuma, Naver and OfferUp seller counts).

## Method and limits

- **Agents.** Version 2 used 6 Sonnet research agents: data gaps for NA (two passes), Japan and Korea, and APAC; competitor mechanisms; and precedents. The main session (Opus) did the verification, the divergent and convergent synthesis, and the diagrams.
- **Verification.** Key figures were confirmed by downloading the source and string-matching the quoted text:
  - Meta's eBay integration paragraph, OfferUp's Posting Rules, Karrot's ToS clauses, and Sell The Flip's mechanism;
  - the Mercari datasheet MAU rows, Gmarket's 660,000 sellers, Jimoty's ~10M monthly users, and WISEAPP's Q1 2026 MAU;
  - Joonggonara's cumulative listings and the Gumtree Group snapshot.
- **Search.** The session's WebSearch budget was exhausted before version 2 began. Discovery used Google News RSS, Bing News RSS, company IR pages, SEC EDGAR, DART, e-Gov, law.go.kr, Chrome Web Store manifests and the iTunes Search API.
- **Process breach.** Two agents scraped DuckDuckGo and Bing results pages (about 12 queries in total) before my instruction not to reached them. They stopped once it did. Only one figure from those queries was kept, Meesho's 234.20M annual transacting users, and it is labelled summary-only. Meesho's verified-raw annual report figure (264.29M) is the one used in the tables.
- **Not verified:**
  - which eBay listings Facebook shows;
  - which marketplace apps accept shared images;
  - Facebook Partnership Program eligibility;
  - Rakuma, Naver and Hellomarket scale;
  - Buyee, ZenMarket and KREAM global (403 or JS-only pages).
- No logged-in pages were viewed. Nothing was posted anywhere.
