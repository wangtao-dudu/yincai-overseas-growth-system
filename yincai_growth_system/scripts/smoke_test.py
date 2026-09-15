import io
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

temporary = tempfile.TemporaryDirectory()
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_PATH"] = os.path.join(temporary.name, "test.db")
os.environ["UPLOAD_FOLDER"] = os.path.join(temporary.name, "uploads")
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ADMIN_USERNAME"] = "tester"
os.environ["ADMIN_PASSWORD"] = "safe-test-password"
os.environ["API_TOKEN"] = "test-api-token"

from app import app, get_db

client = app.test_client()

assert client.get("/api/v1/health").status_code == 200
assert client.get("/").status_code == 301
assert client.get("/products").status_code == 301
assert client.get("/admin").status_code == 302

with client.session_transaction() as session:
    session["csrf_token"] = "smoke-token"

response = client.post(
    "/admin/login",
    data={"username": "tester", "password": "safe-test-password", "csrf_token": "smoke-token"},
    follow_redirects=False,
)
assert response.status_code == 302

with client.session_transaction() as session:
    csrf = session["csrf_token"]

response = client.post(
    "/admin/companies",
    data={"csrf_token": csrf, "name": "测试客户", "country": "美国", "source": "领英开发"},
    follow_redirects=False,
)
assert response.status_code == 302
assert client.get("/admin").status_code == 200
assert client.get("/admin/acquisition").status_code == 200

response = client.post(
    "/admin/products",
    data={"csrf_token": csrf, "name": "30ml Airless Bottle", "category": "Airless bottle", "capacity": "30ml", "material": "PP", "moq": "1000", "published": "on"},
    follow_redirects=False,
)
assert response.status_code == 302

with app.app_context():
    db = get_db()
    product_id = db.execute("SELECT id FROM products WHERE name='30ml Airless Bottle'").fetchone()["id"]
    company_id = db.execute("SELECT id FROM companies WHERE name='测试客户'").fetchone()["id"]

response = client.post(
    "/admin/catalog-rules",
    data={"csrf_token": csrf, "product_id": product_id, "tier1_min": 1000, "tier1_price": .5, "tier2_min": 5000, "tier2_price": .4, "tier3_min": 10000, "tier3_price": .3, "tooling_cost": 500, "decoration_unit_cost": .05, "packaging_unit_cost": .02, "currency": "USD", "pcr_percent": 30, "recyclable": "Yes", "mono_material": "PP", "refillable": "No", "weight_g": 22, "environment_verified": "on"},
)
assert response.status_code == 302

response = client.post(
    "/admin/opportunities",
    data={"csrf_token": csrf, "company_id": company_id, "title": "测试商机", "product_interest": "30ml Airless Bottle", "stage": "正式询价", "amount": 10000, "probability": 35},
)
assert response.status_code == 302
with app.app_context():
    opportunity_id = get_db().execute("SELECT id FROM opportunities WHERE title='测试商机'").fetchone()["id"]

response = client.post("/admin/auto-quote", data={"csrf_token": csrf, "product_id": product_id, "quantity": 10000, "include_decoration": "on", "include_tooling": "on", "save_quote": "on", "opportunity_id": opportunity_id})
assert response.status_code == 200 and "4200.00" in response.get_data(as_text=True)
assert client.post("/admin/intelligence", data={"csrf_token": csrf}).status_code == 302
assert client.get("/admin/intelligence").status_code == 200
assert client.post("/en/packaging-selector", data={"csrf_token": csrf, "category": "Airless", "capacity": "30ml", "material": "PP", "quantity": 10000}).status_code == 200
assert client.post("/en/cost-estimator", data={"csrf_token": csrf, "product_id": product_id, "quantity": 10000}).status_code == 200
assert client.post("/admin/distributors", data={"csrf_token": csrf, "name": "测试渠道商", "company_id": company_id, "country": "德国", "annual_target": 100000, "status": "评估中"}).status_code == 302
assert client.post("/admin/quality", data={"csrf_token": csrf, "company_id": company_id, "category": "泄漏", "severity": "重大", "description": "测试质量问题", "status": "调查中"}).status_code == 302
assert client.post("/admin/translations", data={"csrf_token": csrf, "product_id": product_id, "language": "de"}).status_code == 302
with app.app_context():
    translation_id = get_db().execute("SELECT id FROM product_translations WHERE product_id=? AND language='de'", (product_id,)).fetchone()["id"]
assert client.post(f"/admin/translations/{translation_id}/review", data={"csrf_token": csrf, "name": "30ml Airless-Flasche", "summary": "Geprüfte Zusammenfassung", "description": "Geprüfte Beschreibung", "status": "已批准"}).status_code == 302
assert client.get("/language/de/products/30ml-airless-bottle").status_code == 301
assert client.get("/de/products/30ml-airless-bottle").status_code == 200
assert b"30ml Airless-Flasche" in client.get("/de/products").data
assert b"30ml Airless-Flasche" in client.get("/de/").data
assert client.post(f"/admin/products/{product_id}/generate", data={"csrf_token": csrf}).status_code == 302
assert client.post("/admin/operations", data={"csrf_token": csrf, "kind": "sample", "opportunity_id": opportunity_id, "items": "三件样品", "status": "待确认"}).status_code == 302
assert client.post("/admin/operations", data={"csrf_token": csrf, "kind": "order", "opportunity_id": opportunity_id, "amount": 4200, "currency": "USD", "gross_margin": 1200, "paid_amount": 0, "payment_status": "待付款", "delivery_status": "待生产"}).status_code == 302
with app.app_context():
    sample_id = get_db().execute("SELECT id FROM samples ORDER BY id DESC LIMIT 1").fetchone()["id"]
    order_id = get_db().execute("SELECT id FROM orders ORDER BY id DESC LIMIT 1").fetchone()["id"]
assert client.post(f"/admin/samples/{sample_id}/update", data={"csrf_token": csrf, "status": "运输中", "approval_status": "已批准", "sample_fee": 20, "shipping_fee": 45, "courier": "DHL", "tracking_no": "TEST123"}).status_code == 302
assert client.post(f"/admin/orders/{order_id}/payment", data={"csrf_token": csrf, "amount": 1000, "currency": "USD", "payment_date": "2026-09-14", "method": "电汇"}).status_code == 302
for path in ["/admin/users", "/admin/catalog-rules", "/admin/auto-quote", "/admin/quality", "/admin/distributors", "/admin/translations", "/admin/system", "/en/packaging-selector", "/en/cost-estimator", "/robots.txt", "/sitemap.xml", "/en/privacy"]:
    assert client.get(path).status_code == 200, path
backup = client.post("/admin/system/backup", data={"csrf_token": csrf})
assert backup.status_code == 200 and "application/zip" in backup.content_type

response = client.post("/admin/users", data={"csrf_token": csrf, "username": "sales_test", "password": "sales-password-123", "role": "销售"})
assert response.status_code == 302

sales = app.test_client()
sales.get("/admin/login")
with sales.session_transaction() as sales_session:
    sales_csrf = sales_session["csrf_token"]
assert sales.post("/admin/login", data={"csrf_token": sales_csrf, "username": "sales_test", "password": "sales-password-123"}).status_code == 302
assert sales.get("/admin/companies").status_code == 200
assert sales.get("/admin/users").status_code == 403

response = client.post(
    "/en/request-quote",
    data={
        "csrf_token": csrf,
        "company_name": "海外测试品牌",
        "contact_name": "Test Buyer",
        "email": "buyer@example.com",
        "country": "United States",
        "company_type": "Beauty brand",
        "product": "Airless bottle",
        "quantity": "10000",
        "source": "谷歌广告",
        "consent": "yes",
    },
)
assert response.status_code == 200
assert b"REQUEST RECEIVED" in response.data

print("全部冒烟测试通过")


# V4 public experience and content management
assert client.get("/?lang=zh").status_code == 301
assert client.get("/?lang=zh").headers["Location"].endswith("/zh/")
assert client.get("/admin/content").status_code == 200
response = client.post(
    "/admin/content",
    data={
        "csrf_token": csrf,
        "language": "en",
        "hero_kicker": "TEST KICKER",
        "hero_title": "Test launch headline",
        "hero_body": "Test content body",
        "metric_1_value": "24h", "metric_1_label": "response",
        "metric_2_value": "12+", "metric_2_label": "finishes",
        "metric_3_value": "100%", "metric_3_label": "verification",
        "video_title": "Factory story", "video_body": "Visible manufacturing proof",
        "cta_title": "Start the test project", "cta_body": "Testing CMS content",
        "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "action": "publish",
    },
    follow_redirects=False,
)
assert response.status_code == 302
assert b"Test launch headline" in client.get("/en/").data
assert b"youtube.com/embed/dQw4w9WgXcQ" in client.get("/en/").data


# V4 localized routing, privacy and draft workflow
for language in ("en", "zh", "es", "pt", "fr", "de", "ar", "ja", "ko", "ru"):
    assert client.get(f"/{language}/").status_code == 200
    assert client.get(f"/{language}/products").status_code == 200
    assert client.get(f"/{language}/privacy").status_code == 200

draft_response = client.post(
    "/admin/content",
    data={
        "csrf_token": csrf, "language": "en", "action": "draft",
        "hero_kicker": "DRAFT ONLY", "hero_title": "Unpublished draft",
        "hero_body": "This must stay out of the live page",
        "metric_1_value": "1", "metric_1_label": "one",
        "metric_2_value": "2", "metric_2_label": "two",
        "metric_3_value": "3", "metric_3_label": "three",
        "video_title": "Draft video", "video_body": "Draft",
        "video_url": "", "cta_title": "Draft CTA", "cta_body": "Draft",
    },
    follow_redirects=False,
)
assert draft_response.status_code == 302
assert b"Unpublished draft" not in client.get("/en/").data
assert b"Unpublished draft" in client.get("/admin/content/preview/en").data
with app.app_context():
    assert get_db().execute("SELECT COUNT(*) n FROM content_versions").fetchone()["n"] >= 1

missing_consent = client.post(
    "/en/request-quote",
    data={"csrf_token": csrf, "company_name": "No consent", "contact_name": "Buyer", "email": "buyer@example.com", "product": "Bottle"},
)
assert missing_consent.status_code == 200
assert b"privacy consent" in missing_consent.data
print("V4 launch-hardening tests passed")


# V4.2 canonical routing and localized static interface
legacy = client.get("/products?lang=de&category=Airless%20bottle")
assert legacy.status_code == 301
assert "/de/products" in legacy.headers["Location"]
german_products = client.get("/de/products")
assert b'<html lang="de"' in german_products.data
assert b"Spezifikationen ansehen" in german_products.data
assert b'rel="canonical"' in german_products.data
assert german_products.data.count(b'hreflang=') >= 11
chinese_quote = client.get("/zh/request-quote")
assert "公司名称".encode() in chinese_quote.data
assert "我同意银彩".encode() in chinese_quote.data
analytics_page = client.get("/en/")
assert b"googletagmanager.com/gtag/js" not in analytics_page.data
print("V4.2 localization and canonical tests passed")


# V4.2 role permission matrix and interactive workflow verification
role_accounts = {
    "海外负责人": ("overseas_test", "Overseas-role-2026!"),
    "产品技术": ("product_test", "Product-role-2026!"),
    "质量": ("quality_test", "Quality-role-2026!"),
    "内容运营": ("content_test", "Content-role-2026!"),
    "财务": ("finance_test", "Finance-role-2026!"),
    "交付": ("delivery_test", "Delivery-role-2026!"),
}
for role, (username, password) in role_accounts.items():
    response = client.post(
        "/admin/users",
        data={"csrf_token": csrf, "username": username, "password": password, "role": role},
        follow_redirects=False,
    )
    assert response.status_code == 302, (role, response.status_code)

def login_as(username, password):
    role_client = app.test_client()
    role_client.get("/admin/login")
    with role_client.session_transaction() as role_session:
        login_csrf = role_session["csrf_token"]
    response = role_client.post(
        "/admin/login",
        data={"csrf_token": login_csrf, "username": username, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 302, username
    with role_client.session_transaction() as role_session:
        assert role_session["username"] == username
        return role_client, role_session["csrf_token"]

role_accounts["销售"] = ("sales_test", "sales-password-123")
role_clients = {role: login_as(*account) for role, account in role_accounts.items()}

area_routes = {
    "dashboard": "/admin",
    "acquisition": "/admin/acquisition",
    "companies": "/admin/companies",
    "opportunities": "/admin/opportunities",
    "operations": "/admin/operations",
    "inquiries": "/admin/inquiries",
    "catalog": "/admin/products",
    "content": "/admin/content",
    "quality": "/admin/quality",
    "distributors": "/admin/distributors",
    "intelligence": "/admin/intelligence",
    "translations": "/admin/translations",
    "users": "/admin/users",
}
expected_areas = {
    "海外负责人": {"dashboard","acquisition","companies","opportunities","operations","inquiries","catalog","content","quality","distributors","intelligence","translations"},
    "销售": {"dashboard","acquisition","companies","opportunities","operations","inquiries","intelligence"},
    "产品技术": {"dashboard","catalog","translations","intelligence"},
    "质量": {"dashboard","catalog","operations","quality"},
    "内容运营": {"dashboard","acquisition","catalog","content","translations"},
    "财务": {"dashboard","operations","intelligence"},
    "交付": {"dashboard","operations","quality"},
}
for role, (role_client, role_csrf) in role_clients.items():
    for area, path in area_routes.items():
        response = role_client.get(path)
        expected = 200 if area in expected_areas[role] else 403
        assert response.status_code == expected, (role, area, response.status_code)
    nav = role_client.get("/admin").data.split(b"<nav>", 1)[1].split(b"</nav>", 1)[0]
    assert b'href="/admin/users"' not in nav
    if "catalog" not in expected_areas[role]:
        assert b'href="/admin/products"' not in nav
    if "companies" not in expected_areas[role]:
        assert b'href="/admin/companies"' not in nav
    if "content" not in expected_areas[role]:
        assert b'href="/admin/content"' not in nav

overseas, overseas_csrf = role_clients["海外负责人"]
assert overseas.post("/admin/companies", data={"csrf_token": overseas_csrf, "name": "海外角色测试客户", "country": "Germany"}).status_code == 302

sales_client, sales_role_csrf = role_clients["销售"]
assert sales_client.post(f"/admin/opportunities/{opportunity_id}/stage", data={"csrf_token": sales_role_csrf, "stage": "样品项目"}).status_code == 302
assert sales_client.post(f"/admin/products/{product_id}/generate", data={"csrf_token": sales_role_csrf}).status_code == 403

product_client, product_csrf = role_clients["产品技术"]
assert product_client.post(f"/admin/products/{product_id}/generate", data={"csrf_token": product_csrf}).status_code == 302

quality_client, quality_csrf = role_clients["质量"]
assert quality_client.post("/admin/quality", data={"csrf_token": quality_csrf, "company_id": company_id, "category": "角色测试", "severity": "一般", "description": "质量岗位交互验证", "status": "调查中"}).status_code == 302

content_client, content_csrf = role_clients["内容运营"]
assert content_client.post("/admin/content", data={
    "csrf_token": content_csrf, "language": "zh", "action": "draft",
    "hero_kicker": "角色测试草稿", "hero_title": "内容运营交互验证", "hero_body": "仅保存草稿",
    "metric_1_value": "1", "metric_1_label": "测试", "metric_2_value": "2", "metric_2_label": "测试",
    "metric_3_value": "3", "metric_3_label": "测试", "video_title": "测试", "video_body": "测试",
    "video_url": "", "cta_title": "测试", "cta_body": "测试",
}).status_code == 302
assert "内容运营交互验证".encode() in content_client.get("/admin/content/preview/zh").data

finance_client, finance_csrf = role_clients["财务"]
assert finance_client.post(f"/admin/orders/{order_id}/payment", data={"csrf_token": finance_csrf, "amount": 10, "currency": "USD", "payment_date": "2026-09-14", "method": "角色测试"}).status_code == 302

delivery_client, delivery_csrf = role_clients["交付"]
assert delivery_client.post(f"/admin/samples/{sample_id}/update", data={"csrf_token": delivery_csrf, "status": "已签收", "approval_status": "已批准", "feedback": "交付岗位交互验证"}).status_code == 302

with app.app_context():
    db = get_db()
    assert db.execute("SELECT COUNT(*) n FROM companies WHERE name='海外角色测试客户'").fetchone()["n"] == 1
    assert db.execute("SELECT stage FROM opportunities WHERE id=?", (opportunity_id,)).fetchone()["stage"] == "样品项目"
    assert db.execute("SELECT COUNT(*) n FROM complaints WHERE description='质量岗位交互验证'").fetchone()["n"] == 1
    assert db.execute("SELECT COUNT(*) n FROM payments WHERE method='角色测试'").fetchone()["n"] == 1
    assert db.execute("SELECT feedback FROM samples WHERE id=?", (sample_id,)).fetchone()["feedback"] == "交付岗位交互验证"

print("V4.2 role matrix and interaction tests passed")


# Extended interaction coverage: uploads, imports, APIs, restore, passwords and session exit
valid_png = b"\x89PNG\r\n\x1a\n" + b"verified-image-payload"
edit_response = client.post(
    f"/admin/products/{product_id}/edit",
    data={
        "csrf_token": csrf, "name": "30ml Airless Bottle", "category": "Airless bottle",
        "capacity": "30ml", "material": "PP", "moq": "1000", "published": "on",
        "summary": "Edited through interaction test",
        "image": (io.BytesIO(valid_png), "verified.png"),
    },
    content_type="multipart/form-data",
)
assert edit_response.status_code == 302
with app.app_context():
    uploaded_image = get_db().execute("SELECT image FROM products WHERE id=?", (product_id,)).fetchone()["image"]
assert uploaded_image and client.get(f"/uploads/{uploaded_image}").status_code == 200

bad_upload = client.post(
    "/admin/products",
    data={"csrf_token": csrf, "name": "Rejected upload", "published": "on", "image": (io.BytesIO(b"not-an-image"), "fake.png")},
    content_type="multipart/form-data",
)
assert bad_upload.status_code == 302
with app.app_context():
    assert get_db().execute("SELECT COUNT(*) n FROM products WHERE name='Rejected upload'").fetchone()["n"] == 0

quote_with_attachment = client.post(
    "/en/request-quote",
    data={
        "csrf_token": csrf, "company_name": "Attachment Test Brand", "contact_name": "Buyer",
        "email": "attachment@example.com", "product": "Airless bottle", "quantity": "5000",
        "consent": "yes", "lang": "en",
        "reference_file": (io.BytesIO(b"%PDF-1.4\nverified reference"), "reference.pdf"),
    },
    content_type="multipart/form-data",
)
assert quote_with_attachment.status_code == 200 and b"REQUEST RECEIVED" in quote_with_attachment.data
with app.app_context():
    attachment_name = get_db().execute("SELECT attachment FROM inquiries WHERE email='attachment@example.com'").fetchone()["attachment"]
assert attachment_name and client.get(f"/uploads/{attachment_name}").status_code == 200

csv_payload = "company_name,country,contact_name,email\nCSV Role Company,France,CSV Buyer,csv@example.com\n".encode()
overseas, overseas_csrf = role_clients["海外负责人"]
csv_response = overseas.post(
    "/admin/acquisition",
    data={"csrf_token": overseas_csrf, "csv_file": (io.BytesIO(csv_payload), "leads.csv")},
    content_type="multipart/form-data",
)
assert csv_response.status_code == 302
with app.app_context():
    assert get_db().execute("SELECT COUNT(*) n FROM companies WHERE name='CSV Role Company'").fetchone()["n"] == 1

assert client.post("/api/v1/events", json={}).status_code == 400
assert client.post("/api/v1/events", json={"event_name": "interaction_test", "source": "ci"}).status_code == 201
assert client.post("/api/v1/leads", json={"company_name": "Unauthorized", "email": "no@example.com"}).status_code == 401
api_lead = client.post(
    "/api/v1/leads",
    headers={"Authorization": "Bearer test-api-token"},
    json={"company_name": "API Role Company", "contact_name": "API Buyer", "email": "api@example.com", "country": "Spain"},
)
assert api_lead.status_code == 201 and api_lead.get_json()["company_id"]
assert client.get(f"/api/v1/intelligence/company/{company_id}").status_code == 401
api_score = client.get(f"/api/v1/intelligence/company/{company_id}", headers={"Authorization": "Bearer test-api-token"})
assert api_score.status_code == 200 and 0 <= api_score.get_json()["score"] <= 100
assert client.get("/api/v1/intelligence/company/999999", headers={"Authorization": "Bearer test-api-token"}).status_code == 404

with app.app_context():
    version_id = get_db().execute("SELECT id FROM content_versions ORDER BY id DESC LIMIT 1").fetchone()["id"]
content_client, content_csrf = role_clients["内容运营"]
restore = content_client.post(f"/admin/content/restore/{version_id}", data={"csrf_token": content_csrf})
assert restore.status_code == 302
assert content_client.get("/admin/content/preview/en").status_code == 200

with app.app_context():
    task_id = get_db().execute("SELECT id FROM tasks WHERE status!='已完成' ORDER BY id DESC LIMIT 1").fetchone()["id"]
sales_client, sales_role_csrf = role_clients["销售"]
assert sales_client.post(f"/admin/tasks/{task_id}/complete", data={"csrf_token": sales_role_csrf}).status_code == 302
with app.app_context():
    assert get_db().execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()["status"] == "已完成"

finance_client, finance_csrf = role_clients["财务"]
with app.app_context():
    payment_count = get_db().execute("SELECT COUNT(*) n FROM payments WHERE order_id=?", (order_id,)).fetchone()["n"]
assert finance_client.post(f"/admin/orders/{order_id}/payment", data={"csrf_token": finance_csrf, "amount": -1}).status_code == 302
with app.app_context():
    assert get_db().execute("SELECT COUNT(*) n FROM payments WHERE order_id=?", (order_id,)).fetchone()["n"] == payment_count
assert finance_client.post("/admin/orders/999999/payment", data={"csrf_token": finance_csrf, "amount": 1}).status_code == 404

with app.app_context():
    product_user_id = get_db().execute("SELECT id FROM users WHERE username='product_test'").fetchone()["id"]
    old_hash = get_db().execute("SELECT password_hash FROM users WHERE id=?", (product_user_id,)).fetchone()["password_hash"]
assert client.post(f"/admin/users/{product_user_id}/password", data={"csrf_token": csrf, "password": "short"}).status_code == 302
with app.app_context():
    assert get_db().execute("SELECT password_hash FROM users WHERE id=?", (product_user_id,)).fetchone()["password_hash"] == old_hash
assert client.post(f"/admin/users/{product_user_id}/password", data={"csrf_token": csrf, "password": "New-product-role-2026!"}).status_code == 302
new_product_client, _ = login_as("product_test", "New-product-role-2026!")
assert new_product_client.get("/admin/products").status_code == 200

logout_client, logout_csrf = login_as("delivery_test", "Delivery-role-2026!")
assert logout_client.post("/admin/logout", data={"csrf_token": logout_csrf}).status_code == 302
assert logout_client.get("/admin").status_code == 302

assert client.get(f"/admin/products/{product_id}/edit").status_code == 200
assert client.get(f"/admin/companies/{company_id}").status_code == 200
print("V4.2 extended interaction tests passed")


# V4.2 structured page CMS: every customer-facing section is editable, previewable and publishable.
cms_cases = {
    "solutions": ("solutions_title", "CMS Solutions Proof", "/en/", b"CMS Solutions Proof"),
    "capabilities": ("capabilities_title", "CMS Capability Proof", "/en/", b"CMS Capability Proof"),
    "products": ("products_title", "CMS Product Centre Proof", "/en/products", b"CMS Product Centre Proof"),
    "selector": ("selector_title", "CMS Selector Proof", "/en/packaging-selector", b"CMS Selector Proof"),
    "cost": ("cost_title", "CMS Cost Proof", "/en/cost-estimator", b"CMS Cost Proof"),
}
for cms_page, (field, value, public_path, expected_text) in cms_cases.items():
    editor = content_client.get(f"/admin/content?language=en&page={cms_page}")
    assert editor.status_code == 200 and value.replace("Proof", "").encode() not in editor.data
    response = content_client.post(
        "/admin/content",
        data={"csrf_token": content_csrf, "language": "en", "page": cms_page, "action": "draft", field: value},
        follow_redirects=False,
    )
    assert response.status_code == 302
    preview = content_client.get(f"/admin/content/preview/en/{cms_page}")
    assert preview.status_code == 200 and expected_text in preview.data
    assert expected_text not in client.get(public_path).data
    response = content_client.post(
        "/admin/content",
        data={"csrf_token": content_csrf, "language": "en", "page": cms_page, "action": "publish", field: value},
        follow_redirects=False,
    )
    assert response.status_code == 302 and expected_text in client.get(public_path).data

workspace = content_client.get("/admin/content?language=en&page=products").data
for label in ("首页首屏", "解决方案", "能力与流程", "产品中心", "包装选择器", "成本估算"):
    assert label.encode() in workspace
assert b"/admin/products" in workspace and b"/admin/translations" in workspace
print("V4.2 structured page CMS tests passed")
