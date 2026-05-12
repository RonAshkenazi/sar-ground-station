import { expect, test, type Locator, type Page } from '@playwright/test'

const FOLDER_ID = 'scan - field test 1 - 19.1'
const CALIBRATION_CSV = 'scan_2026-01-19_11-14-13Z-calic_search1.csv'
const CALIBRATION_MAC = '2c:59:8a:58:95:c1'
const ENRICHMENT_CSV = 'scan_2026-01-19_11-20-58Z-test-circle2.csv'
const ENRICHED_ARTIFACT = 'scan_2026-01-19_11-20-58Z-test-circle2_ENRICHED.csv'
const REID_ARTIFACT = 'scan_2026-01-19_11-20-58Z-test-circle2_REID.csv'

test('founder demo - full pipeline', async ({ page }) => {
  test.setTimeout(240_000)
  page.on('console', (message) => console.log(`[browser:${message.type()}] ${message.text()}`))
  page.on('pageerror', (error) => console.log(`[pageerror] ${error.message}`))

  await page.goto('/session')
  await expect(page.getByRole('heading', { name: 'Select Scan Folder' })).toBeVisible()
  await pause(page)

  await page.locator('#folder-select').selectOption({ index: 1 })
  await expect(page.locator('.mode-badge')).toHaveText('WIFI')
  await expect(page.locator('#folder-select')).toHaveValue(FOLDER_ID)
  await page.getByRole('button', { name: 'Wi-Fi' }).click()
  await expect(page.locator('.mode-badge')).toHaveText('WIFI')
  await pause(page)

  await page.getByRole('button', { name: /Start Session/ }).click()
  await expect(page).toHaveURL(/\/overview/)
  await expect(page.locator('.header-folder')).toContainText(FOLDER_ID)
  await pause(page)

  await page.getByRole('navigation', { name: 'Pipeline stages' }).getByText('Calibration').click()
  await expect(page.getByRole('heading', { name: 'Calibration', exact: true })).toBeVisible()
  await selectByValueOrText(page.locator('#calibration-csv'), CALIBRATION_CSV)
  await page.waitForFunction(() => document.querySelectorAll('#calibration-mac option').length > 1, null, {
    timeout: 30_000,
  })
  await selectByValueOrText(page.locator('#calibration-mac'), CALIBRATION_MAC)
  await pause(page)

  await page.getByRole('button', { name: 'Run Calibration' }).click()
  await expect(page.locator('.parameter-table')).toBeVisible({ timeout: 60_000 })
  await pause(page)
  await page.getByRole('button', { name: 'Approve' }).click()
  await expect(page.locator('.success-banner')).toContainText('Calibration approved', { timeout: 30_000 })
  await pause(page)

  await page.getByRole('navigation', { name: 'Pipeline stages' }).getByText('Enrichment & Re-ID').click()
  await expect(page.getByRole('heading', { name: 'Re-ID & Enrichment' })).toBeVisible()
  await selectByValueOrText(page.locator('#enrichment-csv'), ENRICHMENT_CSV)
  await expect(page.locator('.status-ok')).toContainText('PCAP found')
  await pause(page)

  await page.getByRole('button', { name: 'Run Enrichment' }).click()
  await expect(page.locator('.quality-panel').first()).toBeVisible({ timeout: 90_000 })
  const enrichmentMatchRate = await page.locator('.quality-panel').first().getByText('%').last().textContent()
  await pause(page)

  await selectExactOption(page.locator('#reid-enriched'), ENRICHED_ARTIFACT)
  await pause(page)
  await page.getByRole('button', { name: 'Run Re-ID' }).click()
  await expect(page.locator('.quality-panel').nth(1)).toBeVisible({ timeout: 90_000 })
  const staticClusters = await valueForQualityMetric(page, 'Static clusters')
  const dynamicClusters = await valueForQualityMetric(page, 'Dynamic clusters')
  await pause(page)

  await page.getByRole('navigation', { name: 'Pipeline stages' }).getByText('Localization').click()
  await expect(page.getByRole('heading', { name: 'Localization' })).toBeVisible()
  await expect(page.locator('.calibration-info')).toContainText('Using:')
  await selectExactOption(page.locator('#localization-reid-select'), REID_ARTIFACT)
  await pause(page)

  await page.getByRole('button', { name: 'Run Localization' }).click()
  await expect(page.locator('.cluster-table')).toBeVisible({ timeout: 90_000 })
  const localizationRows = await page.locator('.cluster-table tbody tr').count()
  await page.screenshot({ path: 'demo_result.png', fullPage: true })
  const saveButton = page.getByRole('button', { name: 'Save Session' })
  await expect(saveButton).toBeEnabled({ timeout: 30_000 })
  await pause(page)
  await saveButton.click()
  await expect(page.getByRole('button', { name: /Saving|Saved/ })).toBeVisible({ timeout: 10_000 })
  await expect(page.getByRole('button', { name: /Saved/ })).toBeVisible({ timeout: 10_000 })
  await pause(page)

  await page.getByRole('navigation', { name: 'Pipeline stages' }).getByText('Session Start').click()
  await expect(page.getByRole('heading', { name: 'Select Scan Folder' })).toBeVisible()
  const savedRow = page.locator('.saved-sessions-table tbody tr').filter({ hasText: FOLDER_ID }).first()
  await expect(savedRow).toBeVisible({ timeout: 30_000 })
  await savedRow.getByRole('button', { name: 'Resume' }).click()
  await expect(page).toHaveURL(/\/localization/)
  await expect(page.locator('.cluster-table')).toBeVisible({ timeout: 30_000 })
  await expect(page.locator('.cluster-table tbody tr')).toHaveCount(localizationRows, { timeout: 30_000 })
  await page.screenshot({ path: 'demo_result_v3.png', fullPage: true })
  await pause(page, 3000)

  console.log(
    JSON.stringify({
      folder: FOLDER_ID,
      calibrationCsv: CALIBRATION_CSV,
      calibrationMac: CALIBRATION_MAC,
      enrichmentCsv: ENRICHMENT_CSV,
      enrichmentMatchRate: enrichmentMatchRate?.trim() ?? null,
      reidStaticClusters: staticClusters,
      reidDynamicClusters: dynamicClusters,
      localizationClusters: localizationRows,
      screenshot: 'demo_result_v3.png',
    }),
  )
})

async function selectByValueOrText(select: Locator, expected: string) {
  await expect(select).toBeEnabled({ timeout: 30_000 })
  const matchingValue = await select.locator('option').evaluateAll(
    (options, text) =>
      options
        .map((option) => ({ value: (option as HTMLOptionElement).value, label: option.textContent ?? '' }))
        .find((option) => {
          const expected = String(text).toLowerCase()
          return option.value.toLowerCase() === expected || option.label.toLowerCase().includes(expected)
        })?.value ?? null,
    expected,
  )
  if (!matchingValue) throw new Error(`Option not found: ${expected}`)
  await select.selectOption(matchingValue)
}

async function selectExactOption(select: Locator, expected: string) {
  await expect(select).toBeEnabled({ timeout: 30_000 })
  const matchingValue = await select.locator('option').evaluateAll(
    (options, text) =>
      options
        .map((option) => ({ value: (option as HTMLOptionElement).value, label: option.textContent ?? '' }))
        .find((option) => option.value === text || option.label === text)?.value ?? null,
    expected,
  )
  if (!matchingValue) throw new Error(`Exact option not found: ${expected}`)
  await select.selectOption(matchingValue)
}

async function valueForQualityMetric(page: Page, label: string) {
  return page.locator('.quality-panel').filter({ hasText: 'Re-ID Quality' }).evaluate((panel, metricLabel) => {
    const terms = Array.from(panel.querySelectorAll('dt'))
    const term = terms.find((item) => item.textContent?.trim() === metricLabel)
    return term?.nextElementSibling?.textContent?.trim() ?? ''
  }, label)
}

async function pause(page: Page, ms = 1200) {
  await page.waitForTimeout(ms)
}
