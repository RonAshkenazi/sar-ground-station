# UI Kit

## 0. Locked Technical Decisions

These are decided. Do not re-open them.

| Decision | Value |
|---|---|
| Map library | **Leaflet** (`react-leaflet`) |
| Component base | **Custom CSS using this file's tokens** — no UI library (no Tailwind, no shadcn, no Ant Design) |
| Display language | **English UI, Hebrew data** — UI chrome is English; data fields (SSIDs, folder names, vendor strings) may contain Hebrew; body font must render Hebrew correctly; use `dir="auto"` on data cells |
| Primary screen | **1920×1080** |
| Default basemap | **OSM + satellite, user-switchable** (spec view-only control `VIEW-08 basemap_type`) |
| Stage navigation | **Warn but allow** — all 6 stages always clickable; show warning banner on arrival if prerequisites are missing, never block navigation |

---

## 1. Design Goal

The UI should feel like an operational SAR ground-station tool: calm, dense, readable, and built for repeated field use. Avoid marketing-style layouts, oversized hero sections, and decorative visuals.

## 2. Color Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `--color-bg` | `#f5f7fa` | App background |
| `--color-surface` | `#ffffff` | Panels, tables, controls |
| `--color-surface-alt` | `#eef2f6` | Secondary panels and nav |
| `--color-border` | `#c8d1dc` | Borders and dividers |
| `--color-text` | `#17212f` | Primary text |
| `--color-text-muted` | `#5d6b7a` | Secondary text |
| `--color-primary` | `#1f6feb` | Primary actions, active nav |
| `--color-primary-strong` | `#174ea6` | Hover/pressed primary |
| `--color-accent` | `#0f766e` | Operational highlights |
| `--color-success` | `#15803d` | Success states |
| `--color-warning` | `#b45309` | Warning states |
| `--color-danger` | `#b91c1c` | Error/destructive states |

## 3. Typography

Use system fonts for a native Windows/browser feel.

| Token | Value |
|-------|-------|
| `--font-body` | `Segoe UI, Roboto, Arial, sans-serif` |
| `--font-mono` | `Consolas, ui-monospace, SFMono-Regular, monospace` |

| Use | Size | Weight | Line Height |
|-----|------|--------|-------------|
| Page title | `1.5rem` | 700 | 1.25 |
| Section title | `1.125rem` | 650 | 1.35 |
| Body | `0.95rem` | 400 | 1.5 |
| Small/meta | `0.8125rem` | 400 | 1.4 |
| Data/table | `0.875rem` | 400 | 1.35 |

## 4. Layout

- App shell: top header, left stage navigation, main work area.
- Keep controls close to the data they affect.
- Use full-width work surfaces, not nested decorative cards.
- Cards/panels may frame repeated items, modals, tables, and tool areas.
- Maximum border radius: `8px`.
- Standard panel padding: `16px`.
- Dense table row height target: `36px` to `44px`.

## 5. Controls

- Buttons use icon + label for primary commands where space allows.
- Icon-only buttons need tooltips.
- Use segmented controls for mode/stage options.
- Use selects/menus for option sets.
- Use checkboxes/toggles for binary flags.
- Use sliders or numeric inputs for numeric parameters.
- View-only map controls must not trigger execution endpoints.

## 6. Component Rules

### Header

Show:

- active session
- active folder
- active mode
- active artifact summary
- warning count
- save session action

### Left Navigation

Stages:

1. Session
2. Overview
3. Calibration
4. Enrichment/Re-ID
5. Localization
6. Result Analysis

Show active state, completed state, and warning state.

### Tables

- Sticky headers for long tables.
- Monospace for MAC addresses, timestamps, and file paths.
- Empty states must explain what action unlocks the table.

### Maps

- Map rendering displays backend results; it does not compute algorithmic output.
- Layer controls are view-only.
- Result Analysis may enable ground-truth tools.

## 7. Accessibility

- Body text contrast must meet WCAG AA.
- All controls must be keyboard reachable.
- Use semantic HTML.
- Provide visible focus states.
- Respect `prefers-reduced-motion`.
- Do not rely on color alone for warnings or status.

