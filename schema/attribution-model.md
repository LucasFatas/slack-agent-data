# Attribution Model Architecture

## Overview

Multi-touch attribution model for Workwize paid ads. Contact-centric (one row per contact) with a deal-centric companion table for pipeline reporting.

## Table Dependency Chain

```
RAW SOURCES
├── hubspot_page_views.raw_events (HubSpot tracking pixel)
├── hubspot.contact, contact_property_history, contact_association
├── hubspot.deal_property_history
├── google_ads.* (campaign_stats, ad_group_stats, keyword_stats, ad_stats, campaign, ad_group_criterion)
├── facebook_ads.* (campaign_insight, ad_set_insight, ad_insight, *_actions, demographics_*, creative, ad)
├── linkedin_ads.* (ad_analytics_by_campaign, ad_analytics_by_creative, campaign, campaign_group, creative)
├── microsoft_ads.* (campaign_performance_daily_report, ad_group_performance_daily_report, keyword_performance_daily_report, ad_performance_daily_report, campaign, ad_group, keyword, ad)
├── reddit_ads.*
└── commercial.deal_shortened, commercial.deal_stage_history

STAGING (platform-specific daily metrics)
├── page_views/page_views (ILkp3u-JHpQRzw) — platform classification from UTMs
├── page_views/contact_conversions (xd-AMwmqNf6fZ1) — conversion events, mql_ts with qualifying form fallback
├── google_ads/campaigns (JB6347m75ZZ1O4), ad_groups, keywords, ads
├── meta/campaigns (WEAE7hDhp7yiD-), ad_sets, ads, platform_performance, placement_performance
├── linkedin/campaign_groups, campaigns, creatives
├── microsoft_ads/campaigns (hIn-60W8BagBZV), ad_groups, keywords, ads
└── google_analytics/page_views

INTERMEDIATE (sessionized + unified)
├── page_views/sessions (4w4ONRIfPLr8EE) — 30-min inactivity sessionization
├── page_views/contact_touchpoints (8iB4ZE9uQGxbxK) — touchpoint flags per session
├── ad_metrics/campaign_metrics (k2FGLCWSyLS3c_) — UNION of google+meta+linkedin+bing
└── ad_metrics/adset_metrics (KS1yb26a9O-og3) — UNION of all platform adsets

ANALYSIS (dashboard-ready)
├── contact_attribution (L7nzfK0KCIS37a) — THE main table, 1 row per contact
├── pipeline_attribution (N2dW17npUi53W9) — 1 row per inbound deal
├── google_performance, meta_performance, linkedin_performance, microsoft_performance
├── google_keyword_performance, microsoft_keyword_performance
├── adset_performance, content_performance
├── meta_sub_platform_performance, meta_placement_performance
├── landing_page_performance, session_page_views, touchpoint_timeline
└── influenced_pipeline

REVERSE ETL
├── contact_conversion_attribution (NRd5Vb0Bwd_2KG) — view for HubSpot sync
└── deal_conversion_attribution (8sx457W9sRr85H) — view for HubSpot sync
```

## Key Transform IDs

| Transform | ID | Notes |
|---|---|---|
| page_views staging | ILkp3u-JHpQRzw | Platform classification, UTM extraction |
| contact_conversions | xd-AMwmqNf6fZ1 | mql_ts COALESCE with qualifying form fallback |
| sessions | 4w4ONRIfPLr8EE | 30-min sessionization |
| contact_touchpoints | 8iB4ZE9uQGxbxK | Touch model flags |
| contact_attribution | L7nzfK0KCIS37a | Main attribution table |
| pipeline_attribution | N2dW17npUi53W9 | Deal-centric, matches commercial dashboard |
| campaign_metrics | k2FGLCWSyLS3c_ | Unified spend (4 platforms) |
| adset_metrics | KS1yb26a9O-og3 | Unified adset spend |
| content_performance | 2kNjol3I3hmj4c | Ad-level spend (4 platforms) |
| Orchestration | RPRe9-hoy6ayS1 | All transforms on this |

## contact_attribution Key Columns

**Identity:** contact_id, recent_conversion_ts, recent_conversion_form, mql_ts, sql_ts

**6 Touch Models** (each has platform, is_paid, campaign, content, term, ts, is_click_id, li_campaign_group, hsa_grp, hsa_ad):
- first_touch_*, conversion_touch_*, latest_touch_*
- first_paid_touch_*, conversion_paid_touch_*, latest_paid_touch_*

**Conversion touch extras:** conversion_touch_landing_page, conversion_touch_placement, conversion_touch_sub_platform, conversion_touch_source (classified channel)

**Deal:** deal_id, deal_stage, deal_amount, pipeline_name

**Journey:** total_sessions, paid_sessions, organic_sessions, days_first_to_conversion

## pipeline_attribution Key Columns

**Deal:** deal_id, deal_name, deal_amount, stage_name, channel_source, deal_geography, owner_name, bdr_name, reached_stage_2, is_opp, is_won

**Stage timestamps:** stage_0_ts, stage_1_ts, stage_2_ts, stage_3_ts, closed_won_ts

**Attribution (from primary contact):** contact_id, is_unattributed, conversion_touch_source/platform/campaign/term/landing_page/ts/li_campaign_group/placement/sub_platform, conversion_keyword, conversion_content, first_touch_source/platform/campaign, latest_touch_source/platform

**Contact:** recent_conversion_form, recent_conversion_ts, mql_ts, sql_ts, self_reported_source, total_sessions, paid_sessions

## Qualifying Demo Forms (for mql_ts fallback)
Pattern-based matching (updated 2026-07-23, no longer a hardcoded list):
```
%Landing Page Form%  (excluding %Partnership%)
lgf-demo%            (all LinkedIn Lead Gen demo forms)
lin_leadgen-form_demo-booking%
fb_leadgen-form_demo-booking%
```
Excluded by design: content downloads (lgf-content-*, lin_leadgen-form_ebook-*), newsletters, webinar signups, rep booking links, ROI calculators, partnership forms.

## Pipeline Filter
- `pipeline_name = '2025 New Sales Pipeline'`
- `channel_source IN ('Organic', 'Paid', 'Other Inbound', 'Event')` — excludes Outbound
- `channel_source != 'Outbound'` in contact_attribution deal_link

## HubSpot Portal
- Portal ID: 25662839
- Contact URL: `https://app-eu1.hubspot.com/contacts/25662839/record/0-1/{contact_id}/`
- Deal URL: `https://app-eu1.hubspot.com/contacts/25662839/record/0-3/{deal_id}/`
