/**
 * Example E2E Test — Playwright
 *
 * This is a starter test file. Replace with your actual E2E tests.
 *
 * Run:    npx playwright test
 * Debug:  npx playwright test --debug
 * UI:     npx playwright test --ui
 */

import { test, expect } from "@playwright/test";

test.describe("App Smoke Tests", () => {
  test("homepage loads successfully", async ({ page }) => {
    // Replace with your actual dev server URL
    await page.goto("http://localhost:3000");

    // Check the page loaded (replace with your actual assertions)
    await expect(page).toHaveTitle(/.+/);
  });

  test("no console errors on load", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        errors.push(msg.text());
      }
    });

    await page.goto("http://localhost:3000");
    await page.waitForLoadState("networkidle");

    expect(errors).toHaveLength(0);
  });

  test("page is accessible — basic checks", async ({ page }) => {
    await page.goto("http://localhost:3000");

    // Check that the page has a main landmark
    const main = page.locator("main");
    await expect(main).toBeVisible();

    // Check that all images have alt text
    const images = page.locator("img");
    const count = await images.count();
    for (let i = 0; i < count; i++) {
      const alt = await images.nth(i).getAttribute("alt");
      expect(alt).toBeTruthy();
    }
  });
});

test.describe("Screenshot Capture", () => {
  test("capture homepage screenshot", async ({ page }) => {
    await page.goto("http://localhost:3000");
    await page.waitForLoadState("networkidle");

    await page.screenshot({
      path: "tests/screenshots/homepage.png",
      fullPage: true,
    });
  });
});
