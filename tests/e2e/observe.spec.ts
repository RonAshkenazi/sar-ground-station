/**
 * Observe specs — designed for --project=cdp (you drive, Playwright watches).
 *
 * These tests attach to your live Chrome tab and run assertions against
 * whatever page you have open. They don't navigate — they observe.
 *
 * Usage:
 *   1. Open Chrome with:  chrome.exe --remote-debugging-port=9222 --user-data-dir=%TEMP%\pw-cdp
 *   2. Browse to any page in the app you want to inspect
 *   3. Run:  npx playwright test observe.spec.ts --project=cdp
 *
 * For interactive work, use --ui instead:
 *   npx playwright test observe.spec.ts --project=cdp --ui
 */

import { test, expect } from "./fixtures";

test.describe("Observe — current page health", () => {
  test("page has no unhandled JS errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));

    // Give the page a moment to settle (it's already open)
    await page.waitForTimeout(500);

    expect(errors, `JS errors on ${page.url()}: ${errors.join(", ")}`).toHaveLength(0);
  });

  test("app shell is rendered — header and nav are visible", async ({ page }) => {
    await expect(page.locator(".header")).toBeVisible();
    await expect(page.locator(".stage-nav")).toBeVisible();
  });

  test("active nav item is highlighted", async ({ page }) => {
    const activeItem = page.locator(".stage-nav-item.active");
    await expect(activeItem).toBeVisible();
  });

  test("no blank main area — something is rendered in <main>", async ({ page }) => {
    const main = page.locator("main");
    await expect(main).toBeVisible();
    const text = await main.innerText();
    expect(text.trim().length, "main area is empty").toBeGreaterThan(0);
  });
});

test.describe("Observe — network requests", () => {
  test("API base URL is reachable", async ({ page }) => {
    const response = await page.request.get("http://localhost:8000/health");
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toMatchObject({ status: "ok" });
  });
});

test.describe("Observe — accessibility snapshot", () => {
  test("capture current page screenshot", async ({ page }) => {
    const url = page.url().replace(/[^\w]/g, "_").slice(0, 60);
    await page.screenshot({
      path: `tests/screenshots/observe_${url}_${Date.now()}.png`,
      fullPage: true,
    });
    // Screenshot saved — check test-results/ or tests/screenshots/
  });
});
