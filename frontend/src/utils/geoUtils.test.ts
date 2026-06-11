import { describe, expect, it } from 'vitest'
import { circleIntersectsPolygon, circleIntersectionAreaM2, pointInPolygon, polygonAreaM2, sumCircleAreasM2 } from './geoUtils'

describe('geoUtils', () => {
  const square: [number, number][] = [
    [0, 0],
    [0, 0.001],
    [0.001, 0.001],
    [0.001, 0],
  ]

  it('detects points inside and outside a polygon', () => {
    expect(pointInPolygon(0.0005, 0.0005, square)).toBe(true)
    expect(pointInPolygon(0.002, 0.0005, square)).toBe(false)
    expect(pointInPolygon(0.0005, 0.0005, [])).toBe(false)
  })

  it('estimates polygon area in square metres', () => {
    expect(polygonAreaM2(square)).toBeGreaterThan(12000)
    expect(polygonAreaM2(square)).toBeLessThan(13000)
  })

  it('detects circle intersecting polygon via edge proximity', () => {
    // Circle centred just outside square but radius reaches inside
    expect(circleIntersectsPolygon(0.0005, -0.0002, 30, square)).toBe(true)
    // Circle entirely outside, too small to reach
    expect(circleIntersectsPolygon(0.0005, -0.01, 10, square)).toBe(false)
    // Circle centre inside polygon
    expect(circleIntersectsPolygon(0.0005, 0.0005, 5, square)).toBe(true)
  })

  it('circleIntersectionAreaM2: full circle inside polygon ≈ πr²', () => {
    // Large square (~111 m × 111 m) fully contains a 5 m radius circle centred inside
    const bigSquare: [number, number][] = [
      [0, 0], [0, 0.01], [0.01, 0.01], [0.01, 0],
    ]
    const full = circleIntersectionAreaM2(0.005, 0.005, 5, bigSquare)
    expect(full).toBeCloseTo(Math.PI * 25, 0)
  })

  it('circleIntersectionAreaM2: circle entirely outside polygon ≈ 0', () => {
    const area = circleIntersectionAreaM2(0.005, 0.02, 5, square)
    expect(area).toBeLessThan(1)
  })

  it('circleIntersectionAreaM2: circle half inside polygon ≈ πr²/2', () => {
    // Circle centred exactly on the right edge of the square (lon = 0.001)
    const half = circleIntersectionAreaM2(0.0005, 0.001, 50, square)
    const halfExpected = Math.PI * 50 * 50 / 2
    expect(half).toBeGreaterThan(halfExpected * 0.88)
    expect(half).toBeLessThan(halfExpected * 1.12)
  })

  it('sums first uncertainty circle areas', () => {
    const area = sumCircleAreasM2([
      { uncertainty_regions: [{ radius_m: 10 }] },
      { uncertainty_regions: [{ radius_m: 20 }] },
      { uncertainty_regions: [] },
    ])

    expect(area).toBeCloseTo(Math.PI * 500)
  })
})
