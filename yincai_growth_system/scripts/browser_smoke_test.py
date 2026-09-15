import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
temporary = tempfile.TemporaryDirectory()
environment = os.environ.copy()
environment.update({
    "APP_ENV": "test",
    "DATABASE_PATH": str(Path(temporary.name) / "browser.db"),
    "UPLOAD_FOLDER": str(Path(temporary.name) / "uploads"),
    "SECRET_KEY": "browser-test-secret-key",
    "ADMIN_USERNAME": "browser_admin",
    "ADMIN_PASSWORD": "Browser-admin-2026!",
    "ANALYTICS_ID": "G-TEST123",
})
server = subprocess.Popen(
    [sys.executable, "-c", "from app import app; app.run(host='127.0.0.1', port=8765, use_reloader=False)"],
    cwd=ROOT,
    env=environment,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.STDOUT,
)
base_url = "http://127.0.0.1:8765"

try:
    for _ in range(60):
        try:
            urllib.request.urlopen(base_url + "/api/v1/health", timeout=1)
            break
        except Exception:
            time.sleep(0.25)
    else:
        raise RuntimeError("Flask test server did not start")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()

        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        page.goto(base_url + "/en/")
        page.locator("[data-cookie-banner]").wait_for(state="visible")
        page.locator("[data-cookie-reject]").click()
        assert page.evaluate("localStorage.getItem('yc_cookie_consent')") == "essential"
        assert page.locator("[data-cookie-banner]").is_hidden()

        page.locator(".menu-toggle").click()
        assert page.locator(".main-nav").evaluate("node => node.classList.contains('open')")
        with page.expect_navigation():
            page.select_option("[data-language-select]", "/zh/")
        assert page.url.endswith("/zh/")
        assert page.locator("html").get_attribute("lang") == "zh"

        page.goto(base_url + "/en/packaging-selector")
        page.fill('input[name="use_case"]', "serum")
        page.fill('input[name="quantity"]', "5000")
        page.locator('form.tool-form button').click()
        page.wait_for_load_state("networkidle")
        assert page.locator(".manual-route").is_visible()

        page.goto(base_url + "/en/request-quote")
        page.fill('input[name="company_name"]', "Browser Test Brand")
        page.fill('input[name="contact_name"]', "Browser Buyer")
        page.fill('input[name="email"]', "browser@example.com")
        page.fill('input[name="product"]', "Airless bottle")
        page.check('input[name="consent"]')
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state("networkidle")
        assert page.locator(".thanks").is_visible()
        assert page.locator(".request-reference b").inner_text().startswith("YC-")

        page.goto(base_url + "/admin/login")
        page.fill('input[name="username"]', "browser_admin")
        page.fill('input[name="password"]', "Browser-admin-2026!")
        page.locator('form button').click()
        page.wait_for_url("**/admin")
        assert page.locator(".sidebar").is_visible()
        cms_response = page.goto(base_url + "/admin/content", wait_until="networkidle")
        assert cms_response.status == 200, (cms_response.status, page.url)
        draft_button = page.locator('button[name="action"][value="draft"]')
        publish_button = page.locator('button[name="action"][value="publish"]')
        preview_link = page.locator('a[href*="/admin/content/preview/"]')
        assert draft_button.count() == publish_button.count() == preview_link.count() == 1
        draft_button.scroll_into_view_if_needed()
        assert draft_button.is_visible() and publish_button.is_visible() and preview_link.is_visible()
        context.close()

        consent_context = browser.new_context()
        consent_page = consent_context.new_page()
        analytics_requests = []
        consent_page.route("https://www.googletagmanager.com/**", lambda route: (analytics_requests.append(route.request.url), route.fulfill(status=200, content_type="application/javascript", body="")))
        consent_page.goto(base_url + "/en/")
        consent_page.locator("[data-cookie-accept]").click()
        consent_page.wait_for_timeout(300)
        assert consent_page.evaluate("localStorage.getItem('yc_cookie_consent')") == "accepted"
        assert analytics_requests and "G-TEST123" in analytics_requests[0]
        consent_context.close()
        browser.close()

    print("V4.2 real browser interaction tests passed")
finally:
    server.terminate()
    try:
        server.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server.kill()
    temporary.cleanup()
