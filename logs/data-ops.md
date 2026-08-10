### [2026-08-10] How we attribute leads with only a gclid (Google click ID)
- **Question**: how do we currently handle attribution for leads with only gclid id
- **Answer**: Traced the click-ID path through the model.
  - Detection (`staging.page_views__page_views`, ILkp3u-JHpQRzw): `has_gclid = query_params LIKE '%gclid%' OR '%gbraid%'`.
  - Platform: click-ID fallback fires only when there is NO utm_source — `WHEN has_gclid THEN 'google'`. is_paid = TRUE via same fallback → classified as **Paid Search**.
  - `is_click_id_attributed = (source_raw IS NULL AND has_gclid)` — the flag that isolates gclid-only leads (surfaced as `*_is_click_id` on every touch model + `click_id_sessions`).
  - Campaign/keyword recovered from URL, not UTMs: `gad_campaignid` → google_ads.campaign_stats lookup = `gclid_campaign_name`; `kw=` = `gclid_keyword`. `sessions` COALESCEs `utm_campaign, gclid_campaign_name` and `utm_term, gclid_keyword`, so campaign identity propagates into `conversion_touch_campaign/_term`.
  - Same click-ID fallback for other platforms: fbclid→meta, msclkid→bing, li_fat_id→linkedin.
  - Limitation: gclid-only lead with no `gad_campaignid` in URL → Paid Search but NULL campaign/keyword.
- **Thread**: C09QF4KQLMR / 1786370900.282879
