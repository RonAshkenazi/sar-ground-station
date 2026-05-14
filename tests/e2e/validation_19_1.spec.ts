import { expect, test, type Locator, type Page } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const FOLDER_ID = 'scan - field test 1 - 19.1'
const CALIBRATION_CSV = 'scan_2026-01-19_11-14-13Z-calic_search1.csv'
const CALIBRATION_MAC = '2c:59:8a:58:95:c1'
const ENRICHMENT_CSV = 'scan_2026-01-19_11-20-58Z-test-circle2.csv'
const ENRICHED_ARTIFACT = 'scan_2026-01-19_11-20-58Z-test-circle2_ENRICHED.csv'
const REID_ARTIFACT = 'scan_2026-01-19_11-20-58Z-test-circle2_REID.csv'
const GT_CSV = path.resolve(
  'runtime',
  'DATA',
  FOLDER_ID,
  'scan_2026-01-19_11-17-03Z-GPS.csv',
)

type ValidationReport = {
  folder: string
  calibrationMac: string
  enrichmentMatchRate: string | null
  reidStaticClusters: string | null
  reidDynamicClusters: string | null
  reidUniqueDynamicMacs: string | null
  localizationClusters: number | null
  confidenceBadgesVisible: string[]
  gtMeanLat: number
  gtMeanLon: number
  evaluationScore: string | null
  evaluationMatches: number | null
  evaluationFalsePositives: number | null
  evaluationFalseNegatives: number | null
  evaluationAmbiguous: string | null
  error?: string
  failureScreenshot?: string
}

test('validation 19.1 - full pipeline on field scan data', async ({ page }) => {
  test.setTimeout(360_000)
  page.on('console', (message) => console.log(`[browser:${message.type()}] ${message.text()}`))
  page.on('pageerror', (error) => console.log(`[pageerror] ${error.message}`))

  const gtMean = readGtMean(GT_CSV)
  const report: ValidationReport = {
    folder: FOLDER_ID,
    calibrationMac: CALIBRATION_MAC,
    enrichmentMatchRate: null,
    reidStaticClusters: null,
    reidDynamicClusters: null,
    reidUniqueDynamicMacs: null,
    localizationClusters: null,
    confidenceBadgesVisible: [],
    gtMeanLat: gtMean.lat,
    gtMeanLon: gtMean.lon,
    evaluationScore: null,
    evaluationMatches: null,
    evaluationFalsePositives: null,
    evaluationFalseNegatives: null,
    evaluationAmbiguous: null,
  }

  try {
    await page.goto('/session')
    await expect(page.getByRole('heading', { name: 'Select Scan Folder' })).toBeVisible()
    await selectByValueOrText(page.locator('#folder-select'), FOLDER_ID)
    await expect(page.locator('.mode-badge')).toHaveText('WIFI')
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
    report.enrichmentMatchRate = await valueForQualityMetricInPanel(
      page.locator('.quality-panel').filter({ hasText: 'Quality' }).first(),
      'Match rate',
    )
    await pause(page)

    await selectExactOption(page.locator('#reid-enriched'), ENRICHED_ARTIFACT)
    await pause(page)
    await page.getByRole('button', { name: 'Run Re-ID' }).click()
    await expect(page.locator('.quality-panel').filter({ hasText: 'Re-ID Quality' })).toBeVisible({ timeout: 90_000 })
    report.reidStaticClusters = await valueForQualityMetric(page, 'Static clusters')
    report.reidDynamicClusters = await valueForQualityMetric(page, 'Dynamic clusters')
    report.reidUniqueDynamicMacs = await valueForQualityMetric(page, 'Unique dynamic MACs')
    await pause(page)

    await page.getByRole('navigation', { name: 'Pipeline stages' }).getByText('Localization').click()
    await expect(page.getByRole('heading', { name: 'Localization' })).toBeVisible()
    await expect(page.locator('.calibration-info')).toContainText('Using:')
    await selectExactOption(page.locator('#localization-reid-select'), REID_ARTIFACT)
    await pause(page)

    await page.getByRole('button', { name: 'Run Localization' }).click()
    await expect(page.locator('.cluster-table')).toBeVisible({ timeout: 120_000 })
    report.localizationClusters = await page.locator('.cluster-table tbody tr').count()
    report.confidenceBadgesVisible = await page
      .locator('.cluster-table tbody tr')
      .evaluateAll((rows) =>
        rows.slice(0, 5).flatMap((row) =>
          Array.from(row.querySelectorAll('.conf-badge'))
            .map((badge) => badge.textContent?.trim() ?? '')
            .filter(Boolean),
        ),
      )
    await page.screenshot({ path: 'tests/e2e/screenshots/validation_step5_localization.png', fullPage: true })
    await pause(page)

    await page.getByRole('navigation', { name: 'Pipeline stages' }).getByText('Result Analysis').click()
    await expect(page.getByRole('heading', { name: 'Result Analysis' })).toBeVisible()
    await uploadGtCsvOrAddMean(page, GT_CSV, gtMean.lat, gtMean.lon)
    await expect(page.locator('.gt-row').first()).toBeVisible({ timeout: 30_000 })
    await page.screenshot({ path: 'tests/e2e/screenshots/validation_step6_gt_added.png', fullPage: true })
    await pause(page)

    await page.getByRole('button', { name: /Run Evaluation|Evaluate/ }).click()
    await expect(page.locator('.score-panel')).toBeVisible({ timeout: 30_000 })
    report.evaluationScore = await page.locator('.score-total').textContent().then((text) => text?.trim() ?? null)
    report.evaluationMatches = await page.locator('.diagnostics-table tbody tr').count()
    report.evaluationFalsePositives = await diagnosticListCount(page, 'False Positives')
    report.evaluationFalseNegatives = await diagnosticListCount(page, 'False Negatives')
    report.evaluationAmbiguous = await metricRowValue(page, 'Ambiguous GTs')
    await page.screenshot({ path: 'tests/e2e/screenshots/validation_step7_evaluation.png', fullPage: true })

    console.log(JSON.stringify(report))
  } catch (error) {
    report.error = error instanceof Error ? error.message : String(error)
    report.failureScreenshot = 'tests/e2e/screenshots/validation_failure.png'
    await page.screenshot({ path: report.failureScreenshot, fullPage: true }).catch(() => undefined)
    console.log(JSON.stringify(report))
    throw error
  }
})

async function uploadGtCsvOrAddMean(page: Page, csvPath: string, lat: number, lon: number) {
  const csvInput = page.locator('input[type="file"][accept*=".csv"], input[type="file"][accept*="text/csv"]').first()
  if ((await csvInput.count()) > 0) {
    await csvInput.setInputFiles(csvPath)
    return
  }

  const latInput = page.locator('input[name*="lat" i], input[placeholder*="lat" i], label:has-text("lat") input').first()
  const lonInput = page.locator('input[name*="lon" i], input[placeholder*="lon" i], label:has-text("lon") input').first()
  if ((await latInput.count()) === 0 || (await lonInput.count()) === 0) {
    throw new Error('No GPS CSV file input or manual lat/lon controls found for GT entry')
  }
  await latInput.fill(String(lat))
  await lonInput.fill(String(lon))
  await page.getByRole('button', { name: /Add/ }).click()
}

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
  return valueForQualityMetricInPanel(page.locator('.quality-panel').filter({ hasText: 'Re-ID Quality' }), label)
}

async function valueForQualityMetricInPanel(panel: Locator, label: string) {
  return panel.evaluate((element, metricLabel) => {
    const terms = Array.from(element.querySelectorAll('dt'))
    const term = terms.find((item) => item.textContent?.trim() === metricLabel)
    return term?.nextElementSibling?.textContent?.trim() ?? ''
  }, label)
}

async function diagnosticListCount(page: Page, title: string) {
  return page.locator('.diagnostic-list').filter({ hasText: title }).evaluate((list) => {
    const items = Array.from(list.querySelectorAll('span')).map((item) => item.textContent?.trim() ?? '')
    return items.length === 1 && items[0] === 'None' ? 0 : items.filter(Boolean).length
  })
}

async function metricRowValue(page: Page, label: string) {
  return page.locator('.metric-row').filter({ hasText: label }).evaluate((row) => {
    const spans = Array.from(row.querySelectorAll('span'))
    return spans[1]?.textContent?.trim() ?? null
  })
}

async function pause(page: Page, ms = 1200) {
  await page.waitForTimeout(ms)
}

function readGtMean(csvPath: string) {
  const lines = fs.readFileSync(csvPath, 'utf-8').split(/\r?\n/).filter((line) => line.trim())
  const headers = lines[0].split(',').map((header) => header.trim())
  const latIndex = headers.indexOf('gps_lat')
  const lonIndex = headers.indexOf('gps_lon')
  if (latIndex === -1 || lonIndex === -1) {
    throw new Error(`GT CSV missing gps_lat/gps_lon columns: ${csvPath}`)
  }

  let count = 0
  let latSum = 0
  let lonSum = 0
  for (const line of lines.slice(1)) {
    const cells = line.split(',')
    const lat = Number(cells[latIndex])
    const lon = Number(cells[lonIndex])
    if (Number.isFinite(lat) && Number.isFinite(lon)) {
      latSum += lat
      lonSum += lon
      count += 1
    }
  }
  if (count === 0) throw new Error(`GT CSV has no valid gps_lat/gps_lon rows: ${csvPath}`)

  return {
    lat: round6(latSum / count),
    lon: round6(lonSum / count),
  }
}

function round6(value: number) {
  return Math.round(value * 1_000_000) / 1_000_000
}
