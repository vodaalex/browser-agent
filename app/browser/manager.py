from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app.config import Settings, settings
from app.log import logger
from app.browser.actions import BrowserActions
from app.browser.page import PageStateExtractor


class BrowserManager:

    def __init__(self, cfg: Settings | None = None):
        self._cfg = cfg or settings
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

        # Composed helpers (initialised on start)
        self.actions: BrowserActions | None = None
        self.page_state: PageStateExtractor | None = None

    @property
    def page(self) -> Page | None:
        return self._page

    async def start(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._cfg.headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
                "--disable-ipc-flooding-protection",
            ],
        )
        self._context = await self._browser.new_context(
            viewport={"width": self._cfg.viewport_width, "height": self._cfg.viewport_height},  # type: ignore[arg-type]
            device_scale_factor=2,
            user_agent=self._cfg.user_agent,
        )
        self._page = await self._context.new_page()
        await self._page.goto("about:blank")

        # Wire up composed helpers
        self.page_state = PageStateExtractor(self._page)
        self.actions = BrowserActions(
            self._page,
            on_page_change=self.page_state.invalidate_cache,
        )

        logger.info("Browser started (headless=%s)", self._cfg.headless)

    async def stop(self):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser stopped")




