import os
import csv
import io
import json
import smtplib
from email.message import EmailMessage
import secrets
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import (
    Flask, abort, flash, g, jsonify, redirect, render_template, request,
    send_from_directory, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "data" / "yincai.db"))
UPLOAD_FOLDER = Path(os.getenv("UPLOAD_FOLDER", BASE_DIR / "uploads"))
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "mp4", "mov", "webm", "pdf"}
STAGES = ["目标企业", "有效联系人", "合格线索", "正式询价", "样品项目", "正式报价", "试单", "批量订单", "已回款", "复购客户"]
CHANNELS = ["谷歌自然搜索", "谷歌广告", "领英开发", "精准邮件", "社交平台", "海外展会", "海外渠道商", "即时通信", "客户转介绍", "人工录入"]

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "development-only-change-me"),
    MAX_CONTENT_LENGTH=100 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT '管理员', created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS products (
      id INTEGER PRIMARY KEY, name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL,
      category TEXT, summary TEXT, description TEXT, material TEXT, capacity TEXT,
      dimensions TEXT, moq TEXT, sample_time TEXT, lead_time TEXT, decoration TEXT,
      sustainability TEXT, tests TEXT, image TEXT, video TEXT,
      featured INTEGER NOT NULL DEFAULT 0, published INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS companies (
      id INTEGER PRIMARY KEY, name TEXT NOT NULL, country TEXT, company_type TEXT,
      website TEXT, size TEXT, annual_purchase TEXT, source TEXT, owner TEXT,
      grade TEXT NOT NULL DEFAULT '丙级', risk_status TEXT DEFAULT '正常', notes TEXT,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS contacts (
      id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL, name TEXT NOT NULL,
      title TEXT, email TEXT, phone TEXT, linkedin TEXT, decision_role TEXT,
      created_at TEXT NOT NULL, FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS opportunities (
      id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL, title TEXT NOT NULL,
      product_interest TEXT, quantity TEXT, market TEXT, stage TEXT NOT NULL,
      amount REAL NOT NULL DEFAULT 0, probability INTEGER NOT NULL DEFAULT 10,
      expected_close TEXT, owner TEXT, next_action TEXT, next_action_at TEXT,
      lost_reason TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS inquiries (
      id INTEGER PRIMARY KEY, opportunity_id INTEGER, company_id INTEGER,
      contact_name TEXT, email TEXT, phone TEXT, country TEXT, company_name TEXT,
      product TEXT, quantity TEXT, material TEXT, decoration TEXT, timeline TEXT,
      message TEXT, source TEXT, landing_page TEXT, status TEXT DEFAULT '待处理',
      created_at TEXT NOT NULL,
      FOREIGN KEY(opportunity_id) REFERENCES opportunities(id),
      FOREIGN KEY(company_id) REFERENCES companies(id)
    );
    CREATE TABLE IF NOT EXISTS samples (
      id INTEGER PRIMARY KEY, opportunity_id INTEGER NOT NULL, items TEXT,
      shipping_address TEXT, courier TEXT, tracking_no TEXT, status TEXT DEFAULT '待确认',
      sent_at TEXT, received_at TEXT, feedback TEXT, next_action TEXT,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS quotes (
      id INTEGER PRIMARY KEY, opportunity_id INTEGER NOT NULL, quote_no TEXT UNIQUE NOT NULL,
      amount REAL DEFAULT 0, currency TEXT DEFAULT 'USD', payment_terms TEXT,
      valid_until TEXT, status TEXT DEFAULT '草稿', notes TEXT,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS orders (
      id INTEGER PRIMARY KEY, opportunity_id INTEGER NOT NULL, order_no TEXT UNIQUE NOT NULL,
      amount REAL DEFAULT 0, currency TEXT DEFAULT 'USD', gross_margin REAL DEFAULT 0,
      payment_status TEXT DEFAULT '待付款', delivery_status TEXT DEFAULT '待生产',
      due_date TEXT, paid_amount REAL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS tasks (
      id INTEGER PRIMARY KEY, company_id INTEGER, opportunity_id INTEGER,
      title TEXT NOT NULL, assignee TEXT, due_at TEXT, priority TEXT DEFAULT '普通',
      status TEXT DEFAULT '待办', created_at TEXT NOT NULL,
      FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE,
      FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS activities (
      id INTEGER PRIMARY KEY, company_id INTEGER, opportunity_id INTEGER,
      activity_type TEXT, content TEXT NOT NULL, actor TEXT, created_at TEXT NOT NULL,
      FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE,
      FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_opportunity_stage ON opportunities(stage);
    CREATE INDEX IF NOT EXISTS idx_company_source ON companies(source);
    CREATE INDEX IF NOT EXISTS idx_task_due ON tasks(due_at, status);
    CREATE TABLE IF NOT EXISTS settings (
      key TEXT PRIMARY KEY, value TEXT, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS audit_logs (
      id INTEGER PRIMARY KEY, user_id INTEGER, username TEXT, action TEXT NOT NULL,
      entity_type TEXT, entity_id INTEGER, detail TEXT, ip TEXT, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS tracking_events (
      id INTEGER PRIMARY KEY, event_name TEXT NOT NULL, source TEXT, medium TEXT,
      campaign TEXT, keyword TEXT, landing_page TEXT, visitor_id TEXT, ip TEXT,
      payload TEXT, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS complaints (
      id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL, opportunity_id INTEGER,
      order_id INTEGER, complaint_no TEXT UNIQUE NOT NULL, category TEXT, severity TEXT,
      description TEXT NOT NULL, root_cause TEXT, corrective_action TEXT,
      preventive_action TEXT, owner TEXT, due_date TEXT, status TEXT DEFAULT '待处理',
      closed_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      FOREIGN KEY(company_id) REFERENCES companies(id), FOREIGN KEY(opportunity_id) REFERENCES opportunities(id),
      FOREIGN KEY(order_id) REFERENCES orders(id)
    );
    CREATE TABLE IF NOT EXISTS distributors (
      id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT NOT NULL, country TEXT,
      territories TEXT, customer_resources TEXT, product_scope TEXT, annual_target REAL DEFAULT 0,
      discount_level TEXT, exclusivity TEXT, agreement_start TEXT, agreement_end TEXT,
      status TEXT DEFAULT '评估中', owner TEXT, risk_notes TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      FOREIGN KEY(company_id) REFERENCES companies(id)
    );
    CREATE TABLE IF NOT EXISTS payments (
      id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL, amount REAL NOT NULL,
      currency TEXT DEFAULT 'USD', payment_date TEXT, method TEXT, reference_no TEXT,
      status TEXT DEFAULT '已确认', notes TEXT, created_at TEXT NOT NULL,
      FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS product_translations (
      id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL, language TEXT NOT NULL,
      name TEXT, summary TEXT, description TEXT, decoration TEXT, sustainability TEXT,
      status TEXT DEFAULT '待审核', generated_by TEXT, reviewed_by TEXT, reviewed_at TEXT,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      UNIQUE(product_id,language), FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS quote_rules (
      id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL UNIQUE,
      tier1_min INTEGER DEFAULT 1000, tier1_price REAL DEFAULT 0,
      tier2_min INTEGER DEFAULT 5000, tier2_price REAL DEFAULT 0,
      tier3_min INTEGER DEFAULT 10000, tier3_price REAL DEFAULT 0,
      tooling_cost REAL DEFAULT 0, sample_cost REAL DEFAULT 0,
      decoration_unit_cost REAL DEFAULT 0, packaging_unit_cost REAL DEFAULT 0,
      currency TEXT DEFAULT 'USD', active INTEGER DEFAULT 1, updated_at TEXT NOT NULL,
      FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_tracking_source ON tracking_events(source,campaign);
    CREATE INDEX IF NOT EXISTS idx_complaint_status ON complaints(status,severity);
    """)
    def add_column(table, column, definition):
        columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    for column, definition in {
        "score": "INTEGER DEFAULT 0", "score_reason": "TEXT", "last_scored_at": "TEXT"
    }.items(): add_column("companies", column, definition)
    for column, definition in {
        "risk_level": "TEXT DEFAULT '正常'", "risk_reason": "TEXT", "last_risk_check": "TEXT"
    }.items(): add_column("opportunities", column, definition)
    for column, definition in {
        "visitor_ip": "TEXT", "medium": "TEXT", "campaign": "TEXT", "keyword": "TEXT", "visitor_id": "TEXT"
    }.items(): add_column("inquiries", column, definition)
    for column, definition in {
        "sample_fee": "REAL DEFAULT 0", "shipping_fee": "REAL DEFAULT 0", "approval_status": "TEXT DEFAULT '待审批'", "approved_by": "TEXT"
    }.items(): add_column("samples", column, definition)
    for column, definition in {
        "quantity": "INTEGER DEFAULT 0", "unit_price": "REAL DEFAULT 0", "tooling_cost": "REAL DEFAULT 0",
        "decoration_cost": "REAL DEFAULT 0", "packaging_cost": "REAL DEFAULT 0", "shipping_cost": "REAL DEFAULT 0",
        "tier": "TEXT", "calculation_note": "TEXT", "approved_by": "TEXT"
    }.items(): add_column("quotes", column, definition)
    for column, definition in {
        "pcr_percent": "REAL DEFAULT 0", "recyclable": "TEXT", "mono_material": "TEXT", "refillable": "TEXT",
        "weight_g": "REAL DEFAULT 0", "material_composition": "TEXT", "compliance_docs": "TEXT", "environment_verified": "INTEGER DEFAULT 0"
    }.items(): add_column("products", column, definition)
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "admin123456")
    if not db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone():
        db.execute(
            "INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)",
            (username, generate_password_hash(password), "管理员", now())
        )
    db.commit()
    db.close()


def now():
    return datetime.utcnow().replace(microsecond=0).isoformat(sep=" ")


def audit(action, entity_type=None, entity_id=None, detail=None):
    if not session.get("user_id"):
        return
    db = get_db()
    db.execute("INSERT INTO audit_logs(user_id,username,action,entity_type,entity_id,detail,ip,created_at) VALUES(?,?,?,?,?,?,?,?)", (
        session.get("user_id"), session.get("username"), action, entity_type, entity_id, detail,
        request.headers.get("X-Forwarded-For", request.remote_addr), now()
    ))


def send_inquiry_notification(company_name, product, email):
    host = os.getenv("SMTP_HOST", "")
    recipient = os.getenv("INQUIRY_NOTIFY_EMAIL", "")
    if not host or not recipient:
        return False
    message = EmailMessage()
    message["Subject"] = f"银彩新询价：{company_name} - {product}"
    message["From"] = os.getenv("SMTP_FROM", os.getenv("SMTP_USERNAME", recipient))
    message["To"] = recipient
    message.set_content(f"客户企业：{company_name}\n需求产品：{product}\n客户邮箱：{email}\n请登录管理后台在两小时内处理。")
    port = int(os.getenv("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=10) as smtp:
        if os.getenv("SMTP_TLS", "1") == "1": smtp.starttls()
        username = os.getenv("SMTP_USERNAME", "")
        if username: smtp.login(username, os.getenv("SMTP_PASSWORD", ""))
        smtp.send_message(message)
    return True


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(24)
    return session["csrf_token"]


app.jinja_env.globals.update(csrf_token=csrf_token, stages=STAGES)


@app.before_request
def protect_csrf():
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not request.path.startswith("/api/"):
        token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        if not token or not secrets.compare_digest(token, session.get("csrf_token", "")):
            abort(400, "表单已过期，请刷新页面后重试")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def clean_slug(value):
    value = "-".join(secure_filename(value).lower().replace("_", "-").split("-"))
    return value or secrets.token_hex(4)


def save_upload(field):
    file = request.files.get(field)
    if not file or not file.filename:
        return None
    extension = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("不支持的文件格式")
    filename = f"{datetime.utcnow():%Y%m%d%H%M%S}-{secrets.token_hex(4)}.{extension}"
    file.save(UPLOAD_FOLDER / filename)
    return filename


@app.context_processor
def global_context():
    return {
        "company_name": os.getenv("COMPANY_NAME", "Yincai Packaging"),
        "public_email": os.getenv("PUBLIC_EMAIL", "sales@example.com"),
        "public_phone": os.getenv("PUBLIC_PHONE", "+86 000 0000 0000"),
        "current_year": datetime.utcnow().year,
        "analytics_id": os.getenv("ANALYTICS_ID", ""),
    }


@app.get("/")
def public_home():
    products = get_db().execute("SELECT * FROM products WHERE published=1 ORDER BY featured DESC, id DESC LIMIT 8").fetchall()
    return render_template("public/home.html", products=products)


@app.get("/products")
def public_products():
    category = request.args.get("category", "")
    if category:
        products = get_db().execute("SELECT * FROM products WHERE published=1 AND category=? ORDER BY featured DESC, id DESC", (category,)).fetchall()
    else:
        products = get_db().execute("SELECT * FROM products WHERE published=1 ORDER BY featured DESC, id DESC").fetchall()
    categories = get_db().execute("SELECT DISTINCT category FROM products WHERE published=1 AND category!='' ORDER BY category").fetchall()
    return render_template("public/products.html", products=products, categories=categories, active_category=category)


@app.get("/products/<slug>")
def public_product(slug):
    product = get_db().execute("SELECT * FROM products WHERE slug=? AND published=1", (slug,)).fetchone()
    if not product:
        abort(404)
    translations = get_db().execute("SELECT language FROM product_translations WHERE product_id=? AND status='已批准'", (product["id"],)).fetchall()
    return render_template("public/product.html", product=product, translations=translations)


@app.route("/request-quote", methods=["GET", "POST"])
def request_quote():
    product = request.args.get("product", "")
    if request.method == "POST":
        form = request.form
        if form.get("website_confirm"):
            return "", 204
        required = [form.get("contact_name"), form.get("email"), form.get("company_name"), form.get("product")]
        if not all(required):
            flash("Please complete the required fields.", "error")
            return render_template("public/request_quote.html", form=form)
        db = get_db()
        visitor_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        recent_limit = (datetime.utcnow()-timedelta(minutes=10)).replace(microsecond=0).isoformat(sep=" ")
        if db.execute("SELECT COUNT(*) n FROM inquiries WHERE visitor_ip=? AND created_at>=?", (visitor_ip, recent_limit)).fetchone()["n"] >= 5:
            return "Too many requests. Please try again later.", 429
        company = db.execute("SELECT id FROM companies WHERE lower(name)=lower(?)", (form["company_name"].strip(),)).fetchone()
        stamp = now()
        source = form.get("source") or request.args.get("utm_source") or "海外网站"
        medium = form.get("medium") or request.args.get("utm_medium")
        campaign = form.get("campaign") or request.args.get("utm_campaign")
        keyword = form.get("keyword") or request.args.get("utm_term")
        visitor_id = form.get("visitor_id")
        if company:
            company_id = company["id"]
        else:
            cur = db.execute(
                "INSERT INTO companies(name,country,company_type,source,grade,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (form["company_name"].strip(), form.get("country"), form.get("company_type"), source, "丙级", stamp, stamp)
            )
            company_id = cur.lastrowid
        contact = db.execute("SELECT id FROM contacts WHERE company_id=? AND lower(email)=lower(?)", (company_id, form["email"].strip())).fetchone()
        if not contact:
            db.execute(
                "INSERT INTO contacts(company_id,name,email,phone,title,created_at) VALUES(?,?,?,?,?,?)",
                (company_id, form["contact_name"].strip(), form["email"].strip(), form.get("phone"), form.get("title"), stamp)
            )
        title = f"{form['company_name']} - {form['product']}"
        cur = db.execute(
            "INSERT INTO opportunities(company_id,title,product_interest,quantity,market,stage,probability,owner,next_action,next_action_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (company_id, title, form["product"], form.get("quantity"), form.get("country"), "正式询价", 35, "待分配", "首次人工回复", (datetime.utcnow()+timedelta(hours=2)).replace(microsecond=0).isoformat(sep=" "), stamp, stamp)
        )
        opportunity_id = cur.lastrowid
        db.execute(
            "INSERT INTO inquiries(opportunity_id,company_id,contact_name,email,phone,country,company_name,product,quantity,material,decoration,timeline,message,source,landing_page,visitor_ip,medium,campaign,keyword,visitor_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (opportunity_id, company_id, form["contact_name"], form["email"], form.get("phone"), form.get("country"), form["company_name"], form["product"], form.get("quantity"), form.get("material"), form.get("decoration"), form.get("timeline"), form.get("message"), source, request.referrer or request.path, visitor_ip, medium, campaign, keyword, visitor_id, stamp)
        )
        db.execute(
            "INSERT INTO tasks(company_id,opportunity_id,title,assignee,due_at,priority,created_at) VALUES(?,?,?,?,?,?,?)",
            (company_id, opportunity_id, "回复新询价", "待分配", (datetime.utcnow()+timedelta(hours=2)).replace(microsecond=0).isoformat(sep=" "), "紧急", stamp)
        )
        db.commit()
        try:
            send_inquiry_notification(form["company_name"], form["product"], form["email"])
        except (OSError, smtplib.SMTPException):
            pass
        return render_template("public/thanks.html")
    return render_template("public/request_quote.html", product=product)


@app.get("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = get_db().execute("SELECT * FROM users WHERE username=?", (request.form.get("username", ""),)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            csrf_token()
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("用户名或密码错误", "error")
    return render_template("admin/login.html")


@app.post("/admin/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/admin")
@login_required
def dashboard():
    db = get_db()
    metrics = {
        "companies": db.execute("SELECT COUNT(*) n FROM companies").fetchone()["n"],
        "inquiries": db.execute("SELECT COUNT(*) n FROM inquiries WHERE status='待处理'").fetchone()["n"],
        "samples": db.execute("SELECT COUNT(*) n FROM samples WHERE status NOT IN ('已完成','已取消')").fetchone()["n"],
        "pipeline": db.execute("SELECT COALESCE(SUM(amount * probability / 100.0),0) n FROM opportunities WHERE stage NOT IN ('已回款','复购客户')").fetchone()["n"],
        "orders": db.execute("SELECT COALESCE(SUM(amount),0) n FROM orders").fetchone()["n"],
        "payments": db.execute("SELECT COALESCE(SUM(paid_amount),0) n FROM orders").fetchone()["n"],
    }
    tasks = db.execute("SELECT t.*, c.name company_name FROM tasks t LEFT JOIN companies c ON c.id=t.company_id WHERE t.status!='已完成' ORDER BY CASE t.priority WHEN '紧急' THEN 0 WHEN '高' THEN 1 ELSE 2 END, t.due_at LIMIT 12").fetchall()
    inquiries = db.execute("SELECT * FROM inquiries ORDER BY id DESC LIMIT 8").fetchall()
    stages = db.execute("SELECT stage, COUNT(*) count, COALESCE(SUM(amount),0) amount FROM opportunities GROUP BY stage").fetchall()
    sources = db.execute("SELECT COALESCE(source,'未标记') source, COUNT(*) count FROM companies GROUP BY source ORDER BY count DESC LIMIT 8").fetchall()
    return render_template("admin/dashboard.html", metrics=metrics, tasks=tasks, inquiries=inquiries, stage_rows=stages, sources=sources)


@app.route("/admin/products", methods=["GET", "POST"])
@login_required
def admin_products():
    db = get_db()
    if request.method == "POST":
        try:
            image = save_upload("image")
            video = save_upload("video")
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("admin_products"))
        stamp = now()
        slug = clean_slug(request.form.get("slug") or request.form["name"])
        if db.execute("SELECT id FROM products WHERE slug=?", (slug,)).fetchone():
            slug = f"{slug}-{secrets.token_hex(2)}"
        db.execute("""INSERT INTO products
          (name,slug,category,summary,description,material,capacity,dimensions,moq,sample_time,lead_time,decoration,sustainability,tests,image,video,featured,published,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            request.form["name"], slug, request.form.get("category"), request.form.get("summary"), request.form.get("description"),
            request.form.get("material"), request.form.get("capacity"), request.form.get("dimensions"), request.form.get("moq"),
            request.form.get("sample_time"), request.form.get("lead_time"), request.form.get("decoration"), request.form.get("sustainability"),
            request.form.get("tests"), image, video, int(bool(request.form.get("featured"))), int(bool(request.form.get("published"))), stamp, stamp
        ))
        db.commit()
        flash("产品已创建", "success")
        return redirect(url_for("admin_products"))
    products = db.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    return render_template("admin/products.html", products=products)


@app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        abort(404)
    if request.method == "POST":
        try:
            image = save_upload("image") or product["image"]
            video = save_upload("video") or product["video"]
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("edit_product", product_id=product_id))
        db.execute("""UPDATE products SET name=?,category=?,summary=?,description=?,material=?,capacity=?,dimensions=?,moq=?,sample_time=?,lead_time=?,decoration=?,sustainability=?,tests=?,image=?,video=?,featured=?,published=?,updated_at=? WHERE id=?""", (
            request.form["name"], request.form.get("category"), request.form.get("summary"), request.form.get("description"), request.form.get("material"),
            request.form.get("capacity"), request.form.get("dimensions"), request.form.get("moq"), request.form.get("sample_time"), request.form.get("lead_time"),
            request.form.get("decoration"), request.form.get("sustainability"), request.form.get("tests"), image, video,
            int(bool(request.form.get("featured"))), int(bool(request.form.get("published"))), now(), product_id
        ))
        db.commit()
        flash("产品资料已更新", "success")
        return redirect(url_for("admin_products"))
    return render_template("admin/product_edit.html", product=product)


@app.route("/admin/companies", methods=["GET", "POST"])
@login_required
def admin_companies():
    db = get_db()
    if request.method == "POST":
        stamp = now()
        cur = db.execute("INSERT INTO companies(name,country,company_type,website,size,annual_purchase,source,owner,grade,risk_status,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            request.form["name"], request.form.get("country"), request.form.get("company_type"), request.form.get("website"), request.form.get("size"),
            request.form.get("annual_purchase"), request.form.get("source"), request.form.get("owner"), request.form.get("grade", "丙级"),
            request.form.get("risk_status", "正常"), request.form.get("notes"), stamp, stamp
        ))
        company_id = cur.lastrowid
        if request.form.get("contact_name"):
            db.execute("INSERT INTO contacts(company_id,name,title,email,phone,linkedin,decision_role,created_at) VALUES(?,?,?,?,?,?,?,?)", (
                company_id, request.form["contact_name"], request.form.get("title"), request.form.get("email"), request.form.get("phone"),
                request.form.get("linkedin"), request.form.get("decision_role"), stamp
            ))
        db.commit()
        flash("客户企业已创建", "success")
        return redirect(url_for("company_detail", company_id=company_id))
    query = request.args.get("q", "").strip()
    if query:
        companies = db.execute("SELECT * FROM companies WHERE name LIKE ? OR country LIKE ? ORDER BY id DESC", (f"%{query}%", f"%{query}%")).fetchall()
    else:
        companies = db.execute("SELECT * FROM companies ORDER BY id DESC").fetchall()
    return render_template("admin/companies.html", companies=companies, channels=CHANNELS, query=query)


@app.route("/admin/companies/<int:company_id>", methods=["GET", "POST"])
@login_required
def company_detail(company_id):
    db = get_db()
    company = db.execute("SELECT * FROM companies WHERE id=?", (company_id,)).fetchone()
    if not company:
        abort(404)
    if request.method == "POST":
        action = request.form.get("action")
        if action == "contact":
            db.execute("INSERT INTO contacts(company_id,name,title,email,phone,linkedin,decision_role,created_at) VALUES(?,?,?,?,?,?,?,?)", (
                company_id, request.form["name"], request.form.get("title"), request.form.get("email"), request.form.get("phone"), request.form.get("linkedin"), request.form.get("decision_role"), now()
            ))
        elif action == "activity":
            db.execute("INSERT INTO activities(company_id,activity_type,content,actor,created_at) VALUES(?,?,?,?,?)", (
                company_id, request.form.get("activity_type"), request.form["content"], session.get("username"), now()
            ))
        elif action == "task":
            db.execute("INSERT INTO tasks(company_id,title,assignee,due_at,priority,created_at) VALUES(?,?,?,?,?,?)", (
                company_id, request.form["title"], request.form.get("assignee"), request.form.get("due_at"), request.form.get("priority"), now()
            ))
        db.commit()
        flash("记录已保存", "success")
        return redirect(url_for("company_detail", company_id=company_id))
    contacts = db.execute("SELECT * FROM contacts WHERE company_id=? ORDER BY id DESC", (company_id,)).fetchall()
    opportunities = db.execute("SELECT * FROM opportunities WHERE company_id=? ORDER BY id DESC", (company_id,)).fetchall()
    activities = db.execute("SELECT * FROM activities WHERE company_id=? ORDER BY id DESC LIMIT 30", (company_id,)).fetchall()
    tasks = db.execute("SELECT * FROM tasks WHERE company_id=? ORDER BY id DESC", (company_id,)).fetchall()
    return render_template("admin/company_detail.html", company=company, contacts=contacts, opportunities=opportunities, activities=activities, tasks=tasks)


@app.route("/admin/opportunities", methods=["GET", "POST"])
@login_required
def admin_opportunities():
    db = get_db()
    if request.method == "POST":
        stamp = now()
        db.execute("INSERT INTO opportunities(company_id,title,product_interest,quantity,market,stage,amount,probability,expected_close,owner,next_action,next_action_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            request.form["company_id"], request.form["title"], request.form.get("product_interest"), request.form.get("quantity"), request.form.get("market"),
            request.form.get("stage", "合格线索"), float(request.form.get("amount") or 0), int(request.form.get("probability") or 10),
            request.form.get("expected_close"), request.form.get("owner"), request.form.get("next_action"), request.form.get("next_action_at"), stamp, stamp
        ))
        db.commit()
        flash("商机已创建", "success")
        return redirect(url_for("admin_opportunities"))
    opportunities = db.execute("SELECT o.*, c.name company_name FROM opportunities o JOIN companies c ON c.id=o.company_id ORDER BY o.id DESC").fetchall()
    companies = db.execute("SELECT id,name FROM companies ORDER BY name").fetchall()
    grouped = {stage: [] for stage in STAGES}
    for item in opportunities:
        grouped.setdefault(item["stage"], []).append(item)
    return render_template("admin/opportunities.html", grouped=grouped, companies=companies)


@app.post("/admin/opportunities/<int:opportunity_id>/stage")
@login_required
def update_stage(opportunity_id):
    stage = request.form.get("stage")
    if stage not in STAGES:
        abort(400)
    db = get_db()
    opportunity = db.execute("SELECT * FROM opportunities WHERE id=?", (opportunity_id,)).fetchone()
    if not opportunity:
        abort(404)
    probability = {"目标企业": 5, "有效联系人": 10, "合格线索": 20, "正式询价": 35, "样品项目": 50, "正式报价": 60, "试单": 75, "批量订单": 90, "已回款": 100, "复购客户": 100}[stage]
    db.execute("UPDATE opportunities SET stage=?,probability=?,updated_at=? WHERE id=?", (stage, probability, now(), opportunity_id))
    db.execute("INSERT INTO activities(company_id,opportunity_id,activity_type,content,actor,created_at) VALUES(?,?,?,?,?,?)", (
        opportunity["company_id"], opportunity_id, "阶段变更", f"商机从“{opportunity['stage']}”推进到“{stage}”", session.get("username"), now()
    ))
    db.commit()
    flash("商机阶段已更新", "success")
    return redirect(url_for("admin_opportunities"))


@app.route("/admin/operations", methods=["GET", "POST"])
@login_required
def admin_operations():
    db = get_db()
    if request.method == "POST":
        kind = request.form["kind"]
        stamp = now()
        if kind == "sample":
            db.execute("INSERT INTO samples(opportunity_id,items,shipping_address,courier,tracking_no,status,sent_at,received_at,feedback,next_action,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (
                request.form["opportunity_id"], request.form.get("items"), request.form.get("shipping_address"), request.form.get("courier"), request.form.get("tracking_no"), request.form.get("status"), request.form.get("sent_at"), request.form.get("received_at"), request.form.get("feedback"), request.form.get("next_action"), stamp, stamp
            ))
        elif kind == "quote":
            db.execute("INSERT INTO quotes(opportunity_id,quote_no,amount,currency,payment_terms,valid_until,status,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (
                request.form["opportunity_id"], request.form.get("quote_no") or f"YCQ-{datetime.utcnow():%Y%m%d%H%M%S}", float(request.form.get("amount") or 0), request.form.get("currency"), request.form.get("payment_terms"), request.form.get("valid_until"), request.form.get("status"), request.form.get("notes"), stamp, stamp
            ))
        elif kind == "order":
            db.execute("INSERT INTO orders(opportunity_id,order_no,amount,currency,gross_margin,payment_status,delivery_status,due_date,paid_amount,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
                request.form["opportunity_id"], request.form.get("order_no") or f"YCO-{datetime.utcnow():%Y%m%d%H%M%S}", float(request.form.get("amount") or 0), request.form.get("currency"), float(request.form.get("gross_margin") or 0), request.form.get("payment_status"), request.form.get("delivery_status"), request.form.get("due_date"), float(request.form.get("paid_amount") or 0), stamp, stamp
            ))
        else:
            abort(400)
        db.commit()
        flash("业务记录已创建", "success")
        return redirect(url_for("admin_operations"))
    opportunities = db.execute("SELECT o.id,o.title,c.name company_name FROM opportunities o JOIN companies c ON c.id=o.company_id ORDER BY o.id DESC").fetchall()
    samples = db.execute("SELECT s.*,o.title,c.name company_name FROM samples s JOIN opportunities o ON o.id=s.opportunity_id JOIN companies c ON c.id=o.company_id ORDER BY s.id DESC").fetchall()
    quotes = db.execute("SELECT q.*,o.title,c.name company_name FROM quotes q JOIN opportunities o ON o.id=q.opportunity_id JOIN companies c ON c.id=o.company_id ORDER BY q.id DESC").fetchall()
    orders = db.execute("SELECT x.*,o.title,c.name company_name FROM orders x JOIN opportunities o ON o.id=x.opportunity_id JOIN companies c ON c.id=o.company_id ORDER BY x.id DESC").fetchall()
    return render_template("admin/operations.html", opportunities=opportunities, samples=samples, quotes=quotes, orders=orders)


@app.post("/admin/tasks/<int:task_id>/complete")
@login_required
def complete_task(task_id):
    get_db().execute("UPDATE tasks SET status='已完成' WHERE id=?", (task_id,))
    get_db().commit()
    return redirect(request.referrer or url_for("dashboard"))


@app.get("/admin/inquiries")
@login_required
def admin_inquiries():
    rows = get_db().execute("SELECT * FROM inquiries ORDER BY id DESC").fetchall()
    return render_template("admin/inquiries.html", inquiries=rows)


@app.get("/robots.txt")
def robots():
    body = f"User-agent: *\nAllow: /\nDisallow: /admin\nSitemap: {request.url_root.rstrip('/')}/sitemap.xml\n"
    return body, 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.get("/sitemap.xml")
def sitemap():
    pages = [request.url_root.rstrip("/"), url_for("public_products", _external=True), url_for("request_quote", _external=True), url_for("privacy", _external=True)]
    pages += [url_for("public_product", slug=row["slug"], _external=True) for row in get_db().execute("SELECT slug FROM products WHERE published=1")]
    xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{page}</loc></url>' for page in pages) + '</urlset>'
    return xml, 200, {"Content-Type": "application/xml"}


@app.get("/privacy")
def privacy():
    return render_template("public/privacy.html")


@app.post("/api/v1/events")
def track_event():
    data = request.get_json(silent=True) or request.form
    if not data.get("event_name"):
        return jsonify({"error": "event_name required"}), 400
    get_db().execute("INSERT INTO tracking_events(event_name,source,medium,campaign,keyword,landing_page,visitor_id,ip,payload,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (
        data.get("event_name"), data.get("source"), data.get("medium"), data.get("campaign"), data.get("keyword"), data.get("landing_page"), data.get("visitor_id"), request.headers.get("X-Forwarded-For", request.remote_addr), json.dumps(dict(data), ensure_ascii=False), now()
    ))
    get_db().commit()
    return jsonify({"status": "recorded"}), 201


@app.route("/admin/acquisition", methods=["GET", "POST"])
@login_required
def admin_acquisition():
    db = get_db()
    if request.method == "POST":
        file = request.files.get("csv_file")
        if not file or not file.filename.lower().endswith(".csv"):
            flash("请选择逗号分隔表格文件", "error")
            return redirect(url_for("admin_acquisition"))
        try:
            reader = csv.DictReader(io.StringIO(file.read().decode("utf-8-sig")))
            created = 0
            stamp = now()
            for row in reader:
                company_name = (row.get("企业名称") or row.get("company_name") or "").strip()
                if not company_name:
                    continue
                existing = db.execute("SELECT id FROM companies WHERE lower(name)=lower(?)", (company_name,)).fetchone()
                if existing:
                    company_id = existing["id"]
                else:
                    cur = db.execute("INSERT INTO companies(name,country,company_type,website,source,owner,grade,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)", (
                        company_name, row.get("国家") or row.get("country"), row.get("企业类型") or row.get("company_type"), row.get("网站") or row.get("website"),
                        row.get("来源") or row.get("source") or "表格导入", row.get("负责人") or row.get("owner") or "待分配", row.get("等级") or row.get("grade") or "丙级", stamp, stamp
                    ))
                    company_id = cur.lastrowid
                    created += 1
                email = (row.get("邮箱") or row.get("email") or "").strip()
                contact_name = (row.get("联系人") or row.get("contact_name") or "").strip()
                if contact_name and not db.execute("SELECT id FROM contacts WHERE company_id=? AND lower(COALESCE(email,''))=lower(?)", (company_id, email)).fetchone():
                    db.execute("INSERT INTO contacts(company_id,name,title,email,phone,linkedin,decision_role,created_at) VALUES(?,?,?,?,?,?,?,?)", (
                        company_id, contact_name, row.get("职位") or row.get("title"), email, row.get("电话") or row.get("phone"),
                        row.get("领英") or row.get("linkedin"), row.get("决策角色") or row.get("decision_role"), stamp
                    ))
            db.commit()
            flash(f"导入完成，新建 {created} 家企业", "success")
        except (UnicodeDecodeError, csv.Error) as exc:
            db.rollback()
            flash(f"表格解析失败：{exc}", "error")
        return redirect(url_for("admin_acquisition"))
    counts = {row["source"]: row["count"] for row in db.execute("SELECT COALESCE(source,'未标记') source,COUNT(*) count FROM companies GROUP BY source").fetchall()}
    return render_template("admin/acquisition.html", channels=CHANNELS, counts=counts)


@app.get("/api/v1/health")
def api_health():
    return jsonify({"status": "ok", "time": now()})


@app.post("/api/v1/leads")
def api_leads():
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    expected = os.getenv("API_TOKEN", "")
    if not expected or not secrets.compare_digest(token, expected):
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    if not data.get("company_name") or not data.get("email"):
        return jsonify({"error": "company_name and email are required"}), 400
    stamp = now()
    db = get_db()
    cur = db.execute("INSERT INTO companies(name,country,company_type,source,grade,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (
        data["company_name"], data.get("country"), data.get("company_type"), data.get("source", "外部平台接口"), "丙级", stamp, stamp
    ))
    company_id = cur.lastrowid
    db.execute("INSERT INTO contacts(company_id,name,email,phone,title,created_at) VALUES(?,?,?,?,?,?)", (
        company_id, data.get("contact_name", "未命名联系人"), data["email"], data.get("phone"), data.get("title"), stamp
    ))
    db.execute("INSERT INTO tasks(company_id,title,assignee,due_at,priority,created_at) VALUES(?,?,?,?,?,?)", (
        company_id, "处理外部平台新线索", "待分配", (datetime.utcnow()+timedelta(hours=2)).replace(microsecond=0).isoformat(sep=" "), "高", stamp
    ))
    db.commit()
    return jsonify({"company_id": company_id, "status": "created"}), 201


@app.errorhandler(413)
def too_large(_error):
    return "上传文件过大，单次上传不得超过100兆。", 413


from features import register_features
register_features(app, get_db, login_required, now, audit, DB_PATH, UPLOAD_FOLDER)
init_db()

from v4 import register_v4
register_v4(app, get_db, login_required, now, audit, UPLOAD_FOLDER)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
