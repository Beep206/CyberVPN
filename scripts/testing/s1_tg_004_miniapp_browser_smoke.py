#!/usr/bin/env python3
"""Browser smoke for S1-TG-004 Mini App cabinet routes.

The check captures mobile screenshots for home/plans/payments/devices/profile/
wallet against a local Next.js server and a local mock API. Telegram initData
auto-auth is intentionally not injected here; S1-TG-005 owns the identity/linking
evidence. This keeps S1-TG-004 focused on the Mini App cabinet surface.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, sync_playwright


DEFAULT_BASE_URL = "http://127.0.0.1:9001"
DEFAULT_EVIDENCE_DIR = "docs/cybervpn_stage1_launch_docs/evidence/s1-tg-004"

IGNORED_CONSOLE_FRAGMENTS = (
    "Telegram WebApp not available. Running outside Telegram Mini App context.",
    "Failed to load resource: the server responded with a status of 404",
    "favicon.ico",
)


@dataclass(frozen=True)
class RouteCheck:
    name: str
    path: str
    required_text: tuple[str, ...]


@dataclass
class RouteResult:
    name: str
    url: str
    screenshot: str
    text_dump: str
    required_text: list[str]
    console_errors: list[str] = field(default_factory=list)
    page_errors: list[str] = field(default_factory=list)


ROUTES = (
    RouteCheck(
        name="home",
        path="/en-EN/miniapp/home",
        required_text=("Subscription Active", "Plus Beta", "VPN Configuration", "Usage Statistics"),
    ),
    RouteCheck(
        name="plans",
        path="/en-EN/miniapp/plans",
        required_text=("Choose Your Plan", "Basic", "Plus", "180 days"),
    ),
    RouteCheck(
        name="payments",
        path="/en-EN/miniapp/payments",
        required_text=("Payment History", "Plus Beta 30 days", "$14.99"),
    ),
    RouteCheck(
        name="devices",
        path="/en-EN/miniapp/devices",
        required_text=("Active Devices", "Chrome on Windows", "Current"),
    ),
    RouteCheck(
        name="profile",
        path="/en-EN/miniapp/profile",
        required_text=("s1_tg_004", "Security", "Payment History", "Partner Dashboard"),
    ),
    RouteCheck(
        name="wallet",
        path="/en-EN/miniapp/wallet",
        required_text=("Wallet Balance", "$27.50", "Transaction History", "S1 local wallet deposit"),
    ),
)


def is_ignored_console(message: str) -> bool:
    return any(fragment in message for fragment in IGNORED_CONSOLE_FRAGMENTS)


def ensure_route(page: Page, route: RouteCheck, base_url: str, evidence_dir: Path) -> RouteResult:
    url = f"{base_url.rstrip('/')}{route.path}"
    console_errors: list[str] = []
    page_errors: list[str] = []

    def on_console(msg: Any) -> None:
        if msg.type != "error":
            return
        text = msg.text
        if not is_ignored_console(text):
            console_errors.append(text)

    def on_page_error(exc: Exception) -> None:
        page_errors.append(str(exc))

    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except PlaywrightError:
            pass

        body = page.locator("body")
        for expected in route.required_text:
            body.get_by_text(expected, exact=False).first.wait_for(timeout=25_000)

        text = body.inner_text(timeout=10_000)
        normalized_text = text.casefold()
        missing = [
            expected
            for expected in route.required_text
            if expected.casefold() not in normalized_text
        ]
        if missing:
            raise AssertionError(f"{route.name} missing required text: {', '.join(missing)}")

        page.add_style_tag(
            content="""
            nextjs-portal,
            [data-nextjs-dialog-overlay],
            [data-nextjs-dev-tools-button],
            .tsqd-open-btn,
            .tsqd-open-btn-container,
            [data-next-badge-root] {
              display: none !important;
            }
            """
        )
        page.evaluate(
            """
            () => {
              for (const selector of ['nextjs-portal', '.tsqd-open-btn', '.tsqd-open-btn-container']) {
                for (const element of document.querySelectorAll(selector)) {
                  element.style.setProperty('display', 'none', 'important');
                }
              }
              for (const button of document.querySelectorAll('button')) {
                if (String(button.className).includes('fixed bottom-4 left-4')) {
                  button.style.setProperty('display', 'none', 'important');
                }
              }
            }
            """
        )

        screenshots_dir = evidence_dir / "screenshots"
        text_dir = evidence_dir / "route-text"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        text_dir.mkdir(parents=True, exist_ok=True)

        screenshot_path = screenshots_dir / f"{route.name}.png"
        text_path = text_dir / f"{route.name}.txt"
        page.screenshot(path=str(screenshot_path), full_page=True)
        text_path.write_text(text, encoding="utf-8")

        return RouteResult(
            name=route.name,
            url=url,
            screenshot=str(screenshot_path),
            text_dump=str(text_path),
            required_text=list(route.required_text),
            console_errors=console_errors,
            page_errors=page_errors,
        )
    finally:
        page.remove_listener("console", on_console)
        page.remove_listener("pageerror", on_page_error)


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture S1-TG-004 Mini App cabinet screenshots.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--evidence-dir", default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--chrome-bin", default="/usr/bin/google-chrome")
    args = parser.parse_args()

    evidence_dir = Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    results: list[RouteResult] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=args.chrome_bin,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            color_scheme="dark",
            locale="en-US",
        )
        context.add_init_script(
            """
            (() => {
              const noop = () => {};
              window.Telegram = {
                WebApp: {
                  initData: '',
                  initDataUnsafe: {
                    user: {
                      id: 123456789,
                      first_name: 'Sasha',
                      username: 's1_tg_004',
                      language_code: 'en'
                    },
                    start_param: 's1-tg-004'
                  },
                  colorScheme: 'dark',
                  themeParams: {
                    bg_color: '#05070d',
                    text_color: '#ffffff',
                    hint_color: '#7b8794',
                    link_color: '#00ffff',
                    button_color: '#00ffff',
                    button_text_color: '#000000'
                  },
                  isExpanded: true,
                  viewportHeight: 844,
                  viewportStableHeight: 844,
                  ready: noop,
                  expand: noop,
                  close: noop,
                  enableClosingConfirmation: noop,
                  disableClosingConfirmation: noop,
                  showPopup: noop,
                  showAlert: noop,
                  showConfirm: () => Promise.resolve(true),
                  openLink: noop,
                  openTelegramLink: noop,
                  openInvoice: (_url, callback) => callback && callback('pending'),
                  HapticFeedback: {
                    impactOccurred: noop,
                    notificationOccurred: noop,
                    selectionChanged: noop
                  },
                  BackButton: {
                    isVisible: false,
                    show: noop,
                    hide: noop,
                    onClick: noop,
                    offClick: noop
                  },
                  MainButton: {
                    isVisible: false,
                    isActive: false,
                    text: '',
                    color: '#00ffff',
                    textColor: '#000000',
                    isProgressVisible: false,
                    show: noop,
                    hide: noop,
                    enable: noop,
                    disable: noop,
                    showProgress: noop,
                    hideProgress: noop,
                    setText: noop,
                    onClick: noop,
                    offClick: noop
                  }
                }
              };
            })();
            """
        )
        page = context.new_page()
        try:
            for route in ROUTES:
                results.append(ensure_route(page, route, args.base_url, evidence_dir))
        finally:
            context.close()
            browser.close()

    summary = {
        "backlog_id": "S1-TG-004",
        "base_url": args.base_url,
        "telegram_runtime_injected": True,
        "telegram_init_data_injected": False,
        "telegram_identity_scope": "S1-TG-005",
        "viewport": {"width": 390, "height": 844, "device_scale_factor": 2},
        "routes": [asdict(result) for result in results],
    }
    summary_path = evidence_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    unexpected_console = [
        f"{result.name}: {message}"
        for result in results
        for message in result.console_errors
    ]
    page_errors = [
        f"{result.name}: {message}"
        for result in results
        for message in result.page_errors
    ]
    if unexpected_console or page_errors:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        raise SystemExit(
            "Unexpected browser errors:\n"
            + "\n".join(unexpected_console + page_errors)
        )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
