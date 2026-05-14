import { chromium } from '@playwright/test';

const browser = await chromium.launch({ headless: false, slowMo: 400 });
const page = await browser.newPage();
await page.setViewportSize({ width: 1400, height: 900 });
const snap = async (name) => {
  await page.screenshot({ path: `C:/Users/User/AppData/Local/Temp/shot_enr2_${name}.png` });
  console.log(`SNAP:${name}`);
};

await page.goto('http://localhost:5173');
await page.waitForTimeout(500);
await page.locator('select').first().selectOption({ label: 'scan - field test 1 - 19.1 (wifi)' });
await page.waitForTimeout(400);
await page.getByRole('button', { name: /start session/i }).click();
await page.waitForTimeout(1000);

await page.locator('a, button, [role="link"]').filter({ hasText: /enrichment/i }).first().click();
await page.waitForTimeout(500);

// Select test-circle2 which HAS a PCAP
const csvSel = page.locator('select').first();
await csvSel.selectOption({ label: 'scan_2026-01-19_11-20-58Z-test-circle2.csv' });
await page.waitForTimeout(800);
await snap('01_circle2_selected');

const statusTxt = await page.locator('.status-panel').first().textContent().catch(() => 'n/a');
console.log('PCAP_STATUS:' + statusTxt);

const artifactTxt = await page.locator('.artifact-panel').first().textContent().catch(() => 'none');
console.log('ARTIFACT_PANEL:' + artifactTxt?.trim().slice(0,120));

const runBtn = page.getByRole('button', { name: /run enrichment/i });
console.log('RUN_ENABLED:' + !(await runBtn.isDisabled()));

// Click run
await runBtn.click();
await page.waitForTimeout(500);
await snap('02_running');

// Poll for completion
for (let i = 0; i < 10; i++) {
  await page.waitForTimeout(1500);
  const quality = await page.locator('.quality-panel').count();
  const err = await page.locator('.error-banner').count();
  const btnTxt = await runBtn.textContent().catch(() => '');
  console.log(`POLL_${i}: btn="${btnTxt?.trim()}" quality=${quality} err=${err}`);
  if (quality > 0 || err > 0) break;
}

await snap('03_after_run');
const qualityTxt = await page.locator('.quality-panel').first().textContent().catch(() => 'none');
console.log('QUALITY:' + qualityTxt?.replace(/\s+/g,' ').trim());
const errTxt = await page.locator('.error-banner').first().textContent().catch(() => 'none');
console.log('ERROR:' + errTxt);

await page.waitForTimeout(1500);
await browser.close();
