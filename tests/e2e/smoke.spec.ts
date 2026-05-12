import { expect, test } from './fixtures'

test.beforeEach(({}, testInfo) => {
  test.skip(testInfo.project.name === 'cdp', 'Smoke tests use Playwright-managed browsers')
})

test.describe('App shell navigation', () => {
  test('root redirects to /session', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/\/session/)
  })

  test('Session Start page renders heading', async ({ page }) => {
    await page.goto('/session')
    await expect(page.getByRole('heading', { name: 'Select Scan Folder' })).toBeVisible()
  })

  test('Overview page renders without crashing', async ({ page }) => {
    await page.goto('/overview')
    await expect(page.getByText('No active session')).toBeVisible()
    await expect(page.getByLabel('Scan CSV')).toBeDisabled()
  })

  test('Calibration page renders without crashing', async ({ page }) => {
    await page.goto('/calibration')
    await expect(page.getByRole('heading', { name: 'Calibration', exact: true })).toBeVisible()
  })

  test('Enrichment page renders without crashing', async ({ page }) => {
    await page.goto('/enrichment')
    await expect(page.getByRole('heading', { name: 'Re-ID & Enrichment' })).toBeVisible()
  })

  test('Localization page renders without crashing', async ({ page }) => {
    await page.goto('/localization')
    await expect(page.getByRole('heading', { name: 'Localization' })).toBeVisible()
  })

  test('Result Analysis page renders Research / Tuning subtitle', async ({ page }) => {
    await page.goto('/analysis')
    await expect(page.getByText(/Research \/ Tuning/i)).toBeVisible()
  })
})

test.describe('Stage navigation', () => {
  test('left nav contains all 6 stage links', async ({ page }) => {
    await page.goto('/session')
    const nav = page.getByRole('navigation', { name: 'Pipeline stages' })
    await expect(nav.getByText('Session Start')).toBeVisible()
    await expect(nav.getByText('Overview')).toBeVisible()
    await expect(nav.getByText('Calibration')).toBeVisible()
    await expect(nav.getByText('Enrichment & Re-ID')).toBeVisible()
    await expect(nav.getByText('Localization')).toBeVisible()
    await expect(nav.getByText('Result Analysis')).toBeVisible()
  })

  test('clicking Overview nav link navigates', async ({ page }) => {
    await page.goto('/session')
    await page.getByRole('navigation').getByText('Overview').click()
    await expect(page).toHaveURL(/\/overview/)
  })
})

test.describe('Session Start - folder loading', () => {
  test('folder dropdown populates from backend', async ({ page }) => {
    await page.goto('/session')
    await expect(page.locator('.folder-select')).toBeVisible({ timeout: 5000 })
    const options = await page.locator('.folder-select option').count()
    expect(options).toBeGreaterThan(1)
  })

  test('selecting a folder can start a session and navigate to Overview', async ({ page }) => {
    await page.goto('/session')
    const select = page.locator('.folder-select')
    await expect(select).toBeVisible({ timeout: 5000 })
    await select.selectOption({ index: 1 })
    await expect(page.locator('.mode-badge')).toBeVisible()
    await page.getByRole('button', { name: 'BLE' }).click()
    await expect(page.locator('.mode-badge')).toHaveText('BLE')
    await page.getByRole('button', { name: /Start Session/ }).click()
    await expect(page).toHaveURL(/\/overview/)
    await expect(page.getByLabel('Scan CSV')).toBeVisible()
    await expect(page.getByText('Select a CSV file above to begin inspection.')).toBeVisible()
    await expect(page.locator('.header-folder')).not.toHaveText('No folder selected')
    await expect(page.locator('.header-mode-badge')).toHaveText('BLE')
  })
})
