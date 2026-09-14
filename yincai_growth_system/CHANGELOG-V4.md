# Yincai v4 redesign

## Customer-facing website

- Rebuilt the homepage with a premium cosmetic-manufacturing visual system.
- Added a factory/product video section supporting uploaded MP4, MOV and WEBM files or HTTPS/YouTube embeds.
- Added ten public language choices: English, Simplified Chinese, Spanish, Portuguese, French, German, Arabic, Japanese, Korean and Russian.
- Added clear inline states and conversion routes to the packaging selector and cost estimator.
- Added a complete confirmation page after project brief submission.
- Improved mobile navigation, accessibility, reduced-motion behavior and form double-submit protection.

## Administration

- Added Website Content & Video CMS for multilingual hero copy, proof metrics, video and final CTA.
- Reorganized navigation into operating, sales, content/supply and system areas.
- Refreshed hierarchy, spacing, active states and editing workflow.
- Preserved the existing CRM, product, quote, quality, channel and permissions modules.

## Reliability

- Added automated CI smoke testing on Python 3.12.
- Added V4 tests for language selection, CMS persistence, homepage rendering and YouTube URL normalization.
- Added repository ignore rules for environment secrets, uploads, backups, cache and SQLite transient files.
