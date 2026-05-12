# Run E2E Tests (Playwright)

Run end-to-end browser tests using Playwright.

## Steps

1. **Check if Playwright is installed**
   ```bash
   npx playwright --version
   ```
   If not installed, install it:
   ```bash
   npm init -y  # if no package.json exists
   npm install -D @playwright/test
   npx playwright install chromium
   ```

2. **Check if the dev server is running**
   - Look at `playwright.config.ts` for the `baseURL` and `webServer` settings
   - If `webServer` is configured, Playwright will auto-start the server
   - If not, start the dev server manually first (check `CLAUDE.md` for the command)

3. **Run the tests**
   ```bash
   npx playwright test
   ```

4. **Report results**
   ```
   ## E2E Test Results

   **Status:** PASS / FAIL
   **Tests run:** X
   **Passed:** X
   **Failed:** X

   ### Failures (if any)
   - `test_name` — [what went wrong]

   ### Screenshots
   - Captured in `tests/screenshots/`
   ```

## Useful Playwright Commands

```bash
npx playwright test                    # Run all tests
npx playwright test --debug            # Debug mode (step through)
npx playwright test --ui               # Interactive UI mode
npx playwright test --project=chromium # Single browser
npx playwright test tests/e2e/specific.spec.ts  # Single file
npx playwright show-report             # View HTML report
```

## Tips

- Tests are in `tests/e2e/`
- Screenshots go in `tests/screenshots/`
- Config is in `playwright.config.ts`
- On CI, set `CI=true` environment variable for CI-specific behavior
