import secrets
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


def register_v4(app, get_db, login_required, now, audit, upload_folder):
    def current_language():
        requested = request.args.get("lang") or request.form.get("lang")
        if requested in LANGUAGE_LABELS:
            session["public_language"] = requested
        return session.get("public_language", "en") if session.get("public_language") in LANGUAGE_LABELS else "en"

    def setting_value(db, key, default=""):
        row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row and row["value"] is not None else default

    def default_content(language):
        return {**CONTENT_DEFAULTS["en"], **CONTENT_DEFAULTS.get(language, {})}

    def load_content(db, language):
        defaults = default_content(language)
        content = {}
        for field in CONTENT_FIELDS:
            content[field] = setting_value(
                db, f"site_{language}_{field}",
                setting_value(db, f"site_en_{field}", defaults[field])
            )
        content["video_file"] = setting_value(db, "site_video_file")
        content["video_url"] = setting_value(db, "site_video_url")
        return content

    @app.context_processor
    def v4_public_context():
        language = current_language()
        return {
            "current_language": language,
            "language_labels": LANGUAGE_LABELS,
            "t": TRANSLATIONS.get(language, EN),
            "site": load_content(get_db(), language),
        }

    def normalize_video_url(value):
        value = (value or "").strip()
        if not value:
            return ""
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("视频地址必须以 http:// 或 https:// 开头")
        host = parsed.netloc.lower()
        if "youtube.com" in host and parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
            return f"https://www.youtube.com/embed/{video_id}" if video_id else value
        if "youtu.be" in host:
            return f"https://www.youtube.com/embed/{parsed.path.strip('/')}"
        return value

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
            for field in CONTENT_FIELDS:
                key = f"site_{language}_{field}"
                db.execute(
                    """INSERT INTO settings(key,value,updated_at) VALUES(?,?,?)
                       ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",
                    (key, request.form.get(field, "").strip(), now())
                )
            try:
                video_url = normalize_video_url(request.form.get("video_url"))
            except ValueError as exc:
                flash(str(exc), "error")
                return redirect(url_for("content_admin", language=language))
            db.execute(
                """INSERT INTO settings(key,value,updated_at) VALUES('site_video_url',?,?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",
                (video_url, now())
            )
            video = request.files.get("video")
            if video and video.filename:
                extension = video.filename.rsplit(".", 1)[-1].lower() if "." in video.filename else ""
                if extension not in {"mp4", "mov", "webm"}:
                    flash("视频仅支持 MP4、MOV 或 WEBM", "error")
                    return redirect(url_for("content_admin", language=language))
                filename = f"home-{secrets.token_hex(8)}.{extension}"
                video.save(upload_folder / filename)
                db.execute(
                    """INSERT INTO settings(key,value,updated_at) VALUES('site_video_file',?,?)
                       ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",
                    (filename, now())
                )
            if request.form.get("remove_video"):
                db.execute(
                    """INSERT INTO settings(key,value,updated_at) VALUES('site_video_file','',?)
                       ON CONFLICT(key) DO UPDATE SET value='',updated_at=excluded.updated_at""",
                    (now(),)
                )
            audit("更新海外网站内容", "settings", detail=f"语言：{LANGUAGE_LABELS[language]}")
            db.commit()
            flash("网站内容已保存，刷新前台即可查看", "success")
            return redirect(url_for("content_admin", language=language))
        return render_template(
            "admin/content.html", languages=LANGUAGE_LABELS,
            selected_language=language, content=load_content(db, language)
        )
