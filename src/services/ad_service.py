"""AdMob service - banner and interstitial ads.

Production AdService pattern (KTV Player lineage) with real Ad Unit IDs and
UMP consent gating. Interstitials are cooldown-limited via the shared
singleton (see get_ad_service).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

import flet as ft

from core.constants import ADMOB_BANNER_ID, ADMOB_INTERSTITIAL_ID

logger = logging.getLogger(__name__)

# Try importing flet_ads - only available on mobile
try:
    import flet_ads as fta

    _HAS_ADS = True
except ImportError:
    _HAS_ADS = False


class AdService:
    """Manages AdMob banner and interstitial ads."""

    # Set to False before Play Store submission - then replace with real IDs
    USE_TEST_IDS = False

    # Test IDs (Google's official test units)
    BANNER_ID_ANDROID_TEST = "ca-app-pub-3940256099942544/9214589741"
    INTERSTITIAL_ID_ANDROID_TEST = "ca-app-pub-3940256099942544/1033173712"

    # Real Ad Unit IDs for production release
    BANNER_ID_ANDROID_PROD = ADMOB_BANNER_ID
    INTERSTITIAL_ID_ANDROID_PROD = ADMOB_INTERSTITIAL_ID

    def __init__(self, page: ft.Page):
        # S7 FIX: Fail-fast if USE_TEST_IDS is off but production IDs are empty
        if not self.USE_TEST_IDS:
            assert self.BANNER_ID_ANDROID_PROD, (
                "BANNER_ID_ANDROID_PROD must be set before production release"
            )
            assert self.INTERSTITIAL_ID_ANDROID_PROD, (
                "INTERSTITIAL_ID_ANDROID_PROD must be set before production release"
            )
        self.page = page
        self.interstitial = None
        self._on_close: Callable | None = None
        self._can_request_ads: bool = True
        self._consent_manager = None
        self.MIN_INTERSTITIAL_INTERVAL = 90.0

    @property
    def banner_id(self) -> str:
        if self.USE_TEST_IDS:
            return self.BANNER_ID_ANDROID_TEST
        return self.BANNER_ID_ANDROID_PROD

    @property
    def interstitial_id(self) -> str:
        if self.USE_TEST_IDS:
            return self.INTERSTITIAL_ID_ANDROID_TEST
        return self.INTERSTITIAL_ID_ANDROID_PROD

    def _is_mobile(self) -> bool:
        try:
            return self.page.platform.is_mobile()
        except Exception:
            return False

    # ── Consent Management (UMP) ──────────────────────────────────────────────

    async def gather_consent(self):
        """Run UMP consent flow. Only shows UI in regulated regions (EEA/UK)."""
        if not _HAS_ADS or not self._is_mobile():
            self._can_request_ads = True
            return
        try:
            self._consent_manager = fta.ConsentManager()
            self.page.services.append(self._consent_manager)
            await self._consent_manager.request_consent_info_update()
            await self._consent_manager.load_and_show_consent_form_if_required()
            self._can_request_ads = await self._consent_manager.can_request_ads()
        except Exception as e:
            logger.warning("UMP consent flow failed — ads disabled this session: %s", e)
            self._can_request_ads = False

    async def show_privacy_options(self):
        """Show privacy options form if required by regulation (GDPR)."""
        if not self._consent_manager:
            return
        try:
            status = (
                await self._consent_manager.get_privacy_options_requirement_status()
            )
            if status == fta.PrivacyOptionsRequirementStatus.REQUIRED:
                await self._consent_manager.show_privacy_options_form()
                self._can_request_ads = await self._consent_manager.can_request_ads()
        except Exception:
            pass

    # ── Ad Controls ───────────────────────────────────────────────────────────

    def get_banner_ad(self) -> ft.Control:
        """Return a banner ad control, or empty container on desktop."""
        if not _HAS_ADS or not self._is_mobile() or not self._can_request_ads:
            return ft.Container(width=0, height=0)
        try:
            ad = fta.BannerAd(
                unit_id=self.banner_id,
                width=320,
                height=50,
                on_error=lambda e: None,
            )
            return ft.Container(
                content=ad,
                width=320,
                height=50,
                alignment=ft.Alignment.CENTER,
            )
        except Exception:
            return ft.Container(width=0, height=0)

    async def preload_interstitial(self, on_close: Callable | None = None):
        """Pre-load an interstitial ad for later display."""
        self._on_close = on_close
        if not _HAS_ADS or not self._is_mobile() or not self._can_request_ads:
            return
        try:
            self.interstitial = fta.InterstitialAd(
                unit_id=self.interstitial_id,
                on_load=lambda e: None,
                on_error=lambda e: None,
                on_close=self._handle_close,
            )
        except Exception:
            self.interstitial = None

    async def _handle_close(self, e):
        if self._on_close:
            if asyncio.iscoroutinefunction(self._on_close):
                await self._on_close()
            else:
                self._on_close()
        await self.preload_interstitial(on_close=self._on_close)

    async def show_interstitial(self) -> bool:
        """Show an interstitial: the preloaded instance when available, else a
        fresh self-loading one (the same proven pattern as rewarded ads).

        A 90 s cooldown keeps session-start and autopilot-completion spots
        from stacking back-to-back. Returns True when a show was triggered.
        """
        if not _HAS_ADS or not self._is_mobile() or not self._can_request_ads:
            return False
        import time as _time

        now = _time.monotonic()
        if (
            now - getattr(self, "_last_interstitial_at", 0.0)
            < self.MIN_INTERSTITIAL_INTERVAL
        ):
            logger.debug("Interstitial skipped - cooldown active")
            return False

        if self.interstitial is not None:
            ad = self.interstitial
            self.interstitial = None  # flet_ads instances are single-show
            try:
                await ad.show()
                self._last_interstitial_at = now
                return True
            except Exception:
                pass  # stale preload - fall through to the fresh-instance path

        try:

            async def _show(e):
                await e.control.show()
                self._last_interstitial_at = _time.monotonic()

            # Strong ref prevents GC before the ad loads and displays.
            self._active_interstitial = fta.InterstitialAd(
                unit_id=self.interstitial_id,
                on_load=lambda e: self.page.run_task(_show, e),
                on_close=self._handle_close,
                on_error=lambda e: logger.warning("Interstitial error: %s", e.data),
            )
            return True
        except Exception as err:
            logger.warning("Fresh interstitial failed: %s", err)
            return False

    async def show_rewarded_interstitial(self, on_close: Callable) -> bool:
        """Show a rewarded interstitial ad, triggering on_close when closed."""
        if not _HAS_ADS or not self._is_mobile():
            # If offline/desktop, simulate successful completion of ad
            if asyncio.iscoroutinefunction(on_close):
                await on_close()
            else:
                on_close()
            return True

        try:
            # Create a brand new instance of InterstitialAd to avoid Flet reuse errors
            async def _show(e):
                await e.control.show()

            async def _close(e):
                self._active_rewarded_ad = None  # Clean reference to prevent leaks
                if asyncio.iscoroutinefunction(on_close):
                    await on_close()
                else:
                    on_close()

            # Store a strong reference to prevent immediate python garbage collection
            self._active_rewarded_ad = fta.InterstitialAd(
                unit_id=self.interstitial_id,
                on_load=lambda e: self.page.run_task(_show, e),
                on_close=lambda e: self.page.run_task(_close, e),
                on_error=lambda e: logger.error(
                    "Rewarded Interstitial error: %s", e.data
                ),
            )
            return True
        except Exception as err:
            logger.error("Failed to trigger rewarded interstitial: %s", err)
            # Sim fallback in case of errors on unsupported platforms
            if asyncio.iscoroutinefunction(on_close):
                await on_close()
            else:
                on_close()
            return False


_shared_instance: AdService | None = None


def get_ad_service(page: ft.Page) -> AdService:
    """Process-wide AdService so the startup-preloaded ad is shared by every
    call site (session creation, autopilot completion) instead of each spot
    building a throwaway instance whose interstitial was never preloaded."""
    global _shared_instance
    if _shared_instance is None:
        _shared_instance = AdService(page)
    return _shared_instance
