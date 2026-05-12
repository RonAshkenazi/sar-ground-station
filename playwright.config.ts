/**
 * Playwright Configuration
 *
 * Docs: https://playwright.dev/docs/test-configuration
 *
 * Usage:
 *   npx playwright test                      # Headless (CI / fast)
 *   npx playwright test --project=watch      # Headed: Playwright drives, you watch
 *   npx playwright test --project=cdp        # CDP: you drive in Chrome, Playwright observes
 *   npx playwright test --ui                 # Interactive UI mode
 *   npx playwright test --debug              # Step-through debug
 *
 * CDP setup (for --project=cdp):
 *   Launch Chrome with:
 *     chrome.exe --remote-debugging-port=9222 --user-data-dir=%TEMP%\pw-cdp
 *   Then run:  npx playwright test --project=cdp
 *
 * Ports:
 *   Frontend : http://localhost:5173  (FRONTEND_PORT in .env)
 *   Backend  : http://localhost:8000  (BACKEND_PORT in .env)
 *   CDP      : http://localhost:9222  (CDP_PORT in .env, default 9222)
 */

import { defineConfig, devices } from "@playwright/test";

const CDP_PORT = process.env.CDP_PORT ?? "9222";

// Detect whether the frontend is already running so we don't double-start it.
// Set PLAYWRIGHT_NO_WEBSERVER=1 to skip auto-start entirely (e.g. you started it yourself).
const skipWebServer = !!process.env.PLAYWRIGHT_NO_WEBSERVER;

export default defineConfig({
  testDir: "./tests/e2e",

  timeout: 30_000,

  forbidOnly: !!process.env.CI,

  retries: process.env.CI ? 2 : 0,

  reporter: process.env.CI ? "github" : [["html"], ["list"]],

  use: {
    // Port must match FRONTEND_PORT in .env — update here if you change it
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },

  // Auto-start the frontend dev server before any test run.
  // If it's already running on 5173, Playwright reuses it (reuseExistingServer: true).
  // The backend must be started separately: cd backend && uvicorn app.main:app --reload
  webServer: skipWebServer
    ? undefined
    : {
        command: "npm run dev",
        url: "http://localhost:5173",
        reuseExistingServer: true,
        timeout: 60_000,
        cwd: "./frontend",
      },

  projects: [
    // ── default: headless, fast, used for CI and normal test runs ─────────────
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },

    // ── watch: Playwright drives, you watch in a visible window ───────────────
    // Usage: npx playwright test --project=watch
    {
      name: "watch",
      use: {
        ...devices["Desktop Chrome"],
        headless: false,
        launchOptions: {
          slowMo: 400,   // ms between actions — lower to speed up, raise to slow down
          args: ["--window-size=1920,1080"],
        },
        viewport: { width: 1920, height: 1080 },
      },
    },

    // ── cdp: connect to YOUR running Chrome — you drive, Playwright observes ──
    // Usage:
    //   1. Launch Chrome:  chrome.exe --remote-debugging-port=9222 --user-data-dir=%TEMP%\pw-cdp
    //   2. Run tests:      npx playwright test --project=cdp
    {
      name: "cdp",
      use: {
        // connectOverCDP is set per-test via the cdpPage fixture (see tests/e2e/fixtures.ts)
        // baseURL still applies for page.goto() calls that use relative paths
        baseURL: "http://localhost:5173",
      },
    },
  ],
});
