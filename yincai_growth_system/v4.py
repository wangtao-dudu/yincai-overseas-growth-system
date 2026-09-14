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
    },
}

CONTENT_FIELDS = (
    "hero_kicker", "hero_title", "hero_body",
    "metric_1_value", "metric_1_label", "metric_2_value", "metric_2_label",
    "metric_3_value", "metric_3_label", "video_title", "video_body",
    "cta_title", "cta_body",
)



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

    def settings_map(db):
        return {row["key"]: row["value"] for row in db.execute("SELECT key,value FROM settings WHERE key LIKE 'site_%' OR key LIKE 'draft_site_%'")}

    def default_content(language):
        return {**CONTENT_DEFAULTS["en"], **CONTENT_DEFAULTS.get(language, {})}

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
            "canonical_url": request.base_url,
        }

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
        if language not in LANGUAGE_LABELS:
            language = "en"
        if request.method == "POST":
            action = request.form.get("action", "draft")
            prefix = "site" if action == "publish" else "draft_site"
            for field in CONTENT_FIELDS:
                set_setting(db, f"{prefix}_{language}_{field}", request.form.get(field, "").strip())
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
                return redirect(url_for("content_admin", language=language))
            if action == "publish":
                for field in CONTENT_FIELDS:
                    set_setting(db, f"site_{language}_{field}", request.form.get(field, "").strip())
                    set_setting(db, f"draft_site_{language}_{field}", request.form.get(field, "").strip())
                snapshot = load_content(db, language, draft=True)
                db.execute(
                    "INSERT INTO content_versions(language,payload,created_by,created_at) VALUES(?,?,?,?)",
                    (language, json.dumps(snapshot, ensure_ascii=False), session.get("username"), now())
                )
                audit("发布海外网站内容", "settings", detail=f"语言：{LANGUAGE_LABELS[language]}")
                message = "内容已发布到正式网站"
            else:
                audit("保存网站内容草稿", "settings", detail=f"语言：{LANGUAGE_LABELS[language]}")
                message = "草稿已保存，可先预览再发布"
            db.commit()
            flash(message, "success")
            return redirect(url_for("content_admin", language=language))
        versions = db.execute("SELECT * FROM content_versions WHERE language=? ORDER BY id DESC LIMIT 8", (language,)).fetchall()
        return render_template("admin/content.html", languages=LANGUAGE_LABELS, selected_language=language, content=load_content(db, language, draft=True), versions=versions)

    @app.get("/admin/content/preview/<language>")
    @login_required
    def content_preview(language):
        if session.get("role") not in {"管理员", "海外负责人", "内容运营"} or language not in LANGUAGE_LABELS:
            abort(403)
        products = get_db().execute("SELECT * FROM products WHERE published=1 ORDER BY featured DESC,id DESC LIMIT 8").fetchall()
        return render_template("public/home.html", products=products, site=load_content(get_db(), language, draft=True), current_language=language, preview_mode=True)

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
            set_setting(db, f"draft_site_{version['language']}_{field}", payload.get(field, ""))
        set_setting(db, "draft_site_video_file", payload.get("video_file", ""))
        set_setting(db, "draft_site_video_url", payload.get("video_url", ""))
        audit("恢复网站内容版本", "content_version", version_id)
        db.commit()
        flash("历史版本已恢复为草稿，请预览后发布", "success")
        return redirect(url_for("content_admin", language=version["language"]))

    @app.route("/<language>/", methods=["GET"])
    def localized_home(language):
        if language not in LANGUAGE_LABELS:
            abort(404)
        return app.view_functions["public_home"]()

    @app.route("/<language>/products", methods=["GET"])
    def localized_products(language):
        if language not in LANGUAGE_LABELS:
            abort(404)
        return app.view_functions["public_products"]()

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
