#!/usr/bin/env python3
"""Capture README screenshots for examples/demo-ui (Playwright + Chromium)."""

from __future__ import annotations

import http.server
import os
import socketserver
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "demo-ui"
OUT = ROOT / "docs" / "images" / "screenshots"


def _serve_demo(port: int) -> socketserver.TCPServer:
    handler = http.server.SimpleHTTPRequestHandler
    server = socketserver.TCPServer(("127.0.0.1", port), handler)
    server.allow_reuse_address = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    port = 9877
    orig_cwd = Path.cwd()
    try:
        os.chdir(DEMO)
        server = _serve_demo(port)
        time.sleep(0.2)
        base = f"http://127.0.0.1:{port}/index.html"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                device_scale_factor=1,
            )
            page = context.new_page()

            page.goto(base, wait_until="networkidle", timeout=60_000)
            page.wait_for_timeout(400)
            page.screenshot(path=str(OUT / "01-dashboard-home.png"), full_page=True)

            page.goto(f"{base}?mode=sample", wait_until="networkidle", timeout=60_000)
            page.wait_for_timeout(400)
            page.screenshot(path=str(OUT / "02-dashboard-sample.png"), full_page=True)

            page.goto(f"{base}?mode=polling", wait_until="networkidle", timeout=60_000)
            page.wait_for_timeout(600)
            page.screenshot(path=str(OUT / "03-dashboard-polling.png"), full_page=True)

            browser.close()
        server.shutdown()
    finally:
        os.chdir(orig_cwd)

    print("Wrote:", list(OUT.glob("*.png")))


if __name__ == "__main__":
    main()
