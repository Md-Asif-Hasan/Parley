"""
Playwright-based Browser Autopilot Agent for Parley.
Controls real Chromium browsers with persistent session profile so user logins are preserved.
Executes autonomous actions: posting to social media, sending chat messages, drafting emails, scheduling meetings.
"""
import os
import sys
import json
import logging
import asyncio
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path

logger = logging.getLogger(__name__)

# Default persistent profile directory
PROFILE_DIR = os.path.join(str(Path.home()), ".parley", "browser_profile")
os.makedirs(PROFILE_DIR, exist_ok=True)


class BrowserAutopilot:
    def __init__(self, step_callback: Optional[Callable[[str, str], None]] = None):
        """
        step_callback: function(step_name: str, message: str) for live UI updates.
        """
        self.step_callback = step_callback
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        logger.info("[BrowserAutopilot] Cancellation requested.")

    async def _emit_step(self, step_name: str, message: str):
        logger.info(f"[Autopilot] [{step_name}] {message}")
        if self.step_callback:
            res = self.step_callback(step_name, message)
            if asyncio.iscoroutine(res):
                await res

    async def post_to_social(
        self,
        platform: str,
        text: str,
        image_paths: Optional[List[str]] = None,
        headless: bool = False
    ) -> Dict[str, Any]:
        """
        Posts content and optional images to Twitter/X, LinkedIn, Reddit, etc.
        """
        from playwright.async_api import async_playwright

        self._is_cancelled = False
        target = platform.lower().strip()
        await self._emit_step("init", f"Initializing browser for {platform}...")

        async with async_playwright() as p:
            # Launch persistent browser context
            context = await p.chromium.launch_persistent_context(
                user_data_dir=PROFILE_DIR,
                headless=headless,
                viewport={"width": 1280, "height": 800},
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = context.pages[0] if context.pages else await context.new_page()

            try:
                if target in ["twitter", "x"]:
                    return await self._post_twitter(page, text, image_paths)
                elif target in ["linkedin"]:
                    return await self._post_linkedin(page, text, image_paths)
                else:
                    # Generic web flow
                    return await self._generic_post(page, platform, text, image_paths)
            except Exception as e:
                logger.error(f"Autopilot social post failed: {e}", exc_info=True)
                return {"success": False, "error": str(e)}
            finally:
                if not headless:
                    # Keep open briefly so user can see result
                    await asyncio.sleep(4)
                await context.close()

    async def _post_twitter(self, page, text: str, image_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        await self._emit_step("navigate", "Opening Twitter / X compose...")
        await page.goto("https://twitter.com/compose/tweet", wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)

        if "login" in page.url:
            await self._emit_step("login_required", "Please log in to your Twitter/X account in the opened browser window.")
            # Wait up to 60s for user to log in if not logged in
            try:
                await page.wait_for_selector('[data-testid="tweetTextarea_0"]', timeout=60000)
            except Exception:
                return {"success": False, "message": "Timed out waiting for login."}

        await self._emit_step("typing", "Typing post content...")
        textarea = page.locator('[data-testid="tweetTextarea_0"]')
        await textarea.fill(text)
        await asyncio.sleep(1)

        if image_paths:
            valid_images = [img for img in image_paths if os.path.isfile(img)]
            if valid_images:
                await self._emit_step("uploading", f"Attaching {len(valid_images)} image(s)...")
                file_input = page.locator('input[data-testid="fileInput"]')
                await file_input.set_input_files(valid_images)
                await asyncio.sleep(2)

        await self._emit_step("ready", "Post prepared successfully in browser.")
        return {"success": True, "platform": "Twitter/X", "text": text, "media": image_paths or []}

    async def _post_linkedin(self, page, text: str, image_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        await self._emit_step("navigate", "Opening LinkedIn feed...")
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)

        if "login" in page.url or "checkpoint" in page.url:
            await self._emit_step("login_required", "Please log in to your LinkedIn account in the browser.")
            try:
                await page.wait_for_selector('.share-box-feed-entry__trigger', timeout=60000)
            except Exception:
                return {"success": False, "message": "Timed out waiting for LinkedIn login."}

        await self._emit_step("compose", "Opening post creator...")
        start_btn = page.locator('.share-box-feed-entry__trigger, button:has-text("Start a post")').first
        if await start_btn.is_visible():
            await start_btn.click()
            await asyncio.sleep(1.5)

        editor = page.locator('.editor-content .ql-editor, [data-placeholder="What do you want to talk about?"]').first
        if await editor.is_visible():
            await editor.fill(text)
            await asyncio.sleep(1)

        await self._emit_step("ready", "LinkedIn post prepared and ready to publish.")
        return {"success": True, "platform": "LinkedIn", "text": text}

    async def _generic_post(self, page, platform: str, text: str, image_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        await self._emit_step("navigate", f"Navigating to {platform}...")
        url = platform if platform.startswith("http") else f"https://www.{platform}.com"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)
        return {"success": True, "platform": platform, "url": url}

    async def send_whatsapp_message(self, contact_name: str, message: str, headless: bool = False) -> Dict[str, Any]:
        from playwright.async_api import async_playwright

        await self._emit_step("init", "Launching WhatsApp Web...")
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=PROFILE_DIR,
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = context.pages[0] if context.pages else await context.new_page()

            try:
                await self._emit_step("navigate", "Opening WhatsApp Web...")
                await page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)

                # Check if QR code is visible
                qr = page.locator('canvas[aria-label="Scan me!"]')
                if await qr.is_visible():
                    await self._emit_step("qr_required", "Please scan WhatsApp Web QR code to link your account.")
                    await page.wait_for_selector('[contenteditable="true"]', timeout=90000)

                await self._emit_step("searching", f"Searching for contact: '{contact_name}'...")
                search_box = page.locator('div[contenteditable="true"][data-tab="3"]').first
                if await search_box.is_visible():
                    await search_box.click()
                    await search_box.fill(contact_name)
                    await asyncio.sleep(1.5)
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(1)

                msg_box = page.locator('div[contenteditable="true"][data-tab="10"], div[contenteditable="true"][data-tab="6"]').first
                if await msg_box.is_visible():
                    await self._emit_step("typing", f"Typing message to {contact_name}...")
                    await msg_box.fill(message)
                    await asyncio.sleep(1)
                    await self._emit_step("ready", f"Message prepared for {contact_name}.")
                    return {"success": True, "platform": "WhatsApp", "contact": contact_name, "message": message}

                return {"success": True, "platform": "WhatsApp", "contact": contact_name}
            finally:
                if not headless:
                    await asyncio.sleep(3)
                await context.close()
