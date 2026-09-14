import json
import os
import re
import shutil
import sqlite3
import urllib.request
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import abort, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import generate_password_hash


LANGUAGES = {"zh": "简体中文", "de": "德语", "fr": "法语", "es": "西班牙语", "pt": "葡萄牙语", "ar": "阿拉伯语", "ja": "日语", "ko": "韩语", "ru": "俄语"}
ACTIVE_STAGES = {"目标企业", "有效联系人", "合格线索", "正式询价", "样品项目", "正式报价", "试单", "批量订单"}


def register_features(app, get_db, login_required, now, audit, db_path, upload_folder):
    permissions = {
        "海外负责人": {"dashboard", "acquisition", "companies", "opportunities", "operations", "inquiries", "quality", "distributors", "intelligence", "translations", "catalog", "content"},
        "销售": {"dashboard", "acquisition", "companies", "opportunities", "operations", "inquiries", "intelligence"},
        "产品技术": {"dashboard", "catalog", "translations", "intelligence"},
        "质量": {"dashboard", "quality", "catalog", "operations"},
        "内容运营": {"dashboard", "catalog", "translations", "acquisition", "content"},
        "财务": {"dashboard", "operations", "intelligence"},
        "交付": {"dashboard", "operations", "quality"},
    }
    endpoint_area = {
        "dashboard": "dashboard", "admin_acquisition": "acquisition", "admin_companies": "companies", "company_detail": "companies",
        "admin_opportunities": "opportunities", "update_stage": "opportunities", "admin_operations": "operations", "complete_task": "operations",
        "admin_inquiries": "inquiries", "admin_products": "catalog", "edit_product": "catalog",
        "users": "users", "system_admin": "users", "quality": "quality", "distributors": "distributors",
        "intelligence": "intelligence", "translations": "translations", "catalog_rules": "catalog",
        "auto_quote": "operations", "sample_update": "operations", "record_payment": "operations",
        "reset_password": "users", "create_backup": "users", "review_translation": "translations",
        "generate_product_copy": "catalog", "content_admin": "content",
        "content_preview": "content", "restore_content": "content",
    }

    @app.before_request
    def role_guard():
        if not request.path.startswith("/admin") or request.endpoint in {"login", "logout", None}:
            return None
        if not session.get("user_id"):
            return None
        role = session.get("role", "管理员")
        if role == "管理员":
            return None
        area = endpoint_area.get(request.endpoint)
        if not area or area not in permissions.get(role, set()):
            abort(403, "当前岗位没有访问该模块的权限")
        return None

    def can_access(area):
        role = session.get("role", "管理员")
        return role == "管理员" or area in permissions.get(role, set())

    @app.context_processor
    def permission_context():
        return {"can_access": can_access}

    def admin_only(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("role") != "管理员": abort(403)
            return view(*args, **kwargs)
        return wrapped

    def parse_date(value):
        if not value: return None
        try: return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError: return None

    def calculate_company_score(db, company_id):
        company = db.execute("SELECT * FROM companies WHERE id=?", (company_id,)).fetchone()
        contacts = db.execute("SELECT * FROM contacts WHERE company_id=?", (company_id,)).fetchall()
        opportunities = db.execute("SELECT * FROM opportunities WHERE company_id=?", (company_id,)).fetchall()
        score, reasons = 5, ["已建立企业档案 +5"]
        if company["website"]: score += 10; reasons.append("有企业网站 +10")
        if company["country"] in {"美国", "英国", "德国", "法国", "阿联酋", "沙特阿拉伯", "United States", "United Kingdom", "Germany", "France", "UAE", "Saudi Arabia"}: score += 8; reasons.append("重点市场 +8")
        if company["company_type"] in {"美容品牌", "化妆品生产企业", "包装贸易商", "Beauty brand", "Cosmetic manufacturer", "Packaging distributor"}: score += 8; reasons.append("核心客户类型 +8")
        if company["annual_purchase"]: score += 8; reasons.append("已记录采购能力 +8")
        if contacts: score += 8; reasons.append("存在有效联系人 +8")
        titles = " ".join((c["title"] or "") + " " + (c["decision_role"] or "") for c in contacts).lower()
        if any(word in titles for word in ["采购", "创始", "总监", "经理", "procurement", "founder", "director", "manager"]): score += 12; reasons.append("联系人接近决策层 +12")
        if opportunities:
            best = max(opportunities, key=lambda x: x["probability"])
            score += min(25, int(best["probability"] * .25)); reasons.append(f"商机成熟度 +{min(25, int(best['probability']*.25))}")
            if best["amount"] and best["amount"] >= 10000: score += 8; reasons.append("商机金额较高 +8")
            if best["next_action_at"]: score += 5; reasons.append("下一步行动明确 +5")
        if company["risk_status"] not in {None, "正常"}: score -= 15; reasons.append("存在客户风险 -15")
        score = max(0, min(100, score))
        grade = "甲级" if score >= 75 else "乙级" if score >= 50 else "丙级" if score >= 25 else "丁级"
        db.execute("UPDATE companies SET score=?,score_reason=?,grade=?,last_scored_at=?,updated_at=? WHERE id=?", (score, "；".join(reasons), grade, now(), now(), company_id))
        return score, grade

    def calculate_risk(db, opportunity):
        reasons, points = [], 0
        updated = parse_date(opportunity["updated_at"])
        if updated and datetime.utcnow() - updated > timedelta(days=14): points += 2; reasons.append("十四天没有推进")
        next_at = parse_date(opportunity["next_action_at"])
        if not opportunity["next_action"]: points += 1; reasons.append("没有下一步行动")
        if next_at and next_at < datetime.utcnow(): points += 2; reasons.append("跟进已经逾期")
        quote = db.execute("SELECT * FROM quotes WHERE opportunity_id=? ORDER BY id DESC LIMIT 1", (opportunity["id"],)).fetchone()
        if quote and parse_date(quote["created_at"]) and datetime.utcnow() - parse_date(quote["created_at"]) > timedelta(days=14) and quote["status"] not in {"已接受", "已拒绝"}: points += 2; reasons.append("报价超过十四天未决")
        sample = db.execute("SELECT * FROM samples WHERE opportunity_id=? ORDER BY id DESC LIMIT 1", (opportunity["id"],)).fetchone()
        if sample and sample["status"] == "已签收" and not sample["feedback"]: points += 2; reasons.append("样品签收后没有反馈")
        level = "高风险" if points >= 5 else "需关注" if points >= 2 else "正常"
        db.execute("UPDATE opportunities SET risk_level=?,risk_reason=?,last_risk_check=? WHERE id=?", (level, "；".join(reasons) or "未发现明显风险", now(), opportunity["id"]))
        return level

    def recommend_products(db, category, capacity, material, quantity, use_case="", dispensing="", sustainability=""):
        language = (request.view_args or {}).get("language", "en")
        rows = db.execute(
            """SELECT p.*,q.tier1_min,q.tier2_min,q.tier3_min,
                      COALESCE(t.name,p.name) localized_name,
                      COALESCE(t.summary,p.summary) localized_summary,
                      COALESCE(t.description,p.description) localized_description
               FROM products p
               LEFT JOIN quote_rules q ON q.product_id=p.id
               LEFT JOIN product_translations t ON t.product_id=p.id AND t.language=? AND t.status='已批准'
               WHERE p.published=1""",
            (language,)
        ).fetchall()
        results = []
        requested = any((category, capacity, material, use_case, dispensing, sustainability))
        for product in rows:
            searchable = " ".join(str(product[key] or "") for key in (
                "category", "name", "summary", "description", "localized_name",
                "localized_summary", "localized_description", "material", "capacity",
                "decoration", "sustainability", "material_composition"
            )).lower()
            score, reasons = (0 if requested else 50), []
            criteria = (
                (category, 28, "产品类型匹配"),
                (capacity, 22, "容量匹配"),
                (material, 18, "材料匹配"),
                (use_case, 12, "使用场景匹配"),
                (dispensing, 10, "出料方式匹配"),
                (sustainability, 10, "环保目标匹配"),
            )
            for value, weight, reason in criteria:
                if value and value.lower() in searchable:
                    score += weight
                    reasons.append(reason)
            minimum = product["tier1_min"] or 0
            if not minimum and product["moq"]:
                match = re.search(r"[\d,]+", str(product["moq"]))
                minimum = int(match.group(0).replace(",", "")) if match else 0
            if quantity and minimum:
                if quantity >= minimum:
                    score += 10
                    reasons.append("采购量满足起订要求")
                else:
                    score -= 25
                    reasons.append(f"低于参考起订量 {minimum:,}")
            elif quantity:
                reasons.append("起订量需人工确认")
            score = max(0, min(score, 100))
            if not requested or score >= 40:
                results.append((score, reasons, product))
        return sorted(results, key=lambda item: item[0], reverse=True)[:5]

    @app.route("/admin/users", methods=["GET", "POST"])
    @login_required
    @admin_only
    def users():
        db = get_db()
        if request.method == "POST":
            username = request.form["username"].strip()
            password = request.form["password"]
            try:
                cur = db.execute("INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)", (username, generate_password_hash(password), request.form["role"], now()))
                audit("创建用户", "user", cur.lastrowid, f"岗位：{request.form['role']}")
                db.commit(); flash("用户已创建", "success")
            except sqlite3.IntegrityError: flash("用户名已经存在", "error")
            return redirect(url_for("users"))
        return render_template("admin/users.html", users=db.execute("SELECT id,username,role,created_at FROM users ORDER BY id").fetchall())

    @app.post("/admin/users/<int:user_id>/password")
    @login_required
    @admin_only
    def reset_password(user_id):
        get_db().execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(request.form["password"]), user_id))
        audit("重置密码", "user", user_id); get_db().commit(); flash("密码已重置", "success")
        return redirect(url_for("users"))

    @app.route("/admin/catalog-rules", methods=["GET", "POST"])
    @login_required
    def catalog_rules():
        db = get_db()
        if request.method == "POST":
            product_id = int(request.form["product_id"])
            db.execute("""INSERT INTO quote_rules(product_id,tier1_min,tier1_price,tier2_min,tier2_price,tier3_min,tier3_price,tooling_cost,sample_cost,decoration_unit_cost,packaging_unit_cost,currency,active,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1,?) ON CONFLICT(product_id) DO UPDATE SET tier1_min=excluded.tier1_min,tier1_price=excluded.tier1_price,tier2_min=excluded.tier2_min,tier2_price=excluded.tier2_price,tier3_min=excluded.tier3_min,tier3_price=excluded.tier3_price,tooling_cost=excluded.tooling_cost,sample_cost=excluded.sample_cost,decoration_unit_cost=excluded.decoration_unit_cost,packaging_unit_cost=excluded.packaging_unit_cost,currency=excluded.currency,updated_at=excluded.updated_at""", (
                product_id, int(request.form.get("tier1_min") or 0), float(request.form.get("tier1_price") or 0), int(request.form.get("tier2_min") or 0), float(request.form.get("tier2_price") or 0), int(request.form.get("tier3_min") or 0), float(request.form.get("tier3_price") or 0), float(request.form.get("tooling_cost") or 0), float(request.form.get("sample_cost") or 0), float(request.form.get("decoration_unit_cost") or 0), float(request.form.get("packaging_unit_cost") or 0), request.form.get("currency", "USD"), now()
            ))
            db.execute("UPDATE products SET pcr_percent=?,recyclable=?,mono_material=?,refillable=?,weight_g=?,material_composition=?,compliance_docs=?,environment_verified=?,updated_at=? WHERE id=?", (
                float(request.form.get("pcr_percent") or 0), request.form.get("recyclable"), request.form.get("mono_material"), request.form.get("refillable"), float(request.form.get("weight_g") or 0), request.form.get("material_composition"), request.form.get("compliance_docs"), int(bool(request.form.get("environment_verified"))), now(), product_id
            ))
            audit("更新报价与环保规则", "product", product_id); db.commit(); flash("产品规则已保存", "success"); return redirect(url_for("catalog_rules"))
        products = db.execute("SELECT p.*,q.* FROM products p LEFT JOIN quote_rules q ON q.product_id=p.id ORDER BY p.id DESC").fetchall()
        return render_template("admin/catalog_rules.html", products=products)

    @app.post("/admin/products/<int:product_id>/generate")
    @login_required
    def generate_product_copy(product_id):
        db = get_db(); p = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if not p: abort(404)
        summary = f"{p['name']} is a {p['capacity'] or 'custom-capacity'} {p['category'] or 'cosmetic packaging solution'} in {p['material'] or 'selected materials'}, developed for reliable filling, decoration and repeat production."
        description = f"Designed for beauty brands and cosmetic manufacturers, {p['name']} supports {p['decoration'] or 'custom color and decoration options'}. The standard minimum order is {p['moq'] or 'confirmed by project'}, with sampling in {p['sample_time'] or 'a project-specific period'} and production lead time of {p['lead_time'] or 'a confirmed schedule'}. Material, compatibility, leakage and appearance requirements are verified before mass production."
        db.execute("UPDATE products SET summary=?,description=?,updated_at=? WHERE id=?", (summary, description, now(), product_id)); audit("自动生成产品介绍", "product", product_id); db.commit(); flash("产品介绍草稿已生成，请审核后发布", "success")
        return redirect(url_for("edit_product", product_id=product_id))

    @app.route("/admin/auto-quote", methods=["GET", "POST"])
    @login_required
    def auto_quote():
        db = get_db(); result = None
        if request.method == "POST":
            product_id, quantity = int(request.form["product_id"]), int(request.form["quantity"])
            rule = db.execute("SELECT q.*,p.name FROM quote_rules q JOIN products p ON p.id=q.product_id WHERE q.product_id=? AND q.active=1", (product_id,)).fetchone()
            if not rule: flash("该产品尚未设置报价规则", "error"); return redirect(url_for("auto_quote"))
            if quantity >= rule["tier3_min"]: tier, unit = "第三档", rule["tier3_price"]
            elif quantity >= rule["tier2_min"]: tier, unit = "第二档", rule["tier2_price"]
            elif quantity >= rule["tier1_min"]: tier, unit = "第一档", rule["tier1_price"]
            else: flash("数量低于第一档起订量", "error"); return redirect(url_for("auto_quote"))
            decoration = rule["decoration_unit_cost"] if request.form.get("include_decoration") else 0
            packaging = rule["packaging_unit_cost"]
            tooling = rule["tooling_cost"] if request.form.get("include_tooling") else 0
            shipping = float(request.form.get("shipping_cost") or 0)
            total = quantity * (unit + decoration + packaging) + tooling + shipping
            result = {"product": rule["name"], "quantity": quantity, "tier": tier, "unit": unit, "decoration": decoration, "packaging": packaging, "tooling": tooling, "shipping": shipping, "total": total, "currency": rule["currency"]}
            if request.form.get("save_quote") and request.form.get("opportunity_id"):
                stamp = now(); quote_no = f"YCQ-{datetime.utcnow():%Y%m%d%H%M%S}"
                db.execute("INSERT INTO quotes(opportunity_id,quote_no,amount,currency,status,quantity,unit_price,tooling_cost,decoration_cost,packaging_cost,shipping_cost,tier,calculation_note,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                    request.form["opportunity_id"], quote_no, total, rule["currency"], "待审批", quantity, unit, tooling, quantity*decoration, quantity*packaging, shipping, tier, json.dumps(result, ensure_ascii=False), stamp, stamp
                ))
                for days in (2, 7, 14, 30):
                    db.execute("INSERT INTO tasks(opportunity_id,title,assignee,due_at,priority,created_at) VALUES(?,?,?,?,?,?)", (request.form["opportunity_id"], f"报价后第{days}天跟进", session.get("username"), (datetime.utcnow()+timedelta(days=days)).replace(microsecond=0).isoformat(sep=" "), "高" if days <= 7 else "普通", stamp))
                audit("生成自动报价", "opportunity", int(request.form["opportunity_id"]), quote_no); db.commit(); flash("报价已经保存并自动建立四次跟进任务", "success")
        products = db.execute("SELECT p.id,p.name FROM products p JOIN quote_rules q ON q.product_id=p.id WHERE q.active=1 ORDER BY p.name").fetchall()
        opportunities = db.execute("SELECT o.id,o.title,c.name company_name FROM opportunities o JOIN companies c ON c.id=o.company_id ORDER BY o.id DESC").fetchall()
        return render_template("admin/auto_quote.html", products=products, opportunities=opportunities, result=result)

    @app.post("/admin/samples/<int:sample_id>/update")
    @login_required
    def sample_update(sample_id):
        get_db().execute("UPDATE samples SET courier=?,tracking_no=?,status=?,sample_fee=?,shipping_fee=?,approval_status=?,approved_by=?,sent_at=?,received_at=?,feedback=?,next_action=?,updated_at=? WHERE id=?", (
            request.form.get("courier"), request.form.get("tracking_no"), request.form.get("status"), float(request.form.get("sample_fee") or 0), float(request.form.get("shipping_fee") or 0), request.form.get("approval_status"), session.get("username") if request.form.get("approval_status") == "已批准" else None, request.form.get("sent_at"), request.form.get("received_at"), request.form.get("feedback"), request.form.get("next_action"), now(), sample_id
        )); audit("更新样品寄送", "sample", sample_id); get_db().commit(); flash("样品状态已更新", "success"); return redirect(url_for("admin_operations"))

    @app.post("/admin/orders/<int:order_id>/payment")
    @login_required
    def record_payment(order_id):
        db = get_db(); amount = float(request.form["amount"]); stamp = now()
        db.execute("INSERT INTO payments(order_id,amount,currency,payment_date,method,reference_no,status,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (order_id, amount, request.form.get("currency", "USD"), request.form.get("payment_date"), request.form.get("method"), request.form.get("reference_no"), "已确认", request.form.get("notes"), stamp))
        order = db.execute("SELECT amount,paid_amount FROM orders WHERE id=?", (order_id,)).fetchone(); paid = (order["paid_amount"] or 0)+amount
        status = "已付清" if paid >= order["amount"] else "部分付款"
        db.execute("UPDATE orders SET paid_amount=?,payment_status=?,updated_at=? WHERE id=?", (paid,status,stamp,order_id)); audit("登记回款", "order", order_id, str(amount)); db.commit(); flash("回款已登记", "success"); return redirect(url_for("admin_operations"))

    @app.route("/admin/quality", methods=["GET", "POST"])
    @login_required
    def quality():
        db = get_db()
        if request.method == "POST":
            stamp=now(); no=f"YCC-{datetime.utcnow():%Y%m%d%H%M%S}"
            cur=db.execute("INSERT INTO complaints(company_id,opportunity_id,order_id,complaint_no,category,severity,description,root_cause,corrective_action,preventive_action,owner,due_date,status,closed_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (request.form["company_id"],request.form.get("opportunity_id") or None,request.form.get("order_id") or None,no,request.form.get("category"),request.form.get("severity"),request.form["description"],request.form.get("root_cause"),request.form.get("corrective_action"),request.form.get("preventive_action"),request.form.get("owner"),request.form.get("due_date"),request.form.get("status"),now() if request.form.get("status")=="已关闭" else None,stamp,stamp)); audit("创建客诉", "complaint", cur.lastrowid, no); db.commit(); flash("客诉与质量记录已保存", "success"); return redirect(url_for("quality"))
        complaints=db.execute("SELECT x.*,c.name company_name FROM complaints x JOIN companies c ON c.id=x.company_id ORDER BY x.id DESC").fetchall(); companies=db.execute("SELECT id,name FROM companies ORDER BY name").fetchall(); opportunities=db.execute("SELECT id,title FROM opportunities ORDER BY id DESC").fetchall(); orders=db.execute("SELECT id,order_no FROM orders ORDER BY id DESC").fetchall()
        return render_template("admin/quality.html",complaints=complaints,companies=companies,opportunities=opportunities,orders=orders)

    @app.route("/admin/distributors", methods=["GET", "POST"])
    @login_required
    def distributors():
        db=get_db()
        if request.method=="POST":
            stamp=now(); cur=db.execute("INSERT INTO distributors(company_id,name,country,territories,customer_resources,product_scope,annual_target,discount_level,exclusivity,agreement_start,agreement_end,status,owner,risk_notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (request.form.get("company_id") or None,request.form["name"],request.form.get("country"),request.form.get("territories"),request.form.get("customer_resources"),request.form.get("product_scope"),float(request.form.get("annual_target") or 0),request.form.get("discount_level"),request.form.get("exclusivity"),request.form.get("agreement_start"),request.form.get("agreement_end"),request.form.get("status"),request.form.get("owner"),request.form.get("risk_notes"),stamp,stamp)); audit("创建渠道商", "distributor", cur.lastrowid); db.commit(); flash("渠道商已创建", "success"); return redirect(url_for("distributors"))
        rows=db.execute("SELECT d.*,c.name company_name FROM distributors d LEFT JOIN companies c ON c.id=d.company_id ORDER BY d.id DESC").fetchall(); companies=db.execute("SELECT id,name FROM companies ORDER BY name").fetchall(); return render_template("admin/distributors.html",distributors=rows,companies=companies)

    def translate_text(text, language):
        endpoint=os.getenv("TRANSLATION_API_URL",""); key=os.getenv("TRANSLATION_API_KEY","")
        if not endpoint: return text, "未配置翻译服务，已建立待人工翻译草稿"
        payload=json.dumps({"text":text,"target_language":language}).encode("utf-8"); headers={"Content-Type":"application/json"}
        if key: headers["Authorization"]=f"Bearer {key}"
        req=urllib.request.Request(endpoint,data=payload,headers=headers,method="POST")
        with urllib.request.urlopen(req,timeout=30) as response:
            data=json.loads(response.read().decode("utf-8")); return data.get("translation") or data.get("text") or text, "外部翻译服务"

    @app.route("/admin/translations", methods=["GET", "POST"])
    @login_required
    def translations():
        db=get_db()
        if request.method=="POST":
            product_id=int(request.form["product_id"]); language=request.form["language"]; p=db.execute("SELECT * FROM products WHERE id=?",(product_id,)).fetchone()
            try:
                name,provider=translate_text(p["name"] or "",language); summary,_=translate_text(p["summary"] or "",language); description,_=translate_text(p["description"] or "",language)
            except Exception as exc: name,summary,description,provider=p["name"],p["summary"],p["description"],f"翻译服务失败：{exc}"
            stamp=now(); db.execute("INSERT INTO product_translations(product_id,language,name,summary,description,decoration,sustainability,status,generated_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(product_id,language) DO UPDATE SET name=excluded.name,summary=excluded.summary,description=excluded.description,status='待审核',generated_by=excluded.generated_by,updated_at=excluded.updated_at", (product_id,language,name,summary,description,p["decoration"],p["sustainability"],"待审核",provider,stamp,stamp)); audit("生成翻译草稿", "product", product_id, language); db.commit(); flash("翻译草稿已生成，必须人工审核后才能发布", "success"); return redirect(url_for("translations"))
        rows=db.execute("SELECT t.*,p.name source_name FROM product_translations t JOIN products p ON p.id=t.product_id ORDER BY t.id DESC").fetchall(); products=db.execute("SELECT id,name FROM products ORDER BY name").fetchall(); return render_template("admin/translations.html",rows=rows,products=products,languages=LANGUAGES)

    @app.post("/admin/translations/<int:translation_id>/review")
    @login_required
    def review_translation(translation_id):
        db=get_db(); db.execute("UPDATE product_translations SET name=?,summary=?,description=?,decoration=?,sustainability=?,status=?,reviewed_by=?,reviewed_at=?,updated_at=? WHERE id=?", (request.form.get("name"),request.form.get("summary"),request.form.get("description"),request.form.get("decoration"),request.form.get("sustainability"),request.form.get("status"),session.get("username"),now(),now(),translation_id)); audit("审核翻译", "translation", translation_id, request.form.get("status")); db.commit(); flash("翻译审核结果已保存", "success"); return redirect(url_for("translations"))

    @app.route("/admin/intelligence", methods=["GET", "POST"])
    @login_required
    def intelligence():
        db=get_db()
        if request.method=="POST":
            for c in db.execute("SELECT id FROM companies").fetchall(): calculate_company_score(db,c["id"])
            for o in db.execute("SELECT * FROM opportunities").fetchall(): calculate_risk(db,o)
            audit("运行智能分析"); db.commit(); flash("客户评分和商机风险已经重新计算", "success"); return redirect(url_for("intelligence"))
        today=datetime.utcnow(); d30=(today+timedelta(days=30)).date().isoformat(); d90=(today+timedelta(days=90)).date().isoformat()
        forecast30=db.execute("SELECT COALESCE(SUM(amount*probability/100.0),0) n FROM opportunities WHERE expected_close<=? AND stage IN ({})".format(','.join('?'*len(ACTIVE_STAGES))), (d30,*ACTIVE_STAGES)).fetchone()["n"]
        forecast90=db.execute("SELECT COALESCE(SUM(amount*probability/100.0),0) n FROM opportunities WHERE expected_close<=? AND stage IN ({})".format(','.join('?'*len(ACTIVE_STAGES))), (d90,*ACTIVE_STAGES)).fetchone()["n"]
        total=db.execute("SELECT COALESCE(SUM(amount*probability/100.0),0) n FROM opportunities WHERE stage IN ({})".format(','.join('?'*len(ACTIVE_STAGES))), tuple(ACTIVE_STAGES)).fetchone()["n"]
        companies=db.execute("SELECT * FROM companies ORDER BY score DESC,id DESC LIMIT 30").fetchall(); risks=db.execute("SELECT o.*,c.name company_name FROM opportunities o JOIN companies c ON c.id=o.company_id WHERE o.risk_level!='正常' ORDER BY CASE o.risk_level WHEN '高风险' THEN 0 ELSE 1 END,o.amount DESC").fetchall()
        return render_template("admin/intelligence.html",companies=companies,risks=risks,forecast30=forecast30,forecast90=forecast90,total=total)

    @app.route("/packaging-selector", methods=["GET", "POST"])
    def packaging_selector():
        db = get_db()
        results = []
        submitted = request.method == "POST"
        form_data = {
            "category": request.form.get("category", "").strip(),
            "capacity": request.form.get("capacity", "").strip(),
            "material": request.form.get("material", "").strip(),
            "use_case": request.form.get("use_case", "").strip(),
            "dispensing": request.form.get("dispensing", "").strip(),
            "sustainability": request.form.get("sustainability", "").strip(),
            "quantity": request.form.get("quantity", "10000").strip(),
        }
        published_count = db.execute("SELECT COUNT(*) n FROM products WHERE published=1").fetchone()["n"]
        if submitted:
            try:
                quantity = max(0, int(form_data["quantity"] or 0))
            except ValueError:
                quantity = 0
                flash("Please enter a valid order quantity.", "error")
            if not published_count:
                flash("No published products are available yet. Please request a tailored recommendation.", "info")
            else:
                results = recommend_products(
                    db, form_data["category"], form_data["capacity"],
                    form_data["material"], quantity, form_data["use_case"],
                    form_data["dispensing"], form_data["sustainability"]
                )
                if not results:
                    flash("No sufficiently strong match was found. Send your brief and our packaging team will recommend alternatives.", "info")
        categories = db.execute(
            "SELECT DISTINCT category FROM products WHERE published=1 AND category!='' ORDER BY category"
        ).fetchall()
        return render_template(
            "public/selector.html", results=results, categories=categories,
            submitted=submitted, has_products=bool(published_count), form_data=form_data
        )

    @app.route("/cost-estimator", methods=["GET", "POST"])
    def cost_estimator():
        db = get_db()
        result = None
        submitted = request.method == "POST"
        form_data = {
            "product_id": request.form.get("product_id", ""),
            "quantity": request.form.get("quantity", "10000").strip(),
            "include_decoration": bool(request.form.get("include_decoration")),
            "include_tooling": bool(request.form.get("include_tooling")),
        }
        language = (request.view_args or {}).get("language", "en")
        products = db.execute(
            """SELECT p.id,p.name,p.moq,COALESCE(t.name,p.name) localized_name FROM products p
               JOIN quote_rules q ON q.product_id=p.id
               LEFT JOIN product_translations t ON t.product_id=p.id AND t.language=? AND t.status='已批准'
               WHERE p.published=1 AND q.active=1
               ORDER BY localized_name""",
            (language,)
        ).fetchall()
        if submitted:
            try:
                quantity = max(1, int(form_data["quantity"]))
                product_id = int(form_data["product_id"])
            except (TypeError, ValueError):
                quantity = product_id = 0
                flash("Select a product and enter a valid quantity.", "error")
            rule = None
            if product_id:
                rule = db.execute(
                    """SELECT q.*,p.name,COALESCE(t.name,p.name) localized_name FROM quote_rules q
                       JOIN products p ON p.id=q.product_id
                       LEFT JOIN product_translations t ON t.product_id=p.id AND t.language=? AND t.status='已批准'
                       WHERE q.product_id=? AND q.active=1 AND p.published=1""",
                    (language, product_id)
                ).fetchone()
            if not products:
                flash("Cost rules have not been published yet. Submit a project brief for a manual estimate.", "info")
            elif not rule:
                flash("The selected product does not have an active cost rule.", "error")
            else:
                unit = (
                    rule["tier3_price"] if quantity >= rule["tier3_min"] else
                    rule["tier2_price"] if quantity >= rule["tier2_min"] else
                    rule["tier1_price"] if quantity >= rule["tier1_min"] else None
                )
                if unit is None:
                    flash(f"Minimum configured quantity: {rule['tier1_min']:,} units.", "error")
                else:
                    base = quantity * unit
                    packaging = quantity * (rule["packaging_unit_cost"] or 0)
                    decoration = quantity * (rule["decoration_unit_cost"] or 0) if form_data["include_decoration"] else 0
                    tooling = (rule["tooling_cost"] or 0) if form_data["include_tooling"] else 0
                    low = base + packaging + decoration + tooling
                    high = low * 1.08
                    result = {
                        "product": rule["localized_name"], "low": low, "high": high,
                        "currency": rule["currency"], "quantity": quantity,
                        "unit_low": low / quantity, "unit_high": high / quantity,
                        "breakdown": {
                            "base": base, "packaging": packaging,
                            "decoration": decoration, "tooling": tooling,
                        },
                    }
        return render_template(
            "public/cost_estimator.html", products=products, result=result,
            submitted=submitted, has_products=bool(products), form_data=form_data
        )

    @app.get("/language/<language>/products/<slug>")
    def localized_product(language,slug):
        if language not in LANGUAGES: abort(404)
        row=get_db().execute("SELECT id FROM products WHERE slug=? AND published=1",(slug,)).fetchone()
        if not row: abort(404)
        return redirect(url_for("localized_product_v4", language=language, slug=slug), code=301)

    @app.get("/admin/system")
    @login_required
    @admin_only
    def system_admin():
        logs=get_db().execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100").fetchall(); return render_template("admin/system.html",logs=logs)

    @app.post("/admin/system/backup")
    @login_required
    @admin_only
    def create_backup():
        backup_dir=Path(db_path).parent.parent / "backups"; backup_dir.mkdir(parents=True,exist_ok=True); stamp=datetime.utcnow().strftime("%Y%m%d-%H%M%S"); archive=backup_dir/f"yincai-backup-{stamp}"
        temp=backup_dir/f"snapshot-{stamp}"; temp.mkdir(); shutil.copy2(db_path,temp/"yincai.db")
        if Path(upload_folder).exists(): shutil.copytree(upload_folder,temp/"uploads")
        output=shutil.make_archive(str(archive),"zip",temp); shutil.rmtree(temp); audit("创建数据备份"); get_db().commit(); return send_file(output,as_attachment=True,download_name=Path(output).name)

    @app.get("/api/v1/intelligence/company/<int:company_id>")
    def api_company_score(company_id):
        token=request.headers.get("Authorization","").removeprefix("Bearer ")
        if token != os.getenv("API_TOKEN","") or not token: return jsonify({"error":"unauthorized"}),401
        score,grade=calculate_company_score(get_db(),company_id); get_db().commit(); row=get_db().execute("SELECT score_reason FROM companies WHERE id=?",(company_id,)).fetchone(); return jsonify({"company_id":company_id,"score":score,"grade":grade,"reason":row["score_reason"]})
