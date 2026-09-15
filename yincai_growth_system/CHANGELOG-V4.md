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


## 4.2.0 · 国际化与规范化修复

- 将产品、选型、估算、询价、隐私和 Cookie 界面的关键文案扩展至十种语言；
- 首页及产品列表优先显示已人工批准的产品翻译，缺失时安全回退英文源数据；
- 旧版无语言网址统一 301 跳转，旧版表单 POST 使用 308 保留请求体；
- canonical 固定指向对应语言规范网址，避免查询参数与旧网址造成重复收录；
- 选型和成本工具同步使用已审核的本地化产品名称；
- 新增旧网址、规范链接、hreflang、中文询价和德语产品翻译回归测试。


### 4.2.0 角色与交互验证补丁

- 非管理员后台路由改为默认拒绝，补齐内容管理权限映射；
- 后台菜单根据岗位权限动态隐藏不可访问模块；
- 新增七类业务岗位权限矩阵及实际写入交互测试；
- 验证销售推进商机、产品技术生成文案、质量登记客诉、内容运营保存预览草稿、财务登记回款、交付更新样品状态与海外负责人创建客户。

- 扩展验证产品编辑与上传签名、询价附件、CSV 导入、事件与线索 API、客户评分 API、内容版本恢复、任务完成、密码重置、异常回款及退出登录；
- 补充用户密码/岗位校验、异常回款保护和不存在客户的 API 404 处理。
- GitHub Actions 增加 Chromium 真实浏览器测试，覆盖移动端菜单、语言跳转、Cookie 选择、公开工具、询价成功页和后台 CMS 控件。
