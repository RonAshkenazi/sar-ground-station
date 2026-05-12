# Run Test Suite

Run the project's test suite and report results.

## Steps

1. **Check CLAUDE.md** for the test command (look for `{{TEST_COMMAND}}`)
2. **Run the test command**
3. **Report results** in this format:

```
## Test Results

**Status:** PASS / FAIL
**Tests run:** X
**Passed:** X
**Failed:** X
**Skipped:** X

### Failures (if any)
- `test_name` — [reason for failure]

### Summary
[Brief assessment — is it safe to ship?]
```

## If no test command is configured
Tell the user:
> "No test command found in CLAUDE.md. Please add your test command (e.g., `npm test`, `pytest`, `go test ./...`) to the Key Commands section."

## After running tests
- If all pass: report success
- If any fail: analyze the failures, suggest fixes
- If tests are missing: suggest what should be tested
