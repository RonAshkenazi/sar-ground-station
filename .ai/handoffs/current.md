# Codex Handoff — Fix CSV GT Import: Quoted-Field CSV Parsing

## Requested Role

[DEV:frontend]

---

## Context

The "Import CSV (mean GPS)" feature on the Result Analysis page calculates a wrong GT point when the scan CSV contains a row whose SSID field is a quoted string containing a comma.

**Root cause already diagnosed by Claude — do not re-investigate, just implement the fix.**

---

## Root Cause

`ResultAnalysisPage.tsx` `handleImportCsv()` splits each row with:

```typescript
const cols = line.split(',')
```

This does not handle RFC 4180 CSV quoting. Row 40 of `runtime/DATA/Scan09.02/scan_2026-02-09_07-42-14Z-SAMSUNGPS.csv` contains:

```
2026-02-09T07:42:15.701Z,probe-req,8c:aa:b5:ef:89:93,Broadcast,Broadcast,"^XM-,^P@`",-90,1,2412,31.249839333333334,34.806278,...
```

The SSID `"^XM-,^P@`"` is quoted and contains a comma. `split(',')` produces 17 tokens instead of 16, shifting every column after SSID by 1. As a result:

- `cols[9]` → `2412` (freq_mhz) is used as **latitude**
- `cols[10]` → `31.249839` (true gps_lat) is used as **longitude**

With 1907 normal rows contributing ~31.25 to the lat sum and 1 broken row contributing 2412, the computed centroid lat becomes ~32.5° — roughly 140 km north of the actual location.

---

## Fix Required

### File: `frontend/src/pages/ResultAnalysisPage.tsx`

Replace the naive `split(',')` in `handleImportCsv()` with a proper quoted-CSV row parser.

**Current code (around lines 162–197):**

```typescript
const lines = text.split('\n').filter((line) => line.trim())
if (lines.length < 2) throw new Error('CSV has no data rows')
const headers = lines[0].split(',').map((h) => h.trim().toLowerCase())
const latIdx = headers.indexOf('gps_lat') !== -1 ? headers.indexOf('gps_lat') : headers.indexOf('lat')
const lonIdx = headers.indexOf('gps_lon') !== -1 ? headers.indexOf('gps_lon') : headers.indexOf('lon')
if (latIdx === -1 || lonIdx === -1) throw new Error('CSV must have gps_lat/gps_lon or lat/lon columns')
let sumLat = 0,
  sumLon = 0,
  count = 0
for (const line of lines.slice(1)) {
  const cols = line.split(',')
  const lat = parseFloat(cols[latIdx])
  const lon = parseFloat(cols[lonIdx])
  if (!isNaN(lat) && !isNaN(lon)) {
    sumLat += lat
    sumLon += lon
    count++
  }
}
```

**Required changes:**

1. Add a `parseCsvRow(line: string): string[]` helper that handles quoted fields:
   - Inside a quoted field (`"..."`), commas do NOT split
   - `""` inside quotes is an escaped double-quote → becomes `"`
   - Strip surrounding quotes from field values

2. Use `parseCsvRow` instead of `split(',')` for **both** the header line and each data line.

3. Find `gpsFixIdx` from the header (column `gps_fix`). Skip any data row where `cols[gpsFixIdx]` is not `"1"` (when the column exists) — this prevents stale/no-lock GPS rows from skewing the centroid.

**`parseCsvRow` implementation to use:**

```typescript
function parseCsvRow(line: string): string[] {
  const fields: string[] = []
  let current = ''
  let inQuotes = false
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (inQuotes) {
      if (ch === '"' && line[i + 1] === '"') {
        current += '"'
        i++
      } else if (ch === '"') {
        inQuotes = false
      } else {
        current += ch
      }
    } else {
      if (ch === '"') {
        inQuotes = true
      } else if (ch === ',') {
        fields.push(current)
        current = ''
      } else {
        current += ch
      }
    }
  }
  fields.push(current)
  return fields
}
```

Place this function at the bottom of the file alongside `pct`, `fmt`, `heatColor`.

---

## Verification

After the fix, test with `runtime/DATA/Scan09.02/scan_2026-02-09_07-42-14Z-SAMSUNGPS.csv`:

1. Start backend + frontend
2. Load any session with a localization result
3. On Result Analysis → "Import CSV (mean GPS)" → select the file
4. The GT point should land at approximately **lat ≈ 31.2499, lon ≈ 34.8063**
   (not ~32.5 which is the broken result)
5. Confirm the marker appears on the map at the correct location

Also confirm a normal unquoted CSV still imports correctly (no regression).

---

## Files to Change

- `frontend/src/pages/ResultAnalysisPage.tsx` only

## Out of Scope

- Do not change backend files
- Do not add a third-party CSV library
- Do not change any other GT management logic

## Constraints

- Do not run `git commit`
- `parseCsvRow` must handle: quoted fields, commas inside quotes, `""` escaped quotes

## Acceptance Criteria

- [ ] `parseCsvRow` helper added and used for both header and data rows in `handleImportCsv`
- [ ] `gps_fix` filtering added (skip rows where fix ≠ "1" when column exists)
- [ ] SAMSUNGPS.csv imports to ~31.2499, 34.8063 (not ~32.5)
- [ ] Normal unquoted CSV import still works

## Founder Decisions Needed

None — root cause confirmed, fix is clear.
