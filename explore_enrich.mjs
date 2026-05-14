import { chromium } from '@playwright/test';

const browser = await chromium.launch({ headless: false, slowMo: 500 });
const page = await browser.newPage();
await page.setViewportSize({ width: 1400, height: 900 });

const snap = async (name) => {
  const path = `C:/Users/User/AppData/Local/Temp/shot_enr_${name}.png`;
  await page.screenshot({ path });
  console.log(`SNAP:${name}`);
};

// Start session - use field test 1 which has a PCAP
await page.goto('http://localhost:5173');
await page.waitForTimeout(600);
await page.locator('select').first().selectOption({ label: 'scan - field test 1 - 19.1 (wifi)' });
await page.waitForTimeout(400);
await page.getByRole('button', { name: /start session/i }).click();
await page.waitForTimeout(1200);
await snap('01_session_started');

// Navigate to Enrichment & Re-ID
await page.locator('a, button, [role="link"]').filter({ hasText: /enrichment/i }).first().click();
await page.waitForTimeout(600);
await snap('02_enrichment_empty');

// Select a CSV
const csvSel = page.locator('select#enrichment-csv, select').first();
const opts = await csvSel.locator('option').allTextContents();
console.log('CSV_OPTS:' + JSON.stringify(opts.slice(0,5)));
// Try to find a CSV that has a matching PCAP — calic_search1 is the most likely
const calicCsv = opts.find(o => o.includes('calic'));
const firstCsv = calicCsv || opts.find(o => o.endsWith('.csv'));
if (firstCsv) {
  await csvSel.selectOption({ label: firstCsv });
  await page.waitForTimeout(800);
  await snap('03_csv_selected');
  const statusTxt = await page.locator('.status-panel, .status-ok, .status-blocked').first().textContent().catch(() => 'n/a');
  console.log('PCAP_STATUS:' + statusTxt);
}

// Check for existing artifact
const artifactTxt = await page.locator('.artifact-panel').first().textContent().catch(() => 'none');
console.log('ARTIFACT_PANEL:' + artifactTxt?.replace(/\s+/g,' ').trim().slice(0,100));

// Run enrichment if button is enabled
const runBtn = page.getByRole('button', { name: /run enrichment/i });
const disabled = await runBtn.isDisabled();
console.log('RUN_DISABLED:' + disabled);
if (!disabled) {
  await runBtn.click();
  await page.waitForTimeout(500);
  await snap('04_running');
  // Wait for completion (up to 10s)
  let done = false;
  for (let i = 0; i < 8; i++) {
    await page.waitForTimeout(1500);
    const btnTxt = await runBtn.textContent().catch(() => '');
    const quality = await page.locator('.quality-panel').count();
    const errPanel = await page.locator('.error-banner').count();
    console.log(`POLL_${i}: btn="${btnTxt}" quality=${quality} err=${errPanel}`);
    if (quality > 0 || errPanel > 0) { done = true; break; }
  }
  await snap('05_after_run');
  const qualityTxt = await page.locator('.quality-panel').first().textContent().catch(() => 'none');
  console.log('QUALITY:' + qualityTxt?.replace(/\s+/g,' ').trim().slice(0, 200));
}

// Try a second CSV to see PCAP-blocked state
const otherCsv = opts.find(o => o.endsWith('.csv') && !o.includes('calic'));
if (otherCsv) {
  await csvSel.selectOption({ label: otherCsv });
  await page.waitForTimeout(800);
  await snap('06_no_pcap_csv');
  const statusBlocked = await page.locator('.status-blocked').count();
  console.log('STATUS_BLOCKED_COUNT:' + statusBlocked);
  const runDisabled2 = await runBtn.isDisabled();
  console.log('RUN_DISABLED_WHEN_NO_PCAP:' + runDisabled2);
}

await page.waitForTimeout(1500);
await browser.close();
