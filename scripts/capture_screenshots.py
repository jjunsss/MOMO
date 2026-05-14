"""Capture README screenshots from the running Streamlit app.

Captures in English mode (the README uses the English captures as primary).
Also kicks off a fresh run against an existing video so we can capture the
mid-run progress card.

Prerequisites:
    - Streamlit server running on http://localhost:8501
    - `playwright` installed in the active venv
    - `playwright install chromium` has been run
    - At least one media file already sitting in `videos/`

Usage:
    .venv/bin/python scripts/capture_screenshots.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright


BASE_URL = "http://localhost:8501"
OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
VIEWPORT = {"width": 1440, "height": 900}


def _settle(page: Page, extra_ms: int = 600) -> None:
    """Wait for Streamlit to finish a rerun and render."""
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except PlaywrightTimeoutError:
        pass
    page.wait_for_timeout(extra_ms)


def _save(page: Page, name: str, *, full_page: bool = False, clip: dict | None = None) -> None:
    path = OUT_DIR / name
    page.screenshot(path=str(path), full_page=full_page, clip=clip)
    print("  → wrote", path.relative_to(OUT_DIR.parents[1]))


def _switch_to_english(page: Page) -> None:
    sidebar_en = page.locator(
        "section[data-testid='stSidebar']"
    ).get_by_text("English", exact=True).first
    sidebar_en.click()
    _settle(page, 1000)


def capture() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport=VIEWPORT, locale="en-US", device_scale_factor=2
        )
        page = context.new_page()

        print("→ navigating to", BASE_URL)
        page.goto(BASE_URL, wait_until="domcontentloaded")
        # Wait for the Korean default heading to appear, then flip the
        # sidebar language toggle to English for every subsequent capture.
        page.wait_for_selector("text=새 회의 요약하기", timeout=15000)
        _settle(page, 600)
        _switch_to_english(page)
        page.wait_for_selector("text=Summarize a new meeting", timeout=10000)

        # ── 1. Home (English)
        print("\n1) home (English)")
        _save(page, "01-home.png")

        # ── 2. Summary guide close-up
        print("\n2) summary guide close-up")
        guide = page.locator("text=Tell the AI what to focus on").first
        guide.scroll_into_view_if_needed()
        _settle(page, 400)
        bbox = guide.evaluate(
            "el => { const c = el.closest('[data-testid=\"stVerticalBlockBorderWrapper\"]')"
            "      || el.closest('[data-testid=\"stVerticalBlock\"]')"
            "      || el; const r = c.getBoundingClientRect();"
            "  return {x: r.left, y: r.top, width: r.width, height: r.height}; }"
        )
        if bbox and bbox["width"] > 100 and bbox["height"] > 100:
            clip = {
                "x": max(0, bbox["x"]),
                "y": max(0, bbox["y"]),
                "width": min(VIEWPORT["width"], bbox["width"]),
                "height": min(VIEWPORT["height"], bbox["height"]),
            }
            _save(page, "02-summary-guide.png", clip=clip)
        else:
            _save(page, "02-summary-guide.png")

        # ── 3. Template applied (Research)
        print("\n3) template applied (Research)")
        page.get_by_role("button", name="📚 Research").click()
        _settle(page, 1200)
        page.locator("text=Tell the AI what to focus on").first.scroll_into_view_if_needed()
        _settle(page, 400)
        _save(page, "03-template-applied.png")

        # ── 4. Past meeting result (Summary tab)
        print("\n4) past meeting result")
        history_btn = page.locator(
            "section[data-testid='stSidebar'] button"
        ).filter(has_text="Screen_Recording_20260424").first
        history_btn.click()
        _settle(page, 1200)
        page.wait_for_selector("text=Watch with evidence", timeout=10000)
        _save(page, "04-result-summary.png")

        # ── 5. Playback tab with chips
        print("\n5) playback tab")
        page.get_by_role("tab", name="▶ Watch with evidence").click()
        _settle(page, 2500)
        page.wait_for_selector("button:has-text('▶ 00:')", timeout=10000)
        page.evaluate(
            "() => { const el = [...document.querySelectorAll('h3')]"
            ".find(h => h.textContent.includes('Key topics'));"
            "if (el) { el.scrollIntoView({block: 'start', behavior: 'instant'}); } }"
        )
        _settle(page, 700)
        _save(page, "05-playback-chips.png")

        # ── 6. Progress card mid-run.
        # Click "New meeting", select an existing video, hit Start, then wait
        # until enough stages have completed for the card to be visually
        # informative (at least one ✅ check mark visible).
        print("\n6) progress card (kicking off a run on the cached video)")
        page.get_by_role("button", name="➕ New meeting").click()
        _settle(page, 800)
        page.get_by_role("tab", name="📁 Pick from videos/").click()
        _settle(page, 800)
        # Click the placeholder of the selectbox — Streamlit's BaseWeb select
        # exposes the "Choose a file" placeholder as a visible target.
        choose_target = page.get_by_text("Choose a file", exact=True).first
        choose_target.scroll_into_view_if_needed()
        _settle(page, 300)
        choose_target.click()
        _settle(page, 500)
        page.locator('[role="option"]').first.click()
        _settle(page, 800)
        # Click Start
        page.get_by_role("button", name="🚀 Start summarizing").click()
        print("   waiting for the progress card to populate…")
        page.wait_for_selector("text=Analyzing the meeting", timeout=20000)
        # Wait until we see at least 3 ✅ checkmarks (transcript cached path
        # should march through prepare/audio/transcribe quickly, leaving
        # synthesize as the in-flight stage).
        for _ in range(60):
            done_count = page.locator("text=✅").count()
            if done_count >= 3:
                break
            page.wait_for_timeout(1000)
        _settle(page, 800)
        _save(page, "06-progress.png")

        browser.close()
        print("\n✓ done — see docs/screenshots/")
    return 0


if __name__ == "__main__":
    sys.exit(capture())
