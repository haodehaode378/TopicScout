"""WeChat MP QR-code login — Playwright in background thread with ProactorEventLoop."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
from datetime import datetime
from typing import Optional

from .config import config
from .wx_token import WxCredentials, clear_credentials, save_credentials

logger = logging.getLogger(__name__)

WX_LOGIN_URL = "https://mp.weixin.qq.com/"
WX_HOME_URL = "https://mp.weixin.qq.com/cgi-bin/home"
QR_IMAGE_PATH = os.path.join(config.storage.data_dir, "wx_qrcode.png")


class WxLoginSession:
    """Singleton managing the QR login flow."""

    def __init__(self) -> None:
        self.status: str = "idle"  # idle | loading | qr_ready | success | error
        self.error_message: str = ""
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start_login(self) -> dict:
        """Start QR login in background thread. Returns initial status."""
        if self.status in ("loading", "qr_ready"):
            return {"status": self.status, "qr_url": "/api/wx/qrcode"}

        # Clean up old QR
        if os.path.exists(QR_IMAGE_PATH):
            os.remove(QR_IMAGE_PATH)

        self.status = "loading"
        self.error_message = ""
        self._stop_event.clear()

        self._thread = threading.Thread(target=self._run_login, daemon=True)
        self._thread.start()

        return {"status": "loading", "qr_url": "/api/wx/qrcode"}

    def get_status(self) -> dict:
        return {
            "status": self.status,
            "logged_in": self.status == "success",
            "error": self.error_message,
            "qr_exists": os.path.exists(QR_IMAGE_PATH),
        }

    def stop_login(self) -> None:
        self._stop_event.set()
        self.status = "idle"

    def _run_login(self) -> None:
        """Run Playwright login in a separate event loop (Proactor on Windows)."""
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            loop = asyncio.ProactorEventLoop()
        else:
            loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_login())
        except Exception as e:
            logger.exception("WeChat login failed")
            self.status = "error"
            self.error_message = str(e)
        finally:
            loop.close()

    async def _async_login(self) -> None:
        """Core async login flow using Playwright."""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()

            # Navigate to login page
            logger.info("[wx_auth] Opening mp.weixin.qq.com...")
            await page.goto(WX_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)

            # Wait for QR code to appear
            try:
                qr_selector = ".login__type__container__scan__qrcode"
                await page.wait_for_selector(qr_selector, timeout=15000)
            except Exception:
                # Try alternative selectors
                try:
                    await page.wait_for_selector("img[src*='qrcode']", timeout=5000)
                except Exception as e:
                    logger.warning(f"[wx_auth] QR selector not found, using full page screenshot: {e}")

            # Screenshot QR code
            os.makedirs(os.path.dirname(QR_IMAGE_PATH), exist_ok=True)
            try:
                qr_element = page.locator(".login__type__container__scan__qrcode")
                await qr_element.screenshot(path=QR_IMAGE_PATH)
            except Exception as e:
                logger.warning(f"[wx_auth] QR element screenshot failed, using full page: {e}")
                await page.screenshot(path=QR_IMAGE_PATH)

            self.status = "qr_ready"
            logger.info("[wx_auth] QR code ready, waiting for scan...")

            # Wait for navigation (user scans QR code) — 5 min timeout
            try:
                async with page.expect_navigation(timeout=300_000) as nav_info:
                    # Also poll for URL changes (some redirects don't trigger framenavigated)
                    pass
                response = await nav_info.value
                final_url = response.url if response else page.url
            except Exception as e:
                # Check if we ended up on the home page anyway
                logger.info(f"[wx_auth] Navigation wait ended: {e}")
                final_url = page.url

            if "home" in final_url or "cgi-bin/home" in final_url:
                logger.info("[wx_auth] Login successful!")

                # Extract token
                token = await self._extract_token(page)

                # Get cookies
                cookies = await context.cookies()
                cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)

                user_agent = await page.evaluate("navigator.userAgent")

                # Save credentials
                creds = WxCredentials(
                    token=token,
                    cookies=[{"name": c["name"], "value": c["value"], "domain": c.get("domain", "")} for c in cookies],
                    cookie_str=cookie_str,
                    user_agent=user_agent,
                    login_time=datetime.now().isoformat(),
                )
                save_credentials(creds)
                self.status = "success"
                logger.info(f"[wx_auth] Credentials saved, token={'yes' if token else 'no'}")
            else:
                self.status = "error"
                self.error_message = "登录超时或被取消"
                logger.warning(f"[wx_auth] Login failed, final URL: {final_url}")

            await browser.close()

        # Only clean up QR on error/success is handled by status — frontend checks status first
        if self.status != "success" and os.path.exists(QR_IMAGE_PATH):
            os.remove(QR_IMAGE_PATH)

    async def _extract_token(self, page) -> str:
        """Extract token from URL params, localStorage, or cookies."""
        # Try URL parameter
        url = page.url
        if "token=" in url:
            from urllib.parse import parse_qs, urlparse
            params = parse_qs(urlparse(url).query)
            tokens = params.get("token", [])
            if tokens:
                return tokens[0]

        # Try localStorage
        try:
            token = await page.evaluate("localStorage.getItem('token')")
            if token:
                return token
        except Exception as e:
            logger.debug(f"[wx_auth] localStorage token check failed: {e}")

        # Try cookies
        try:
            cookies = await page.context.cookies()
            for c in cookies:
                if c["name"] == "token":
                    return c["value"]
        except Exception as e:
            logger.debug(f"[wx_auth] Cookie token check failed: {e}")

        return ""


# Module-level singleton
_session = WxLoginSession()


def start_login() -> dict:
    return _session.start_login()


def get_status() -> dict:
    return _session.get_status()


def stop_login() -> None:
    _session.stop_login()
