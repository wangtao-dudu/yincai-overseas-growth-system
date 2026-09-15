import json
import os
import secrets
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from flask import abort, flash, redirect, render_template, request, session, url_for


LANGUAGE_LABELS = {
    "en": "English", "zh": "简体中文", "es": "Español", "pt": "Português",
    "fr": "Français", "de": "Deutsch", "ar": "العربية",
    "ja": "日本語", "ko": "한국어", "ru": "Русский",
}

EN = {
    "nav_products": "Products", "nav_solutions": "Solutions", "nav_capabilities": "Capabilities",
    "nav_selector": "Packaging selector", "nav_cost": "Cost estimate", "nav_quote": "Request a quote",
    "explore": "Explore products", "start_project": "Start a project", "watch_story": "Watch our process",
    "solutions_kicker": "BUILT AROUND YOUR BUSINESS", "solutions_title": "A packaging partner built for the launch, not just the purchase order.",
    "brand_title": "Beauty brands", "brand_body": "Distinctive packaging, flexible development and support from first sample to repeat production.",
    "manufacturer_title": "Manufacturers", "manufacturer_body": "Fast quotation, multi-product sourcing and dependable coordination across customer programs.",
    "distributor_title": "Distributors", "distributor_body": "Structured product data, regional cooperation and scalable supply for local demand.",
    "process_kicker": "FROM BRIEF TO SCALE", "process_title": "A transparent route from idea to repeat production.",
    "step_1": "Discover", "step_1_body": "Formula, market, target cost and launch timing.",
    "step_2": "Engineer", "step_2_body": "Structure, material, decoration and compatibility.",
    "step_3": "Validate", "step_3_body": "Samples, appearance, leakage and quality records.",
    "step_4": "Deliver", "step_4_body": "Production milestones, inspection and global shipping.",
    "selected": "SELECTED PRODUCTS", "selected_title": "Proven formats, ready for your identity.",
    "view_all": "View all products", "video_kicker": "INSIDE YINCAI", "video_placeholder": "Upload a factory or product video from Website Content in the admin.",
    "estimate": "Calculate estimate", "recommend": "Show recommendations", "no_products": "Product data is being prepared.",
    "footer_line": "Custom cosmetic packaging for beauty brands and manufacturers.",
}
TRANSLATIONS = {
    "en": EN,
    "zh": {**EN, "nav_products":"产品中心","nav_solutions":"解决方案","nav_capabilities":"制造能力","nav_selector":"包装选择器","nav_cost":"成本估算","nav_quote":"提交需求","explore":"查看产品","start_project":"启动项目","watch_story":"观看制造过程","solutions_kicker":"围绕您的业务设计","solutions_title":"不仅提供容器，更对产品上市结果负责。","brand_title":"美妆品牌","brand_body":"从首轮样品到稳定复购，提供差异化包装与灵活开发。","manufacturer_title":"生产企业","manufacturer_body":"快速报价、多品类采购与跨项目交付协同。","distributor_title":"区域经销商","distributor_body":"结构化产品资料、区域合作与可规模化供应。","process_kicker":"从需求到量产","process_title":"透明、可验证的产品开发路径。","step_1":"需求诊断","step_1_body":"配方、市场、目标成本和上市周期。","step_2":"工程开发","step_2_body":"结构、材料、表面工艺与相容性。","step_3":"验证测试","step_3_body":"样品、外观、密封与质量记录。","step_4":"量产交付","step_4_body":"生产节点、检验和全球运输。","selected":"精选产品","selected_title":"成熟包装结构，承载您的品牌识别。","view_all":"查看全部产品","video_kicker":"走进银彩","video_placeholder":"请在后台“网站内容”上传工厂或产品视频。","estimate":"计算估算区间","recommend":"显示推荐结果","no_products":"产品资料正在准备中。","footer_line":"为美妆品牌与制造企业提供定制化妆品包装。"},
    "es": {**EN, "nav_products":"Productos","nav_solutions":"Soluciones","nav_capabilities":"Capacidades","nav_selector":"Selector de envases","nav_cost":"Estimación de costes","nav_quote":"Solicitar cotización","explore":"Ver productos","start_project":"Iniciar proyecto","watch_story":"Ver nuestro proceso","solutions_title":"Un socio de envases comprometido con su lanzamiento.","brand_title":"Marcas de belleza","manufacturer_title":"Fabricantes","distributor_title":"Distribuidores","process_title":"Una ruta transparente de la idea a la producción.","selected_title":"Formatos probados listos para su marca.","view_all":"Ver todos"},
    "pt": {**EN, "nav_products":"Produtos","nav_solutions":"Soluções","nav_capabilities":"Capacidades","nav_selector":"Seletor de embalagens","nav_cost":"Estimativa de custo","nav_quote":"Solicitar cotação","explore":"Explorar produtos","start_project":"Iniciar projeto","watch_story":"Ver processo","solutions_title":"Um parceiro de embalagem focado no seu lançamento.","brand_title":"Marcas de beleza","manufacturer_title":"Fabricantes","distributor_title":"Distribuidores","process_title":"Um caminho transparente da ideia à produção.","selected_title":"Formatos comprovados, prontos para sua marca.","view_all":"Ver todos"},
    "fr": {**EN, "nav_products":"Produits","nav_solutions":"Solutions","nav_capabilities":"Savoir-faire","nav_selector":"Sélecteur d’emballage","nav_cost":"Estimation des coûts","nav_quote":"Demander un devis","explore":"Voir les produits","start_project":"Démarrer un projet","watch_story":"Voir notre processus","solutions_title":"Un partenaire emballage engagé dans votre lancement.","brand_title":"Marques beauté","manufacturer_title":"Fabricants","distributor_title":"Distributeurs","process_title":"Un parcours transparent de l’idée à la production.","selected_title":"Des formats éprouvés, prêts pour votre marque.","view_all":"Voir tout"},
    "de": {**EN, "nav_products":"Produkte","nav_solutions":"Lösungen","nav_capabilities":"Kompetenzen","nav_selector":"Verpackungsfinder","nav_cost":"Kostenschätzung","nav_quote":"Angebot anfragen","explore":"Produkte ansehen","start_project":"Projekt starten","watch_story":"Prozess ansehen","solutions_title":"Ein Verpackungspartner mit Verantwortung für Ihren Launch.","brand_title":"Beauty-Marken","manufacturer_title":"Hersteller","distributor_title":"Distributoren","process_title":"Ein transparenter Weg von der Idee zur Serie.","selected_title":"Bewährte Formate für Ihre Markenidentität.","view_all":"Alle ansehen"},
    "ar": {**EN, "nav_products":"المنتجات","nav_solutions":"الحلول","nav_capabilities":"القدرات","nav_selector":"اختيار العبوة","nav_cost":"تقدير التكلفة","nav_quote":"طلب عرض سعر","explore":"استكشف المنتجات","start_project":"ابدأ مشروعاً","watch_story":"شاهد عملية الإنتاج","solutions_title":"شريك تعبئة ملتزم بنجاح إطلاق منتجك.","brand_title":"علامات التجميل","manufacturer_title":"المصنّعون","distributor_title":"الموزعون","process_title":"مسار واضح من الفكرة إلى الإنتاج.","selected_title":"تصاميم موثوقة جاهزة لهوية علامتك.","view_all":"عرض الكل"},
    "ja": {**EN, "nav_products":"製品","nav_solutions":"ソリューション","nav_capabilities":"製造力","nav_selector":"包装セレクター","nav_cost":"コスト見積り","nav_quote":"見積り依頼","explore":"製品を見る","start_project":"相談を始める","watch_story":"製造工程を見る","solutions_title":"容器だけでなく、発売の成功に向き合う包装パートナー。","brand_title":"ビューティーブランド","manufacturer_title":"メーカー","distributor_title":"販売代理店","process_title":"企画から量産まで、透明性のある開発プロセス。","selected_title":"ブランドに対応できる実績ある包装。","view_all":"すべて見る"},
    "ko": {**EN, "nav_products":"제품","nav_solutions":"솔루션","nav_capabilities":"제조 역량","nav_selector":"패키지 선택","nav_cost":"비용 견적","nav_quote":"견적 요청","explore":"제품 보기","start_project":"프로젝트 시작","watch_story":"제조 과정 보기","solutions_title":"용기를 넘어 출시 성과까지 책임지는 패키징 파트너.","brand_title":"뷰티 브랜드","manufacturer_title":"제조사","distributor_title":"유통사","process_title":"아이디어에서 양산까지 투명한 개발 과정.","selected_title":"브랜드를 위한 검증된 패키지 형식.","view_all":"전체 보기"},
    "ru": {**EN, "nav_products":"Продукция","nav_solutions":"Решения","nav_capabilities":"Возможности","nav_selector":"Подбор упаковки","nav_cost":"Расчёт стоимости","nav_quote":"Запросить цену","explore":"Смотреть продукцию","start_project":"Начать проект","watch_story":"Смотреть процесс","solutions_title":"Партнёр по упаковке, отвечающий за успешный запуск.","brand_title":"Бьюти-бренды","manufacturer_title":"Производители","distributor_title":"Дистрибьюторы","process_title":"Прозрачный путь от идеи до серийного производства.","selected_title":"Проверенные форматы для вашего бренда.","view_all":"Смотреть все"},
}

CONTENT_DEFAULTS = {
    "en": {
        "hero_kicker": "COSMETIC PACKAGING, ENGINEERED TO LAUNCH",
        "hero_title": "Packaging that makes the first impression last.",
        "hero_body": "Custom bottles, jars, pumps and closures—developed with the speed, evidence and production control global beauty teams expect.",
        "metric_1_value": "48h", "metric_1_label": "initial project response",
        "metric_2_value": "10+", "metric_2_label": "decoration processes",
        "metric_3_value": "100%", "metric_3_label": "pre-production verification",
        "video_title": "See how a packaging idea becomes a repeatable product.",
        "video_body": "Use a factory, process or hero-product film to turn manufacturing capability into visible proof.",
        "cta_title": "Bring us the brief. Leave with a production route.",
        "cta_body": "Tell us the formula, format, quantity and launch date. We will respond with practical next steps.",
        "solutions_kicker": "BUILT AROUND YOUR BUSINESS",
        "solutions_title": "A packaging partner built for the launch, not just the purchase order.",
        "solutions_body": "Choose the cooperation route that matches your commercial model and launch stage.",
        "solution_1_label": "01 / BRAND", "solution_1_title": "Beauty brands",
        "solution_1_body": "Distinctive packaging, flexible development and support from first sample to repeat production.",
        "solution_2_label": "02 / OEM·ODM", "solution_2_title": "Manufacturers",
        "solution_2_body": "Fast quotation, multi-product sourcing and dependable coordination across customer programs.",
        "solution_3_label": "03 / CHANNEL", "solution_3_title": "Distributors",
        "solution_3_body": "Structured product data, regional cooperation and scalable supply for local demand.",
        "capabilities_kicker": "FROM BRIEF TO SCALE",
        "capabilities_title": "A transparent route from idea to repeat production.",
        "capabilities_body": "Each stage leaves a clear decision, owner and verification record.",
        "capability_1_title": "Discover", "capability_1_body": "Formula, market, target cost and launch timing.",
        "capability_2_title": "Engineer", "capability_2_body": "Structure, material, decoration and compatibility.",
        "capability_3_title": "Validate", "capability_3_body": "Samples, appearance, leakage and quality records.",
        "capability_4_title": "Deliver", "capability_4_body": "Production milestones, inspection and global shipping.",
        "products_kicker": "PRODUCT DATABASE",
        "products_title": "Packaging selected for real projects.",
        "products_intro": "Specifications, customization routes and production information for faster project decisions.",
        "products_featured_kicker": "SELECTED PRODUCTS",
        "products_featured_title": "Proven formats, ready for your identity.",
        "products_empty_title": "Product data is being prepared.",
        "products_empty_body": "Send a project brief for a tailored recommendation.",
        "selector_kicker": "SMART MATCH / 01",
        "selector_title": "Packaging selector",
        "selector_intro": "Match product type, usage, dispensing, material, capacity, sustainability and order quantity.",
        "selector_empty_kicker": "YC / MATCH ENGINE",
        "selector_empty_title": "Explainable recommendations appear here.",
        "selector_empty_body": "Final compatibility and specifications are confirmed during sampling.",
        "selector_no_match_kicker": "NO STRONG MATCH",
        "selector_no_match_title": "We will build a shortlist manually.",
        "selector_manual_title": "Catalog data is still being prepared.",
        "cost_kicker": "BUDGET BUILDER / 02",
        "cost_title": "Cost estimate",
        "cost_intro": "Build an early planning range from approved public pricing rules.",
        "cost_empty_kicker": "YC / COST ENGINE",
        "cost_empty_title": "Your budget range will appear here immediately.",
        "cost_empty_body": "Only products with approved public cost rules can be calculated.",
        "cost_note": "Planning estimate only. Freight, tax and testing are confirmed separately.",
        "cost_no_rules_title": "No public cost rule is available.",
        "cost_no_rules_body": "Send quantity, finish and reference artwork for a manual estimate.",
        "cost_result_kicker": "ESTIMATED PROJECT RANGE",
        "cost_estimate_cta": "Turn estimate into exact quote",
    },
    "zh": {
        "hero_kicker": "为产品上市而设计的化妆品包装",
        "hero_title": "让第一眼的吸引力，变成长期的品牌记忆。",
        "hero_body": "从瓶、罐、泵头到配套盖件，以全球美妆团队需要的速度、验证和量产控制完成定制开发。",
        "metric_1_value": "48小时", "metric_1_label": "项目首次响应",
        "metric_2_value": "10+", "metric_2_label": "表面工艺选择",
        "metric_3_value": "100%", "metric_3_label": "量产前验证",
        "video_title": "看见一个包装创意如何成为可稳定复购的产品。",
        "video_body": "通过工厂、工艺或主推产品视频，把制造能力变成客户看得见的证据。",
        "cta_title": "提交需求，获得一条可执行的量产路径。",
        "cta_body": "告诉我们配方、包装形式、数量和上市时间，团队将给出明确的下一步。",
        "solutions_body": "根据客户商业模式与产品阶段选择合适的合作路径。",
        "solution_1_label": "01 / 品牌", "solution_2_label": "02 / OEM·ODM", "solution_3_label": "03 / 渠道",
        "capabilities_body": "每个阶段都有明确决策、负责人和验证记录。",
        "products_empty_body": "提交项目需求，我们将提供针对性产品建议。",
        "selector_empty_kicker": "银彩 / 智能匹配",
        "selector_empty_title": "可解释的产品建议将在这里显示。",
        "selector_empty_body": "最终相容性与规格将在打样阶段确认。",
        "selector_no_match_kicker": "暂无高匹配结果",
        "selector_no_match_title": "我们将人工建立候选清单。",
        "selector_manual_title": "产品目录数据正在准备中。",
        "cost_kicker": "预算测算 / 02",
        "cost_empty_kicker": "银彩 / 成本引擎",
        "cost_empty_title": "预算区间将在这里即时显示。",
        "cost_empty_body": "只有已批准公开报价规则的产品可以计算。",
        "cost_note": "仅供前期规划；运费、税费与测试费用需另行确认。",
        "cost_no_rules_title": "目前没有可公开计算的成本规则。",
        "cost_no_rules_body": "请提交数量、工艺和参考图，我们将人工估算。",
        "cost_result_kicker": "项目成本估算区间",
        "cost_estimate_cta": "转为精确报价",
    },
}

CONTENT_FIELDS = (
    "hero_kicker", "hero_title", "hero_body",
    "metric_1_value", "metric_1_label", "metric_2_value", "metric_2_label",
    "metric_3_value", "metric_3_label", "video_title", "video_body",
    "cta_title", "cta_body",
    "solutions_kicker", "solutions_title", "solutions_body",
    "solution_1_label", "solution_1_title", "solution_1_body",
    "solution_2_label", "solution_2_title", "solution_2_body",
    "solution_3_label", "solution_3_title", "solution_3_body",
    "capabilities_kicker", "capabilities_title", "capabilities_body",
    "capability_1_title", "capability_1_body", "capability_2_title", "capability_2_body",
    "capability_3_title", "capability_3_body", "capability_4_title", "capability_4_body",
    "products_kicker", "products_title", "products_intro",
    "products_featured_kicker", "products_featured_title", "products_empty_title", "products_empty_body",
    "selector_kicker", "selector_title", "selector_intro",
    "selector_empty_kicker", "selector_empty_title", "selector_empty_body",
    "selector_no_match_kicker", "selector_no_match_title", "selector_manual_title",
    "cost_kicker", "cost_title", "cost_intro", "cost_empty_kicker", "cost_empty_title",
    "cost_empty_body", "cost_note", "cost_no_rules_title", "cost_no_rules_body",
    "cost_result_kicker", "cost_estimate_cta",
)

CONTENT_TRANSLATION_MAP = {
    "solutions_kicker": "solutions_kicker", "solutions_title": "solutions_title",
    "solution_1_title": "brand_title", "solution_1_body": "brand_body",
    "solution_2_title": "manufacturer_title", "solution_2_body": "manufacturer_body",
    "solution_3_title": "distributor_title", "solution_3_body": "distributor_body",
    "capabilities_kicker": "process_kicker", "capabilities_title": "process_title",
    "capability_1_title": "step_1", "capability_1_body": "step_1_body",
    "capability_2_title": "step_2", "capability_2_body": "step_2_body",
    "capability_3_title": "step_3", "capability_3_body": "step_3_body",
    "capability_4_title": "step_4", "capability_4_body": "step_4_body",
    "products_kicker": "product_database", "products_title": "products_title",
    "products_intro": "products_intro", "products_featured_kicker": "selected",
    "products_featured_title": "selected_title", "products_empty_title": "no_products",
    "selector_title": "nav_selector", "selector_intro": "selector_intro",
    "cost_title": "nav_cost", "cost_intro": "cost_intro",
}

CONTENT_PAGES = {
    "home": {
        "label": "首页首屏", "number": "01", "path": "/en/",
        "description": "品牌定位、可信度数据、视频与最终询价行动。",
        "links": (),
        "groups": (
            ("首屏价值", "客户进入网站三秒内必须看懂的核心价值。", (
                ("hero_kicker", "顶部小标题", "text"), ("hero_title", "核心标题", "textarea"),
                ("hero_body", "价值说明", "textarea"),
            )),
            ("可信度数据", "只填写可以被销售与质量团队核验的数据。", (
                ("metric_1_value", "数据 1", "text"), ("metric_1_label", "数据 1 说明", "text"),
                ("metric_2_value", "数据 2", "text"), ("metric_2_label", "数据 2 说明", "text"),
                ("metric_3_value", "数据 3", "text"), ("metric_3_label", "数据 3 说明", "text"),
            )),
            ("视频证据", "标题和说明在此编辑；文件或链接在下方上传。", (
                ("video_title", "视频区标题", "textarea"), ("video_body", "视频区说明", "textarea"),
            )),
            ("询价转化", "页面底部推动客户提交项目需求。", (
                ("cta_title", "行动标题", "textarea"), ("cta_body", "行动说明", "textarea"),
            )),
        ),
    },
    "solutions": {
        "label": "解决方案", "number": "02", "path": "/en/#solutions",
        "description": "按美妆品牌、制造企业和渠道商组织合作价值。",
        "links": (),
        "groups": (
            ("板块标题", "说明银彩针对不同客户类型提供什么价值。", (
                ("solutions_kicker", "顶部小标题", "text"), ("solutions_title", "核心标题", "textarea"),
                ("solutions_body", "板块说明", "textarea"),
            )),
            ("客户方案 1", "面向美妆品牌。", (
                ("solution_1_label", "分类标签", "text"), ("solution_1_title", "方案标题", "text"),
                ("solution_1_body", "方案说明", "textarea"),
            )),
            ("客户方案 2", "面向 OEM / ODM 制造企业。", (
                ("solution_2_label", "分类标签", "text"), ("solution_2_title", "方案标题", "text"),
                ("solution_2_body", "方案说明", "textarea"),
            )),
            ("客户方案 3", "面向区域经销商与渠道伙伴。", (
                ("solution_3_label", "分类标签", "text"), ("solution_3_title", "方案标题", "text"),
                ("solution_3_body", "方案说明", "textarea"),
            )),
        ),
    },
    "capabilities": {
        "label": "能力与流程", "number": "03", "path": "/en/#process",
        "description": "把需求、工程、验证和交付能力变成可见证据。",
        "links": (),
        "groups": (
            ("板块标题", "用客户能理解的语言解释制造能力。", (
                ("capabilities_kicker", "顶部小标题", "text"), ("capabilities_title", "核心标题", "textarea"),
                ("capabilities_body", "板块说明", "textarea"),
            )),
            ("01 需求诊断", "明确配方、市场、成本和时间。", (
                ("capability_1_title", "步骤标题", "text"), ("capability_1_body", "步骤说明", "textarea"),
            )),
            ("02 工程开发", "明确结构、材料和工艺。", (
                ("capability_2_title", "步骤标题", "text"), ("capability_2_body", "步骤说明", "textarea"),
            )),
            ("03 验证测试", "明确打样、相容性与质量记录。", (
                ("capability_3_title", "步骤标题", "text"), ("capability_3_body", "步骤说明", "textarea"),
            )),
            ("04 量产交付", "明确生产、检验和运输。", (
                ("capability_4_title", "步骤标题", "text"), ("capability_4_body", "步骤说明", "textarea"),
            )),
        ),
    },
    "products": {
        "label": "产品中心", "number": "04", "path": "/en/products",
        "description": "编辑产品页定位；具体产品、图片和多语言在关联入口维护。",
        "links": (("产品与素材", "admin_products"), ("多语言审核", "translations")),
        "groups": (
            ("产品页标题", "帮助采购快速理解产品数据库的用途。", (
                ("products_kicker", "顶部小标题", "text"), ("products_title", "核心标题", "textarea"),
                ("products_intro", "页面说明", "textarea"),
            )),
            ("首页精选产品", "控制首页产品区的标题。", (
                ("products_featured_kicker", "顶部小标题", "text"),
                ("products_featured_title", "核心标题", "textarea"),
            )),
            ("无产品状态", "目录尚未发布产品时给客户明确下一步。", (
                ("products_empty_title", "空状态标题", "text"),
                ("products_empty_body", "空状态说明", "textarea"),
            )),
        ),
    },
    "selector": {
        "label": "包装选择器", "number": "05", "path": "/en/packaging-selector",
        "description": "编辑工具说明与结果状态；匹配依据来自产品和选型规则。",
        "links": (("产品与素材", "admin_products"), ("选型与报价规则", "catalog_rules")),
        "groups": (
            ("工具首屏", "告诉客户需要输入什么，以及会得到什么。", (
                ("selector_kicker", "顶部小标题", "text"), ("selector_title", "工具标题", "text"),
                ("selector_intro", "工具说明", "textarea"),
            )),
            ("等待结果", "客户尚未提交条件时的提示。", (
                ("selector_empty_kicker", "状态标签", "text"), ("selector_empty_title", "状态标题", "text"),
                ("selector_empty_body", "状态说明", "textarea"),
            )),
            ("无匹配结果", "没有达到推荐阈值时引导人工选型。", (
                ("selector_no_match_kicker", "状态标签", "text"),
                ("selector_no_match_title", "状态标题", "text"),
                ("selector_manual_title", "目录未就绪提示", "text"),
            )),
        ),
    },
    "cost": {
        "label": "成本估算", "number": "06", "path": "/en/cost-estimator",
        "description": "编辑预算工具说明、免责声明和询价转化文案。",
        "links": (("报价与环保数据", "catalog_rules"), ("自动报价", "auto_quote")),
        "groups": (
            ("工具首屏", "说明估算范围和数据来源。", (
                ("cost_kicker", "顶部小标题", "text"), ("cost_title", "工具标题", "text"),
                ("cost_intro", "工具说明", "textarea"),
            )),
            ("等待结果", "客户尚未计算时显示。", (
                ("cost_empty_kicker", "状态标签", "text"), ("cost_empty_title", "状态标题", "text"),
                ("cost_empty_body", "状态说明", "textarea"),
            )),
            ("规则与结果", "无规则提示、估算免责声明和下一步行动。", (
                ("cost_note", "估算免责声明", "textarea"), ("cost_no_rules_title", "无规则标题", "text"),
                ("cost_no_rules_body", "无规则说明", "textarea"),
                ("cost_result_kicker", "结果标签", "text"), ("cost_estimate_cta", "询价按钮文案", "text"),
            )),
        ),
    },
}

def page_field_names(page):
    return tuple(field[0] for group in CONTENT_PAGES[page]["groups"] for field in group[2])



EXTRA_TRANSLATIONS = {
    "en": {"product_database":"PRODUCT DATABASE","products_title":"Packaging selected for real projects.","all":"All","material":"Material","capacity":"Capacity","dimensions":"Dimensions","moq":"Minimum order","sample_time":"Sample time","lead_time":"Production lead time","customization":"Customization","verification":"Verification","request_samples":"Request quote or samples","privacy":"Privacy","quote_title":"Turn your packaging idea into a production route.","submit":"Submit project brief","thanks_title":"Thank you. A packaging specialist will contact you shortly.","reference":"Request reference"},
    "zh": {"product_database":"产品数据库","products_title":"为真实项目筛选的包装方案。","all":"全部","material":"材料","capacity":"容量","dimensions":"尺寸","moq":"最低采购量","sample_time":"样品周期","lead_time":"生产周期","customization":"定制开发","verification":"质量验证","request_samples":"询价或申请样品","privacy":"隐私政策","quote_title":"把包装创意转化为可执行的量产路径。","submit":"提交项目需求","thanks_title":"感谢提交，包装专员将尽快与您联系。","reference":"需求编号"},
    "es": {"product_database":"CATÁLOGO DE PRODUCTOS","products_title":"Envases seleccionados para proyectos reales.","all":"Todos","material":"Material","capacity":"Capacidad","dimensions":"Dimensiones","moq":"Pedido mínimo","sample_time":"Plazo de muestra","lead_time":"Plazo de producción","customization":"Personalización","verification":"Verificación","request_samples":"Solicitar precio o muestras","privacy":"Privacidad","quote_title":"Convierta su idea de envase en una ruta de producción.","submit":"Enviar proyecto","thanks_title":"Gracias. Un especialista se pondrá en contacto pronto.","reference":"Referencia"},
    "pt": {"product_database":"CATÁLOGO DE PRODUTOS","products_title":"Embalagens selecionadas para projetos reais.","all":"Todos","material":"Material","capacity":"Capacidade","dimensions":"Dimensões","moq":"Pedido mínimo","sample_time":"Prazo da amostra","lead_time":"Prazo de produção","customization":"Personalização","verification":"Verificação","request_samples":"Solicitar preço ou amostras","privacy":"Privacidade","quote_title":"Transforme sua ideia de embalagem em uma rota de produção.","submit":"Enviar projeto","thanks_title":"Obrigado. Um especialista entrará em contato em breve.","reference":"Referência"},
    "fr": {"product_database":"CATALOGUE PRODUITS","products_title":"Des emballages sélectionnés pour des projets réels.","all":"Tous","material":"Matériau","capacity":"Capacité","dimensions":"Dimensions","moq":"Commande minimum","sample_time":"Délai échantillon","lead_time":"Délai production","customization":"Personnalisation","verification":"Vérification","request_samples":"Demander un prix ou des échantillons","privacy":"Confidentialité","quote_title":"Transformez votre idée en parcours de production.","submit":"Envoyer le projet","thanks_title":"Merci. Un spécialiste vous contactera rapidement.","reference":"Référence"},
    "de": {"product_database":"PRODUKTKATALOG","products_title":"Verpackungen für reale Projekte ausgewählt.","all":"Alle","material":"Material","capacity":"Volumen","dimensions":"Abmessungen","moq":"Mindestmenge","sample_time":"Musterzeit","lead_time":"Produktionszeit","customization":"Individualisierung","verification":"Prüfung","request_samples":"Preis oder Muster anfragen","privacy":"Datenschutz","quote_title":"Machen Sie aus Ihrer Idee einen Produktionsweg.","submit":"Projekt senden","thanks_title":"Vielen Dank. Ein Spezialist meldet sich in Kürze.","reference":"Referenz"},
    "ar": {"product_database":"كتالوج المنتجات","products_title":"عبوات مختارة لمشاريع حقيقية.","all":"الكل","material":"المادة","capacity":"السعة","dimensions":"الأبعاد","moq":"الحد الأدنى","sample_time":"مدة العينة","lead_time":"مدة الإنتاج","customization":"التخصيص","verification":"التحقق","request_samples":"طلب سعر أو عينات","privacy":"الخصوصية","quote_title":"حوّل فكرة العبوة إلى مسار إنتاج.","submit":"إرسال المشروع","thanks_title":"شكراً لك. سيتواصل معك متخصص قريباً.","reference":"رقم الطلب"},
    "ja": {"product_database":"製品カタログ","products_title":"実際のプロジェクト向けに選定した包装。","all":"すべて","material":"素材","capacity":"容量","dimensions":"寸法","moq":"最低発注量","sample_time":"サンプル期間","lead_time":"生産期間","customization":"カスタマイズ","verification":"検証","request_samples":"見積り・サンプル依頼","privacy":"プライバシー","quote_title":"包装アイデアを量産ルートへ。","submit":"プロジェクトを送信","thanks_title":"ありがとうございます。担当者よりご連絡します。","reference":"受付番号"},
    "ko": {"product_database":"제품 카탈로그","products_title":"실제 프로젝트를 위한 패키지.","all":"전체","material":"소재","capacity":"용량","dimensions":"크기","moq":"최소 주문량","sample_time":"샘플 기간","lead_time":"생산 기간","customization":"맞춤 제작","verification":"검증","request_samples":"견적 또는 샘플 요청","privacy":"개인정보","quote_title":"패키지 아이디어를 양산 경로로 전환하세요.","submit":"프로젝트 제출","thanks_title":"감사합니다. 담당자가 곧 연락드리겠습니다.","reference":"요청 번호"},
    "ru": {"product_database":"КАТАЛОГ ПРОДУКЦИИ","products_title":"Упаковка для реальных проектов.","all":"Все","material":"Материал","capacity":"Объём","dimensions":"Размеры","moq":"Минимальный заказ","sample_time":"Срок образца","lead_time":"Срок производства","customization":"Персонализация","verification":"Проверка","request_samples":"Запросить цену или образцы","privacy":"Конфиденциальность","quote_title":"Превратите идею упаковки в план производства.","submit":"Отправить проект","thanks_title":"Спасибо. Специалист скоро свяжется с вами.","reference":"Номер запроса"},
}
for _language, _labels in EXTRA_TRANSLATIONS.items():
    TRANSLATIONS[_language] = {**EN, **TRANSLATIONS.get(_language, {}), **_labels}


FULL_UI = {
    "en": {
        "products_intro":"Specifications, customization routes and production information for faster project decisions.","view_specs":"View specifications","selector_intro":"Match product type, usage, dispensing, material, capacity, sustainability and order quantity.","category_label":"Packaging category","any_category":"Any category","use_case":"Use case","dispensing":"Dispensing format","sustainability_goal":"Sustainability goal","estimated_quantity":"Estimated quantity","manual_recommend":"Get a manual recommendation","cost_intro":"Build an early planning range from approved quantity tiers and optional project costs.","product_label":"Product","select_product":"Select a configured product","include_decoration":"Include decoration","include_tooling":"Include tooling","manual_estimate":"Request manual estimate","company_name":"Company name","your_name":"Your name","work_email":"Work email","phone":"Phone / WhatsApp","country":"Country","product_needed":"Product needed","timeline":"Target timeline","project_details":"Project details","reference_file":"Reference image or PDF","consent_text":"I agree that my information and attachment may be used to respond to this request.","privacy_title":"How project information is used.","privacy_intro":"We use submitted information only to evaluate packaging needs, prepare recommendations, communicate quotations and deliver projects. We do not sell contact information.","cookie_title":"Privacy choices","cookie_body":"Optional analytics help us improve this website. They load only after you accept.","essential_only":"Essential only","accept_analytics":"Accept analytics"},
    "zh": {
        "products_intro":"查看规格、定制路线与生产信息，更快完成项目决策。","view_specs":"查看规格","selector_intro":"按包装类型、用途、出料方式、材料、容量、环保目标与采购量进行匹配。","category_label":"包装类别","any_category":"不限类别","use_case":"使用场景","dispensing":"出料方式","sustainability_goal":"环保目标","estimated_quantity":"预计采购量","manual_recommend":"获取人工推荐","cost_intro":"基于已审核的数量阶梯和可选项目费用生成前期预算区间。","product_label":"产品","select_product":"选择已配置产品","include_decoration":"计入表面工艺","include_tooling":"计入模具费用","manual_estimate":"申请人工估算","company_name":"公司名称","your_name":"您的姓名","work_email":"工作邮箱","phone":"电话 / WhatsApp","country":"国家或地区","product_needed":"所需产品","timeline":"目标时间","project_details":"项目说明","reference_file":"参考图片或 PDF","consent_text":"我同意银彩使用本人信息及附件回复本次需求。","privacy_title":"我们如何使用项目信息。","privacy_intro":"提交的信息仅用于评估包装需求、提供建议、沟通报价及交付项目；我们不会出售联系人信息。","cookie_title":"隐私选择","cookie_body":"可选访问统计帮助我们改善网站，仅在您同意后加载。","essential_only":"仅必要功能","accept_analytics":"同意统计"},
    "es": {
        "products_intro":"Especificaciones, personalización y producción para decidir más rápido.","view_specs":"Ver especificaciones","selector_intro":"Combine tipo, uso, dispensación, material, capacidad, sostenibilidad y cantidad.","category_label":"Categoría de envase","any_category":"Cualquier categoría","use_case":"Uso","dispensing":"Sistema de dispensación","sustainability_goal":"Objetivo sostenible","estimated_quantity":"Cantidad estimada","manual_recommend":"Recomendación manual","cost_intro":"Cree un rango inicial con tarifas aprobadas y costes opcionales.","product_label":"Producto","select_product":"Seleccione un producto","include_decoration":"Incluir decoración","include_tooling":"Incluir moldes","manual_estimate":"Solicitar cálculo manual","company_name":"Empresa","your_name":"Nombre","work_email":"Correo profesional","phone":"Teléfono / WhatsApp","country":"País","product_needed":"Producto necesario","timeline":"Plazo objetivo","project_details":"Detalles del proyecto","reference_file":"Imagen o PDF de referencia","consent_text":"Acepto el uso de mis datos y adjuntos para responder a esta solicitud.","privacy_title":"Cómo utilizamos la información del proyecto.","privacy_intro":"Usamos la información solo para evaluar, recomendar, cotizar y entregar el proyecto. No vendemos datos de contacto.","cookie_title":"Opciones de privacidad","cookie_body":"La analítica opcional solo se carga tras su consentimiento.","essential_only":"Solo esenciales","accept_analytics":"Aceptar analítica"},
    "pt": {
        "products_intro":"Especificações, personalização e produção para decisões mais rápidas.","view_specs":"Ver especificações","selector_intro":"Combine tipo, uso, dispensação, material, capacidade, sustentabilidade e quantidade.","category_label":"Categoria da embalagem","any_category":"Qualquer categoria","use_case":"Aplicação","dispensing":"Sistema de dosagem","sustainability_goal":"Meta sustentável","estimated_quantity":"Quantidade estimada","manual_recommend":"Recomendação manual","cost_intro":"Crie uma faixa inicial com preços aprovados e custos opcionais.","product_label":"Produto","select_product":"Selecione um produto","include_decoration":"Incluir decoração","include_tooling":"Incluir ferramental","manual_estimate":"Solicitar estimativa manual","company_name":"Empresa","your_name":"Nome","work_email":"E-mail profissional","phone":"Telefone / WhatsApp","country":"País","product_needed":"Produto necessário","timeline":"Prazo desejado","project_details":"Detalhes do projeto","reference_file":"Imagem ou PDF de referência","consent_text":"Concordo com o uso dos meus dados e anexos para responder a esta solicitação.","privacy_title":"Como usamos as informações do projeto.","privacy_intro":"Usamos os dados apenas para avaliar, recomendar, cotar e entregar o projeto. Não vendemos contatos.","cookie_title":"Opções de privacidade","cookie_body":"A análise opcional só é carregada após o seu consentimento.","essential_only":"Somente essenciais","accept_analytics":"Aceitar análise"},
    "fr": {
        "products_intro":"Spécifications, personnalisation et production pour décider plus vite.","view_specs":"Voir les spécifications","selector_intro":"Associez type, usage, distribution, matériau, capacité, durabilité et quantité.","category_label":"Catégorie d’emballage","any_category":"Toutes catégories","use_case":"Usage","dispensing":"Mode de distribution","sustainability_goal":"Objectif durable","estimated_quantity":"Quantité estimée","manual_recommend":"Recommandation manuelle","cost_intro":"Créez une première fourchette avec les tarifs validés et les options.","product_label":"Produit","select_product":"Sélectionnez un produit","include_decoration":"Inclure la décoration","include_tooling":"Inclure l’outillage","manual_estimate":"Demander une estimation","company_name":"Entreprise","your_name":"Votre nom","work_email":"E-mail professionnel","phone":"Téléphone / WhatsApp","country":"Pays","product_needed":"Produit recherché","timeline":"Délai cible","project_details":"Détails du projet","reference_file":"Image ou PDF de référence","consent_text":"J’accepte l’utilisation de mes données et pièces jointes pour répondre à cette demande.","privacy_title":"Utilisation des informations du projet.","privacy_intro":"Les données servent uniquement à évaluer, conseiller, chiffrer et livrer le projet. Nous ne vendons aucune coordonnée.","cookie_title":"Choix de confidentialité","cookie_body":"Les statistiques facultatives ne sont chargées qu’après votre accord.","essential_only":"Essentiels uniquement","accept_analytics":"Accepter les statistiques"},
    "de": {
        "products_intro":"Spezifikationen, Veredelung und Produktion für schnellere Entscheidungen.","view_specs":"Spezifikationen ansehen","selector_intro":"Verpackungsart, Anwendung, Dosierung, Material, Volumen, Nachhaltigkeit und Menge abgleichen.","category_label":"Verpackungskategorie","any_category":"Alle Kategorien","use_case":"Anwendung","dispensing":"Dosiersystem","sustainability_goal":"Nachhaltigkeitsziel","estimated_quantity":"Geschätzte Menge","manual_recommend":"Manuelle Empfehlung","cost_intro":"Erstellen Sie eine erste Spanne aus freigegebenen Preisen und Optionen.","product_label":"Produkt","select_product":"Produkt auswählen","include_decoration":"Veredelung einbeziehen","include_tooling":"Werkzeugkosten einbeziehen","manual_estimate":"Manuelle Kalkulation","company_name":"Unternehmen","your_name":"Ihr Name","work_email":"Geschäftliche E-Mail","phone":"Telefon / WhatsApp","country":"Land","product_needed":"Gesuchtes Produkt","timeline":"Zieltermin","project_details":"Projektdetails","reference_file":"Referenzbild oder PDF","consent_text":"Ich stimme der Nutzung meiner Daten und Anhänge zur Beantwortung dieser Anfrage zu.","privacy_title":"So verwenden wir Projektinformationen.","privacy_intro":"Daten werden nur für Bewertung, Empfehlung, Angebot und Lieferung verwendet. Kontaktdaten werden nicht verkauft.","cookie_title":"Datenschutzauswahl","cookie_body":"Optionale Analysen laden wir erst nach Ihrer Zustimmung.","essential_only":"Nur erforderlich","accept_analytics":"Analyse akzeptieren"},
    "ar": {
        "products_intro":"المواصفات وخيارات التخصيص والإنتاج لاتخاذ قرار أسرع.","view_specs":"عرض المواصفات","selector_intro":"طابق النوع والاستخدام ونظام التوزيع والمادة والسعة والاستدامة والكمية.","category_label":"فئة العبوة","any_category":"كل الفئات","use_case":"الاستخدام","dispensing":"نظام التوزيع","sustainability_goal":"هدف الاستدامة","estimated_quantity":"الكمية المتوقعة","manual_recommend":"توصية يدوية","cost_intro":"أنشئ نطاقاً أولياً وفق الأسعار المعتمدة والتكاليف الاختيارية.","product_label":"المنتج","select_product":"اختر منتجاً","include_decoration":"إضافة الزخرفة","include_tooling":"إضافة تكلفة القالب","manual_estimate":"طلب تقدير يدوي","company_name":"اسم الشركة","your_name":"الاسم","work_email":"البريد المهني","phone":"الهاتف / واتساب","country":"الدولة","product_needed":"المنتج المطلوب","timeline":"الموعد المستهدف","project_details":"تفاصيل المشروع","reference_file":"صورة أو PDF مرجعي","consent_text":"أوافق على استخدام بياناتي ومرفقاتي للرد على هذا الطلب.","privacy_title":"كيفية استخدام معلومات المشروع.","privacy_intro":"نستخدم المعلومات للتقييم والتوصية والتسعير والتنفيذ فقط، ولا نبيع بيانات الاتصال.","cookie_title":"خيارات الخصوصية","cookie_body":"لا يتم تحميل التحليلات الاختيارية إلا بعد موافقتك.","essential_only":"الضروري فقط","accept_analytics":"قبول التحليلات"},
    "ja": {
        "products_intro":"仕様・カスタマイズ・生産情報を確認し、判断を迅速化します。","view_specs":"仕様を見る","selector_intro":"容器タイプ、用途、吐出方式、素材、容量、環境目標、数量から照合します。","category_label":"容器カテゴリー","any_category":"すべて","use_case":"用途","dispensing":"吐出方式","sustainability_goal":"環境目標","estimated_quantity":"予定数量","manual_recommend":"担当者に相談","cost_intro":"承認済み価格帯と追加費用から初期予算を算出します。","product_label":"製品","select_product":"製品を選択","include_decoration":"加飾費を含む","include_tooling":"金型費を含む","manual_estimate":"個別見積りを依頼","company_name":"会社名","your_name":"お名前","work_email":"業務用メール","phone":"電話 / WhatsApp","country":"国・地域","product_needed":"希望製品","timeline":"希望時期","project_details":"プロジェクト詳細","reference_file":"参考画像またはPDF","consent_text":"本依頼への回答のため、情報と添付資料が使用されることに同意します。","privacy_title":"プロジェクト情報の利用について。","privacy_intro":"情報は評価、提案、見積り、納品のためだけに使用し、連絡先を販売しません。","cookie_title":"プライバシー設定","cookie_body":"任意のアクセス解析は同意後にのみ読み込まれます。","essential_only":"必須のみ","accept_analytics":"解析に同意"},
    "ko": {
        "products_intro":"사양, 맞춤 제작 및 생산 정보를 확인해 더 빠르게 결정하세요.","view_specs":"사양 보기","selector_intro":"용기 유형, 용도, 토출 방식, 소재, 용량, 친환경 목표와 수량을 매칭합니다.","category_label":"패키지 카테고리","any_category":"전체","use_case":"용도","dispensing":"토출 방식","sustainability_goal":"친환경 목표","estimated_quantity":"예상 수량","manual_recommend":"담당자 추천 받기","cost_intro":"승인된 가격 구간과 선택 비용으로 초기 예산 범위를 계산합니다.","product_label":"제품","select_product":"제품 선택","include_decoration":"후가공 포함","include_tooling":"금형비 포함","manual_estimate":"수동 견적 요청","company_name":"회사명","your_name":"이름","work_email":"업무 이메일","phone":"전화 / WhatsApp","country":"국가","product_needed":"필요 제품","timeline":"희망 일정","project_details":"프로젝트 상세","reference_file":"참고 이미지 또는 PDF","consent_text":"문의 답변을 위해 정보와 첨부 자료를 사용하는 데 동의합니다.","privacy_title":"프로젝트 정보 이용 안내.","privacy_intro":"정보는 평가, 추천, 견적 및 납품에만 사용하며 연락처를 판매하지 않습니다.","cookie_title":"개인정보 선택","cookie_body":"선택적 분석 기능은 동의 후에만 로드됩니다.","essential_only":"필수 기능만","accept_analytics":"분석 동의"},
    "ru": {
        "products_intro":"Характеристики, персонализация и производство для быстрых решений.","view_specs":"Смотреть характеристики","selector_intro":"Сопоставьте тип, применение, дозирование, материал, объём, экологичность и тираж.","category_label":"Категория упаковки","any_category":"Все категории","use_case":"Применение","dispensing":"Способ дозирования","sustainability_goal":"Экологическая цель","estimated_quantity":"Планируемый тираж","manual_recommend":"Рекомендация специалиста","cost_intro":"Рассчитайте начальный диапазон по утверждённым ценам и опциям.","product_label":"Продукт","select_product":"Выберите продукт","include_decoration":"Включить декор","include_tooling":"Включить оснастку","manual_estimate":"Запросить ручной расчёт","company_name":"Компания","your_name":"Ваше имя","work_email":"Рабочая почта","phone":"Телефон / WhatsApp","country":"Страна","product_needed":"Нужный продукт","timeline":"Желаемый срок","project_details":"Описание проекта","reference_file":"Референс или PDF","consent_text":"Я согласен на использование данных и вложений для ответа на запрос.","privacy_title":"Как используются данные проекта.","privacy_intro":"Данные используются только для оценки, рекомендаций, расчёта и поставки. Мы не продаём контакты.","cookie_title":"Настройки конфиденциальности","cookie_body":"Необязательная аналитика загружается только после согласия.","essential_only":"Только необходимые","accept_analytics":"Разрешить аналитику"},
}
for _language, _labels in FULL_UI.items():
    TRANSLATIONS[_language].update(_labels)

PRIVACY_UI = {
"en":["Information collected","Company and contact details, requirements, quantities, market, timing, reference files and communication records.","Purpose and legal basis","Project evaluation and requested pre-contract service, delivery, compliance and legitimate service improvement.","Retention and access","Access is restricted to authorized personnel. Data is retained only for legitimate business and compliance needs, then securely deleted.","Your choices","Optional analytics load only after consent. Contact us to request access, correction or deletion where applicable."],
"zh":["收集的信息","公司与联系人资料、产品需求、数量、市场、时间、参考文件及沟通记录。","用途与法律依据","项目评估、客户主动请求的合同前服务、订单交付、合规以及合理的服务改进。","保存与访问","仅授权人员可以访问；数据只在业务与合规所需期限内保存，之后安全删除。","您的选择","可选访问统计仅在同意后加载；您可以联系我们申请访问、更正或删除相关信息。"],
"es":["Información recopilada","Datos de empresa y contacto, requisitos, cantidades, mercado, plazos, archivos y comunicaciones.","Finalidad y base legal","Evaluación, servicios precontractuales solicitados, entrega, cumplimiento y mejora legítima.","Conservación y acceso","Solo accede personal autorizado. Los datos se conservan el tiempo necesario y luego se eliminan de forma segura.","Sus opciones","La analítica opcional requiere consentimiento. Puede solicitar acceso, corrección o eliminación."],
"pt":["Informações coletadas","Dados da empresa e contato, requisitos, quantidades, mercado, prazos, arquivos e comunicações.","Finalidade e base legal","Avaliação, serviço pré-contratual solicitado, entrega, conformidade e melhoria legítima.","Retenção e acesso","Somente pessoal autorizado acessa os dados, mantidos pelo período necessário e depois excluídos com segurança.","Suas escolhas","A análise opcional exige consentimento. Você pode solicitar acesso, correção ou exclusão."],
"fr":["Informations collectées","Coordonnées, besoins, quantités, marché, délais, fichiers de référence et échanges.","Finalité et base légale","Évaluation, service précontractuel demandé, livraison, conformité et amélioration légitime.","Conservation et accès","Accès limité au personnel autorisé; les données sont conservées le temps nécessaire puis supprimées de manière sécurisée.","Vos choix","Les statistiques facultatives exigent votre accord. Vous pouvez demander accès, rectification ou suppression."],
"de":["Erhobene Daten","Unternehmens- und Kontaktdaten, Anforderungen, Mengen, Markt, Termine, Referenzdateien und Kommunikation.","Zweck und Rechtsgrundlage","Bewertung, angefragte vorvertragliche Leistung, Lieferung, Compliance und berechtigte Verbesserung.","Speicherung und Zugriff","Nur autorisierte Personen haben Zugriff. Daten werden nur so lange wie nötig gespeichert und danach sicher gelöscht.","Ihre Wahl","Optionale Analysen erfordern Zustimmung. Sie können Auskunft, Berichtigung oder Löschung anfordern."],
"ar":["المعلومات التي نجمعها","بيانات الشركة والاتصال والمتطلبات والكميات والسوق والتوقيت والملفات وسجلات التواصل.","الغرض والأساس القانوني","التقييم والخدمة المطلوبة قبل التعاقد والتسليم والامتثال وتحسين الخدمة المشروع.","الحفظ والوصول","يقتصر الوصول على الموظفين المخولين، وتُحذف البيانات بأمان بعد انتهاء الحاجة التجارية والنظامية.","خياراتك","لا تعمل التحليلات الاختيارية دون موافقتك، ويمكنك طلب الوصول أو التصحيح أو الحذف."],
"ja":["収集する情報","会社・連絡先、製品要件、数量、市場、時期、参考資料、連絡履歴。","利用目的と法的根拠","評価、依頼された契約前対応、納品、法令順守、正当なサービス改善。","保存とアクセス","権限のある担当者のみがアクセスし、必要期間後に安全に削除します。","お客様の選択","任意の解析には同意が必要です。開示、訂正、削除を依頼できます。"],
"ko":["수집 정보","회사 및 연락처, 제품 요구사항, 수량, 시장, 일정, 참고 파일과 상담 기록.","목적 및 법적 근거","평가, 요청된 계약 전 서비스, 납품, 규정 준수와 정당한 서비스 개선.","보관 및 접근","승인된 담당자만 접근하며 필요한 기간 이후 안전하게 삭제합니다.","사용자 선택","선택적 분석은 동의 후 작동하며 열람, 수정 또는 삭제를 요청할 수 있습니다."],
"ru":["Собираемые данные","Сведения о компании и контактах, требования, тираж, рынок, сроки, файлы и переписка.","Цель и правовое основание","Оценка, запрошенная преддоговорная услуга, поставка, соблюдение требований и улучшение сервиса.","Хранение и доступ","Доступ имеют только уполномоченные сотрудники; после необходимого срока данные безопасно удаляются.","Ваш выбор","Необязательная аналитика требует согласия. Можно запросить доступ, исправление или удаление."]
}
for _language, _values in PRIVACY_UI.items():
    for _key, _value in zip(("privacy_collected","privacy_collected_body","privacy_purpose","privacy_purpose_body","privacy_retention","privacy_retention_body","privacy_choices_heading","privacy_choices_body"), _values):
        TRANSLATIONS[_language][_key] = _value


def register_v4(app, get_db, login_required, now, audit, upload_folder):
    public_endpoints = {
        "public_home": "localized_home", "localized_home": "localized_home",
        "public_products": "localized_products", "localized_products": "localized_products",
        "public_product": "localized_product_v4", "localized_product_v4": "localized_product_v4",
        "packaging_selector": "localized_selector", "localized_selector": "localized_selector",
        "cost_estimator": "localized_cost_estimator", "localized_cost_estimator": "localized_cost_estimator",
        "request_quote": "localized_request_quote", "localized_request_quote": "localized_request_quote",
        "privacy": "localized_privacy", "localized_privacy": "localized_privacy",
    }

    with app.app_context():
        db = get_db()
        db.execute("""CREATE TABLE IF NOT EXISTS content_versions (
            id INTEGER PRIMARY KEY, language TEXT NOT NULL, payload TEXT NOT NULL,
            created_by TEXT, created_at TEXT NOT NULL
        )""")
        db.commit()

    def current_language():
        requested = (
            (request.view_args or {}).get("language")
            or request.args.get("lang")
            or request.form.get("lang")
        )
        if requested in LANGUAGE_LABELS:
            session["public_language"] = requested
        saved = session.get("public_language", "en")
        return saved if saved in LANGUAGE_LABELS else "en"

    def localized_product_rows(db, language, category=None, limit=None):
        sql = "SELECT * FROM products WHERE published=1"
        params = []
        if category:
            sql += " AND category=?"
            params.append(category)
        sql += " ORDER BY featured DESC,id DESC"
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        products = [dict(row) for row in db.execute(sql, params).fetchall()]
        if language != "en" and products:
            ids = [item["id"] for item in products]
            placeholders = ",".join("?" for _ in ids)
            rows = db.execute(
                f"SELECT * FROM product_translations WHERE language=? AND status='已批准' AND product_id IN ({placeholders})",
                [language, *ids]
            ).fetchall()
            translations = {row["product_id"]: row for row in rows}
            for item in products:
                translated = translations.get(item["id"])
                item["display_name"] = translated["name"] if translated and translated["name"] else item["name"]
                item["display_summary"] = translated["summary"] if translated and translated["summary"] else item["summary"]
        else:
            for item in products:
                item["display_name"] = item["name"]
                item["display_summary"] = item["summary"]
        return products

    def settings_map(db):
        return {row["key"]: row["value"] for row in db.execute("SELECT key,value FROM settings WHERE key LIKE 'site_%' OR key LIKE 'draft_site_%'")}

    def default_content(language):
        defaults = {**CONTENT_DEFAULTS["en"], **CONTENT_DEFAULTS.get(language, {})}
        labels = TRANSLATIONS.get(language, TRANSLATIONS["en"])
        for field, translation_key in CONTENT_TRANSLATION_MAP.items():
            if labels.get(translation_key):
                defaults[field] = labels[translation_key]
        return defaults

    def load_content(db, language, draft=False):
        values = settings_map(db)
        defaults = default_content(language)
        content = {}
        for field in CONTENT_FIELDS:
            live = values.get(f"site_{language}_{field}", values.get(f"site_en_{field}", defaults[field]))
            content[field] = values.get(f"draft_site_{language}_{field}", live) if draft else live
        content["video_file"] = values.get("draft_site_video_file", values.get("site_video_file", "")) if draft else values.get("site_video_file", "")
        content["video_url"] = values.get("draft_site_video_url", values.get("site_video_url", "")) if draft else values.get("site_video_url", "")
        return content

    def set_setting(db, key, value):
        db.execute(
            """INSERT INTO settings(key,value,updated_at) VALUES(?,?,?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",
            (key, value, now())
        )

    def lurl(endpoint, **values):
        language = values.pop("language", current_language())
        target = public_endpoints.get(endpoint)
        if target:
            return url_for(target, language=language, **values)
        return url_for(endpoint, **values)

    def language_url(language):
        endpoint = request.endpoint or "public_home"
        target = public_endpoints.get(endpoint, "localized_home")
        values = dict(request.view_args or {})
        values.pop("language", None)
        for key in ("category", "product"):
            if request.args.get(key):
                values[key] = request.args[key]
        return url_for(target, language=language, **values)

    @app.context_processor
    def v4_public_context():
        language = current_language()
        return {
            "current_language": language,
            "language_labels": LANGUAGE_LABELS,
            "t": TRANSLATIONS.get(language, TRANSLATIONS["en"]),
            "site": load_content(get_db(), language),
            "lurl": lurl,
            "language_url": language_url,
            "canonical_url": request.url_root.rstrip("/") + language_url(language),
        }

    @app.before_request
    def redirect_legacy_public_urls():
        legacy = {
            "public_home": "localized_home",
            "public_products": "localized_products",
            "public_product": "localized_product_v4",
            "packaging_selector": "localized_selector",
            "cost_estimator": "localized_cost_estimator",
            "request_quote": "localized_request_quote",
            "privacy": "localized_privacy",
        }
        target = legacy.get(request.endpoint)
        if not target:
            return None
        language = request.args.get("lang")
        if language not in LANGUAGE_LABELS:
            language = session.get("public_language", "en")
        if language not in LANGUAGE_LABELS:
            language = "en"
        values = dict(request.view_args or {})
        query = request.args.to_dict(flat=True)
        query.pop("lang", None)
        values.update(query)
        return redirect(url_for(target, language=language, **values), code=308 if request.method != "GET" else 301)

    def normalize_video_url(value):
        value = (value or "").strip()
        if not value:
            return ""
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("视频地址必须以 http:// 或 https:// 开头")
        host = parsed.netloc.lower()
        if host in {"www.youtube.com", "youtube.com", "m.youtube.com"} and parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
            if video_id:
                return f"https://www.youtube.com/embed/{video_id}"
        if host in {"youtu.be", "www.youtu.be"} and parsed.path.strip("/"):
            return f"https://www.youtube.com/embed/{parsed.path.strip('/')}"
        if host in {"vimeo.com", "www.vimeo.com"} and parsed.path.strip("/").isdigit():
            return f"https://player.vimeo.com/video/{parsed.path.strip('/')}"
        if parsed.path.lower().endswith((".mp4", ".mov", ".webm")):
            return value
        if (host in {"www.youtube.com", "youtube.com"} and "/embed/" in parsed.path) or (host == "player.vimeo.com" and "/video/" in parsed.path):
            return value
        raise ValueError("仅支持 YouTube、Vimeo 或 HTTPS 直链视频")

    def validate_video(file):
        extension = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if extension not in {"mp4", "mov", "webm"}:
            raise ValueError("视频仅支持 MP4、MOV 或 WEBM")
        file.stream.seek(0, 2)
        size = file.stream.tell()
        file.stream.seek(0)
        if size <= 0 or size > 100 * 1024 * 1024:
            raise ValueError("视频必须小于100兆")
        head = file.stream.read(16)
        file.stream.seek(0)
        valid = (extension in {"mp4", "mov"} and len(head) >= 12 and head[4:8] == b"ftyp") or (extension == "webm" and head.startswith(b"\x1a\x45\xdf\xa3"))
        if not valid:
            raise ValueError("视频内容与扩展名不一致")
        return extension

    def remove_upload(filename):
        if not filename:
            return
        path = Path(upload_folder) / Path(filename).name
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass

    @app.route("/admin/content", methods=["GET", "POST"])
    @login_required
    def content_admin():
        if session.get("role") not in {"管理员", "海外负责人", "内容运营"}:
            abort(403, "当前岗位没有网站内容管理权限")
        db = get_db()
        language = request.form.get("language") or request.args.get("language") or "en"
        selected_page = request.form.get("page") or request.args.get("page") or "home"
        if language not in LANGUAGE_LABELS:
            language = "en"
        if selected_page not in CONTENT_PAGES:
            selected_page = "home"
        fields = page_field_names(selected_page)
        if request.method == "POST":
            action = request.form.get("action", "draft")
            if action not in {"draft", "publish"}:
                abort(400)
            prefix = "site" if action == "publish" else "draft_site"
            for field in fields:
                set_setting(db, f"{prefix}_{language}_{field}", request.form.get(field, "").strip())
            if selected_page == "home":
                try:
                    video_url = normalize_video_url(request.form.get("video_url"))
                    video = request.files.get("video")
                    if video and video.filename:
                        extension = validate_video(video)
                        old = load_content(db, language, draft=True).get("video_file")
                        filename = f"home-{secrets.token_hex(8)}.{extension}"
                        video.save(Path(upload_folder) / filename)
                        set_setting(db, "draft_site_video_file", filename)
                        if action == "publish":
                            set_setting(db, "site_video_file", filename)
                        if old and old != filename:
                            remove_upload(old)
                    if request.form.get("remove_video"):
                        old = load_content(db, language, draft=True).get("video_file")
                        set_setting(db, "draft_site_video_file", "")
                        if action == "publish":
                            set_setting(db, "site_video_file", "")
                        remove_upload(old)
                    set_setting(db, "draft_site_video_url", video_url)
                    if action == "publish":
                        current_draft_video = load_content(db, language, draft=True).get("video_file", "")
                        set_setting(db, "site_video_file", current_draft_video)
                        set_setting(db, "site_video_url", video_url)
                except ValueError as exc:
                    db.rollback()
                    flash(str(exc), "error")
                    params = {"language": language}
                    if selected_page != "home":
                        params["page"] = selected_page
                    return redirect(url_for("content_admin", **params))
            if action == "publish":
                for field in fields:
                    value = request.form.get(field, "").strip()
                    set_setting(db, f"site_{language}_{field}", value)
                    set_setting(db, f"draft_site_{language}_{field}", value)
                snapshot = load_content(db, language, draft=True)
                db.execute(
                    "INSERT INTO content_versions(language,payload,created_by,created_at) VALUES(?,?,?,?)",
                    (language, json.dumps(snapshot, ensure_ascii=False), session.get("username"), now())
                )
                audit("发布海外网站内容", "settings", detail=f"页面：{CONTENT_PAGES[selected_page]['label']}；语言：{LANGUAGE_LABELS[language]}")
                message = f"{CONTENT_PAGES[selected_page]['label']}已发布到正式网站"
            else:
                audit("保存网站内容草稿", "settings", detail=f"页面：{CONTENT_PAGES[selected_page]['label']}；语言：{LANGUAGE_LABELS[language]}")
                message = f"{CONTENT_PAGES[selected_page]['label']}草稿已保存，可先预览再发布"
            db.commit()
            flash(message, "success")
            params = {"language": language}
            if selected_page != "home":
                params["page"] = selected_page
            return redirect(url_for("content_admin", **params))
        draft_content = load_content(db, language, draft=True)
        live_content = load_content(db, language)
        page_status = {}
        for page_key in CONTENT_PAGES:
            page_fields = page_field_names(page_key)
            page_status[page_key] = {
                "filled": sum(bool(draft_content.get(field)) for field in page_fields),
                "total": len(page_fields),
                "changed": any(draft_content.get(field) != live_content.get(field) for field in page_fields),
            }
        versions = db.execute("SELECT * FROM content_versions WHERE language=? ORDER BY id DESC LIMIT 8", (language,)).fetchall()
        return render_template(
            "admin/content.html", languages=LANGUAGE_LABELS, selected_language=language,
            selected_page=selected_page, pages=CONTENT_PAGES, page=CONTENT_PAGES[selected_page],
            content=draft_content, page_status=page_status, versions=versions
        )

    @app.get("/admin/content/preview/<language>")
    @app.get("/admin/content/preview/<language>/<page>")
    @login_required
    def content_preview(language, page="home"):
        if session.get("role") not in {"管理员", "海外负责人", "内容运营"} or language not in LANGUAGE_LABELS:
            abort(403)
        if page not in CONTENT_PAGES:
            abort(404)
        db = get_db()
        draft = load_content(db, language, draft=True)
        if page in {"home", "solutions", "capabilities"}:
            products = localized_product_rows(db, language, limit=8)
            return render_template("public/home.html", products=products, site=draft, current_language=language, preview_mode=True)
        if page == "products":
            categories = db.execute("SELECT DISTINCT category FROM products WHERE published=1 AND category!='' ORDER BY category").fetchall()
            return render_template(
                "public/products.html", products=localized_product_rows(db, language),
                categories=categories, active_category="", site=draft,
                current_language=language, preview_mode=True
            )
        if page == "selector":
            categories = db.execute("SELECT DISTINCT category FROM products WHERE published=1 AND category!='' ORDER BY category").fetchall()
            count = db.execute("SELECT COUNT(*) n FROM products WHERE published=1").fetchone()["n"]
            form_data = {"category":"","capacity":"","material":"","use_case":"","dispensing":"","sustainability":"","quantity":"10000"}
            return render_template(
                "public/selector.html", results=[], categories=categories, submitted=False,
                has_products=bool(count), form_data=form_data, site=draft,
                current_language=language, preview_mode=True
            )
        products = db.execute(
            """SELECT p.id,p.name,p.moq,p.name localized_name FROM products p
               JOIN quote_rules q ON q.product_id=p.id
               WHERE p.published=1 AND q.active=1 ORDER BY p.name"""
        ).fetchall()
        return render_template(
            "public/cost_estimator.html", products=products, result=None, submitted=False,
            has_products=bool(products), form_data={"product_id":"","quantity":"10000","include_decoration":False,"include_tooling":False},
            site=draft, current_language=language, preview_mode=True
        )

    @app.post("/admin/content/restore/<int:version_id>")
    @login_required
    def restore_content(version_id):
        if session.get("role") not in {"管理员", "海外负责人", "内容运营"}:
            abort(403)
        db = get_db()
        version = db.execute("SELECT * FROM content_versions WHERE id=?", (version_id,)).fetchone()
        if not version:
            abort(404)
        payload = json.loads(version["payload"])
        for field in CONTENT_FIELDS:
            if field in payload:
                set_setting(db, f"draft_site_{version['language']}_{field}", payload[field])
        if "video_file" in payload:
            set_setting(db, "draft_site_video_file", payload["video_file"])
        if "video_url" in payload:
            set_setting(db, "draft_site_video_url", payload["video_url"])
        audit("恢复网站内容版本", "content_version", version_id)
        db.commit()
        flash("历史版本已恢复为草稿，请预览后发布", "success")
        return redirect(url_for("content_admin", language=version["language"]))

    @app.route("/<language>/", methods=["GET"])
    def localized_home(language):
        if language not in LANGUAGE_LABELS:
            abort(404)
        return render_template("public/home.html", products=localized_product_rows(get_db(), language, limit=8))

    @app.route("/<language>/products", methods=["GET"])
    def localized_products(language):
        if language not in LANGUAGE_LABELS:
            abort(404)
        db = get_db()
        category = request.args.get("category", "")
        categories = db.execute("SELECT DISTINCT category FROM products WHERE published=1 AND category!='' ORDER BY category").fetchall()
        return render_template(
            "public/products.html",
            products=localized_product_rows(db, language, category=category or None),
            categories=categories,
            active_category=category,
        )

    @app.route("/<language>/products/<slug>", methods=["GET"])
    def localized_product_v4(language, slug):
        if language not in LANGUAGE_LABELS:
            abort(404)
        db = get_db()
        product = db.execute("SELECT * FROM products WHERE slug=? AND published=1", (slug,)).fetchone()
        if not product:
            abort(404)
        translated = None
        if language != "en":
            translated = db.execute("SELECT * FROM product_translations WHERE product_id=? AND language=? AND status='已批准'", (product["id"], language)).fetchone()
        display = {
            "name": translated["name"] if translated and translated["name"] else product["name"],
            "summary": translated["summary"] if translated and translated["summary"] else product["summary"],
            "description": translated["description"] if translated and translated["description"] else product["description"],
            "decoration": translated["decoration"] if translated and translated["decoration"] else product["decoration"],
            "sustainability": translated["sustainability"] if translated and translated["sustainability"] else product["sustainability"],
        }
        translations = db.execute("SELECT language FROM product_translations WHERE product_id=? AND status='已批准'", (product["id"],)).fetchall()
        return render_template("public/product.html", product=product, display=display, translations=translations)

    @app.route("/<language>/packaging-selector", methods=["GET", "POST"])
    def localized_selector(language):
        if language not in LANGUAGE_LABELS:
            abort(404)
        return app.view_functions["packaging_selector"]()

    @app.route("/<language>/cost-estimator", methods=["GET", "POST"])
    def localized_cost_estimator(language):
        if language not in LANGUAGE_LABELS:
            abort(404)
        return app.view_functions["cost_estimator"]()

    @app.route("/<language>/request-quote", methods=["GET", "POST"])
    def localized_request_quote(language):
        if language not in LANGUAGE_LABELS:
            abort(404)
        return app.view_functions["request_quote"]()

    @app.route("/<language>/privacy", methods=["GET"])
    def localized_privacy(language):
        if language not in LANGUAGE_LABELS:
            abort(404)
        return app.view_functions["privacy"]()
