import { defineConfig } from '@playwright/test'
import base from './playwright.config'

export default defineConfig({
  ...base,
  timeout: 180_000,
  use: {
    ...base.use,
    headless: false,
    launchOptions: { slowMo: 900 },
    viewport: { width: 1400, height: 900 },
  },
  projects: [{ name: 'demo' }],
  workers: 1,
})
