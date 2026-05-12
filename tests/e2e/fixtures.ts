/**
 * Playwright fixtures — extend base test with CDP support.
 *
 * Import `test` and `expect` from this file instead of "@playwright/test"
 * in any spec that should run across all three projects:
 *
 *   chromium  — headless, fast (default / CI)
 *   watch     — headed, slowMo, Playwright drives and you watch
 *   cdp       — connects to YOUR running Chrome; you drive, Playwright observes
 *
 * CDP setup (one-time, before running --project=cdp):
 *   Windows:  chrome.exe --remote-debugging-port=9222 --user-data-dir=%TEMP%\pw-cdp
 *   macOS:    open -a "Google Chrome" --args --remote-debugging-port=9222
 *   Linux:    google-chrome --remote-debugging-port=9222
 *
 * Then:  npx playwright test --project=cdp
 */

import { test as base, chromium, expect, type Page } from "@playwright/test";

type CdpFixtures = {
  page: Page;
};

export const test = base.extend<CdpFixtures>({
  page: async ({ page }, use, testInfo) => {
    if (testInfo.project.name !== "cdp") {
      // chromium and watch projects: use the standard Playwright-managed page
      await use(page);
      return;
    }

    // cdp project: attach to the user's running Chrome instance
    const cdpPort = process.env.CDP_PORT ?? "9222";
    const endpoint = `http://localhost:${cdpPort}`;

    let browser;
    try {
      browser = await chromium.connectOverCDP(endpoint);
    } catch {
      throw new Error(
        `Cannot connect to Chrome on ${endpoint}.\n` +
          `Start Chrome with:\n` +
          `  chrome.exe --remote-debugging-port=${cdpPort} --user-data-dir=%TEMP%\\pw-cdp\n` +
          `Then re-run the tests.`
      );
    }

    // Use the first existing context/page; create one if Chrome just opened
    const context = browser.contexts()[0] ?? (await browser.newContext());
    const cdpPage = context.pages()[0] ?? (await context.newPage());

    await use(cdpPage);

    // Do NOT close the browser — it belongs to the user
  },
});

export { expect };
