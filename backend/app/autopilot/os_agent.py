"""
Native OS Autopilot Agent for Parley.
Controls screen capture (mss), mouse navigation, and keyboard input (pyautogui).
Executes desktop-level commands across any application.
"""
import os
import sys
import logging
import asyncio
import base64
import io
from typing import Optional, Dict, Any, Tuple, List, Callable

logger = logging.getLogger(__name__)


class OSAutopilot:
    def __init__(self, step_callback: Optional[Callable[[str, str], None]] = None):
        self.step_callback = step_callback
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        logger.info("[OSAutopilot] Emergency stop triggered.")

    async def _emit_step(self, step_name: str, message: str):
        logger.info(f"[OSAutopilot] [{step_name}] {message}")
        if self.step_callback:
            res = self.step_callback(step_name, message)
            if asyncio.iscoroutine(res):
                await res

    def capture_screen_base64(self, monitor_index: int = 1) -> str:
        """
        Captures the primary monitor screen in real-time and returns JPEG base64 data.
        """
        import mss
        from PIL import Image

        with mss.mss() as sct:
            monitors = sct.monitors
            mon = monitors[min(monitor_index, len(monitors) - 1)]
            sct_img = sct.grab(mon)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

            # Resize if 4K to conserve memory & token limits
            max_w, max_h = 1920, 1080
            if img.width > max_w or img.height > max_h:
                img.thumbnail((max_w, max_h), Image.LANCZOS)

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            return base64.b64encode(buf.getvalue()).decode("utf-8")

    async def move_and_click(self, x: int, y: int, clicks: int = 1, button: str = "left") -> bool:
        """
        Moves the mouse smoothly and clicks on target coordinates.
        """
        import pyautogui

        if self._is_cancelled:
            return False

        await self._emit_step("mouse", f"Moving cursor to ({x}, {y}) and clicking...")
        try:
            pyautogui.moveTo(x, y, duration=0.3, tween=pyautogui.easeOutQuad)
            if clicks == 1:
                pyautogui.click(x, y, button=button)
            elif clicks == 2:
                pyautogui.doubleClick(x, y, button=button)
            return True
        except Exception as e:
            logger.error(f"Failed to click at ({x}, {y}): {e}")
            return False

    async def type_text(self, text: str, interval: float = 0.02) -> bool:
        """
        Types the given text into the active focused window.
        """
        import pyautogui

        if self._is_cancelled:
            return False

        await self._emit_step("keyboard", f"Typing text ({len(text)} chars)...")
        try:
            # Type via clipboard if text contains non-ASCII characters
            try:
                import pyperclip
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl" if sys.platform == "win32" else "command", "v")
            except Exception:
                pyautogui.write(text, interval=interval)
            return True
        except Exception as e:
            logger.error(f"Failed typing text: {e}")
            return False

    async def press_hotkey(self, *keys) -> bool:
        """
        Executes a native OS hotkey sequence.
        """
        import pyautogui

        if self._is_cancelled:
            return False

        await self._emit_step("hotkey", f"Pressing hotkey: {'+'.join(keys)}")
        try:
            pyautogui.hotkey(*keys)
            return True
        except Exception as e:
            logger.error(f"Failed pressing hotkey: {e}")
            return False

    async def open_url_in_browser(self, url: str) -> bool:
        """
        Opens a URL in the user's default web browser.
        """
        import webbrowser

        await self._emit_step("browser", f"Opening {url} in default browser...")
        try:
            webbrowser.open(url)
            await asyncio.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Failed opening browser URL: {e}")
            return False
