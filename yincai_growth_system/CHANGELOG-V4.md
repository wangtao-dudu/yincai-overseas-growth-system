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


## 4.0.1 · 上线加固

- 修复全站视觉断层并启用十种语言独立网址与 hreflang；
- 加固生产密钥、管理密码、代理来源、上传签名及数据库隔离；
- 记录询价隐私同意、语言、政策版本和参考附件；
- 访问统计改为同意后加载；
- 选型器增加匹配阈值与更多维度，成本估算提供费用拆分；
- 内容管理加入草稿、预览、发布、版本恢复；
- 扩展自动化冒烟测试覆盖多语言路由和内容发布流程。
