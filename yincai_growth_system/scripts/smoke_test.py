import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

temporary = tempfile.TemporaryDirectory()
os.environ["DATABASE_PATH"] = os.path.join(temporary.name, "test.db")
os.environ["UPLOAD_FOLDER"] = os.path.join(temporary.name, "uploads")
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ADMIN_USERNAME"] = "tester"
os.environ["ADMIN_PASSWORD"] = "safe-test-password"

from app import app, get_db

client = app.test_client()

assert client.get("/api/v1/health").status_code == 200
assert client.get("/").status_code == 200
assert client.get("/products").status_code == 200
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
assert client.post("/packaging-selector", data={"csrf_token": csrf, "category": "Airless", "capacity": "30ml", "material": "PP", "quantity": 10000}).status_code == 200
assert client.post("/cost-estimator", data={"csrf_token": csrf, "product_id": product_id, "quantity": 10000}).status_code == 200
assert client.post("/admin/distributors", data={"csrf_token": csrf, "name": "测试渠道商", "company_id": company_id, "country": "德国", "annual_target": 100000, "status": "评估中"}).status_code == 302
assert client.post("/admin/quality", data={"csrf_token": csrf, "company_id": company_id, "category": "泄漏", "severity": "重大", "description": "测试质量问题", "status": "调查中"}).status_code == 302
assert client.post("/admin/translations", data={"csrf_token": csrf, "product_id": product_id, "language": "de"}).status_code == 302
with app.app_context():
    translation_id = get_db().execute("SELECT id FROM product_translations WHERE product_id=? AND language='de'", (product_id,)).fetchone()["id"]
assert client.post(f"/admin/translations/{translation_id}/review", data={"csrf_token": csrf, "name": "30ml Airless-Flasche", "summary": "Geprüfte Zusammenfassung", "description": "Geprüfte Beschreibung", "status": "已批准"}).status_code == 302
assert client.get("/language/de/products/30ml-airless-bottle").status_code == 200
assert client.post(f"/admin/products/{product_id}/generate", data={"csrf_token": csrf}).status_code == 302
assert client.post("/admin/operations", data={"csrf_token": csrf, "kind": "sample", "opportunity_id": opportunity_id, "items": "三件样品", "status": "待确认"}).status_code == 302
assert client.post("/admin/operations", data={"csrf_token": csrf, "kind": "order", "opportunity_id": opportunity_id, "amount": 4200, "currency": "USD", "gross_margin": 1200, "paid_amount": 0, "payment_status": "待付款", "delivery_status": "待生产"}).status_code == 302
with app.app_context():
    sample_id = get_db().execute("SELECT id FROM samples ORDER BY id DESC LIMIT 1").fetchone()["id"]
    order_id = get_db().execute("SELECT id FROM orders ORDER BY id DESC LIMIT 1").fetchone()["id"]
assert client.post(f"/admin/samples/{sample_id}/update", data={"csrf_token": csrf, "status": "运输中", "approval_status": "已批准", "sample_fee": 20, "shipping_fee": 45, "courier": "DHL", "tracking_no": "TEST123"}).status_code == 302
assert client.post(f"/admin/orders/{order_id}/payment", data={"csrf_token": csrf, "amount": 1000, "currency": "USD", "payment_date": "2026-09-14", "method": "电汇"}).status_code == 302
for path in ["/admin/users", "/admin/catalog-rules", "/admin/auto-quote", "/admin/quality", "/admin/distributors", "/admin/translations", "/admin/system", "/packaging-selector", "/cost-estimator", "/robots.txt", "/sitemap.xml", "/privacy"]:
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
    "/request-quote",
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
    },
)
assert response.status_code == 200
assert b"REQUEST RECEIVED" in response.data

print("全部冒烟测试通过")
