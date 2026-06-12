# Tag / vendor taxonomy

Domain → vendor lookup for identifying what a tag *is* once `tag_scan.py` (or a
raw `passe capture`) has listed the hosts a page talks to. This is the canonical,
human-maintained reference. `scripts/tag_scan.py` carries a convenience subset for
auto-labelling; **when you identify a new vendor, add it here first** (and
optionally to the script's `TAXONOMY` list).

Matching is by substring against the request hostname. Many vendors use several
domains (CDN for the script, a separate beacon/collector for the data) — both
count as the same tag.

## Tag management
| Domain | Vendor / product |
|---|---|
| `googletagmanager.com` | Google Tag Manager (container id `GTM-XXXXXXX`) |
| first-party subdomain (`ssgtm.*`, `gtm.*`, `*.metric.*`) | **Server-side GTM** — first-party endpoint, easy to miss; look for `/g/collect`, `/gtm`, GA4-shaped params |
| `tags.tiqcdn.com` | Tealium iQ |
| `cdn.tagcommander.com` | Commanders Act / TagCommander |

## Consent / CMP
| Domain | Vendor |
|---|---|
| `cdn.cookielaw.org`, `*.onetrust.com` | OneTrust |
| `*.consensu.org` | IAB TCF v2 CMP (shared) |
| `consent.cookiebot.com` | Cookiebot |
| `sourcepoint`, `*.privacymanager.io` | Sourcepoint |
| `quantcast.mgr.consensu.org` | Quantcast Choice |

## Analytics
| Domain | Vendor |
|---|---|
| `google-analytics.com`, `analytics.google.com`, `region1.*` | Google Analytics 4 (property `G-XXXXXXX`) |
| `stats.g.doubleclick.net` | GA → DoubleClick remarketing join |
| `*.sc.omtrdc.net`, `*.omtrdc.net` | Adobe Analytics |
| `cdn.segment.com`, `api.segment.io` | Segment |

## Paid-media pixels (search / social / conversion)
| Domain | Vendor |
|---|---|
| `connect.facebook.net`, `facebook.com/tr` | Meta Pixel |
| `bat.bing.com` | Microsoft / Bing UET |
| `analytics.tiktok.com`, `ads.tiktok.com` | TikTok Pixel |
| `px.ads.linkedin.com`, `snap.licdn.com` | LinkedIn Insight |
| `tr.snapchat.com`, `sc-static.net` | Snap Pixel |
| `ct.pinterest.com`, `ads.pinterest.com` | Pinterest Tag |
| `googleadservices.com`, `googlesyndication.com`, `g.doubleclick.net`, `www.google.<tld>/ccm/collect` | Google Ads conversion / AdSense (conversion id `AW-XXXXXXXXX`) |

## Programmatic (DSP / SSP / retargeting)
| Domain | Vendor |
|---|---|
| `ib.adnxs.com`, `*.adnxs.com` | Xandr / AppNexus (Microsoft) |
| `*.creativecdn.com` | RTB House |
| `static.criteo.net`, `*.criteo.com` | Criteo |
| `*.adsrvr.org` | The Trade Desk |
| `*.casalemedia.com` | Index Exchange |
| `*.pubmatic.com` | PubMatic |
| `*.rubiconproject.com` | Magnite / Rubicon |
| `*.openx.net` | OpenX |
| `*.taboola.com` / `*.outbrain.com` | Taboola / Outbrain (native) |

## CDP / identity
| Domain | Vendor |
|---|---|
| `*.zeotap.com` | Zeotap |
| `*.demdex.net` | Adobe Audience Manager |
| `*.rlcdn.com`, `idsync.rlcdn.com` | LiveRamp |
| `id5-sync.com` | ID5 |
| `cdn.segment.com` | Segment (also analytics) |

## Affiliate / partner attribution
> The category most prone to **name collisions** — affiliate vendors love evocative product names. Confirm the *vendor*, not just the word.

| Domain | Vendor |
|---|---|
| `www.dwin1.com`, `*.awin1.com` | Awin |
| `lantern.roeye.com`, `lantern.roeyecdn.com` | **R.O.EYE "Lantern"** — UK affiliate-marketing tracker (Manchester; attribution product sold to Awin 2021). NOT ITV Lantern. |
| `prf.hn` | Impact / Partnerize |
| `*.tradedoubler.com` | Tradedoubler |
| `*.linksynergy.com` | Rakuten Advertising |
| `*.webgains.com` | Webgains |
| `*.cj.com`, `*.dpbolvw.net` | CJ / Commission Junction |

**How to recognise an affiliate tag in the wild:** drops a first-party cookie keyed
to the inbound referrer, with a multi-day expiry (the attribution window, often 30
days); only beacons when the referrer domain ≠ the current host (i.e. external/partner
traffic) or on a completed order; conversion calls carry `order_id` / `order_value`.

## Experience / testing / session replay
| Domain | Vendor |
|---|---|
| `*.optimizely.com` | Optimizely (A/B + RUM) |
| `*.contentsquare.net` | Contentsquare |
| `*.hotjar.com` | Hotjar |
| `*.fullstory.com` | FullStory |
| `*.mouseflow.com` | Mouseflow |
| `*.glassbox*` | Glassbox |
| `*.dynamicyield.com` | Dynamic Yield |
| `*.visualwebsiteoptimizer.com` | VWO |

## Survey / feedback
| Domain | Vendor |
|---|---|
| `*.siteintercept.qualtrics.com` | Qualtrics |
| `*.medallia.com` | Medallia |
| `*.usabilla.com` | Usabilla |

## Performance RUM
| Domain | Vendor |
|---|---|
| `cdn.speedcurve.com`, `lux.speedcurve.com` | SpeedCurve |
| `*.nr-data.net` | New Relic |
| `browser-intake-*.datadoghq.com` | Datadog RUM |
| `*.sentry.io`, `*.ingest.sentry.io` | Sentry |

## Infra / CDN / libraries (usually not "tags")
`code.jquery.com` (jQuery), `cdn.jsdelivr.net` / `unpkg.com` (generic CDNs),
`*.storyblok.com` (CMS), Cloudflare/Akamai/Fastly edges. Note these to explain the
host list, but they're plumbing, not marketing tags.
