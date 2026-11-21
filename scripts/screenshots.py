"""Real UI capture with Playwright: the RAG API's Swagger page answering a question through the ingress."""
from __future__ import annotations

from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"


def shot(page, name, full=False):
    p = OUT / f"{name}.png"
    page.screenshot(path=str(p), full_page=full)
    im = Image.open(p)
    if im.width > 1440:
        im.resize((1440, round(im.height * 1440 / im.width)), Image.LANCZOS).save(p, optimize=True)
    print("saved", p.relative_to(ROOT))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if True:
        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
            page.goto("http://127.0.0.1:48080/docs")
            page.wait_for_timeout(2500)
            page.get_by_text("/v1/ask", exact=True).first.click()
            page.get_by_role("button", name="Try it out").first.click()
            page.locator("textarea.body-param__text").first.fill(
                '{"question": "What PSI value triggers retraining in the churn MLOps pipeline?"}')
            page.get_by_role("button", name="Execute").first.click()
            page.wait_for_selector(".live-responses-table .response-col_status", timeout=120000)
            page.wait_for_timeout(1000)
            page.locator(".live-responses-table").first.scroll_into_view_if_needed()
            shot(page, "rag_api_swagger_ask", full=True)
            b.close()


if __name__ == "__main__":
    main()
