import { describe, expect, it } from 'vitest'
import {
  circleIntersectsPolygon,
  circleIntersectionAreaM2,
  pointInPolygon,
  polygonAreaM2,
  sumCircleAreasM2,
  unionCircleAreaWithinPolygonM2,
} from './geoUtils'

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

  it('unionCircleAreaWithinPolygonM2 sums non-overlapping circles inside a large polygon', () => {
    const bigSquare: [number, number][] = [
      [0, 0], [0, 0.01], [0.01, 0.01], [0.01, 0],
    ]
    const circles = [
      { centerLat: 0.004, centerLon: 0.004, radiusM: 20 },
      { centerLat: 0.006, centerLon: 0.006, radiusM: 20 },
    ]

    const union = unionCircleAreaWithinPolygonM2(circles, bigSquare, 80000)
    const expected = circles.reduce(
      (sum, circle) => sum + circleIntersectionAreaM2(circle.centerLat, circle.centerLon, circle.radiusM, bigSquare),
      0,
    )

    expect(union).toBeGreaterThan(expected * 0.9)
    expect(union).toBeLessThan(expected * 1.1)
  })

  it('unionCircleAreaWithinPolygonM2 counts fully overlapping circles once', () => {
    const bigSquare: [number, number][] = [
      [0, 0], [0, 0.01], [0.01, 0.01], [0.01, 0],
    ]
    const circles = [
      { centerLat: 0.005, centerLon: 0.005, radiusM: 25 },
      { centerLat: 0.005, centerLon: 0.005, radiusM: 25 },
    ]

    const union = unionCircleAreaWithinPolygonM2(circles, bigSquare, 80000)
    const expected = circleIntersectionAreaM2(0.005, 0.005, 25, bigSquare)

    expect(union).toBeGreaterThan(expected * 0.9)
    expect(union).toBeLessThan(expected * 1.1)
  })

  it('unionCircleAreaWithinPolygonM2 matches single circle clipping at polygon edge', () => {
    const circle = { centerLat: 0.0005, centerLon: 0.001, radiusM: 50 }

    const union = unionCircleAreaWithinPolygonM2([circle], square, 80000)
    const expected = circleIntersectionAreaM2(circle.centerLat, circle.centerLon, circle.radiusM, square)

    expect(union).toBeGreaterThan(expected * 0.88)
    expect(union).toBeLessThan(expected * 1.12)
  })

  it('unionCircleAreaWithinPolygonM2 never exceeds polygon area for overlapping oversized circles', () => {
    const area = unionCircleAreaWithinPolygonM2(
      [
        { centerLat: 0.0005, centerLon: 0.0005, radiusM: 150 },
        { centerLat: 0.00045, centerLon: 0.0005, radiusM: 150 },
        { centerLat: 0.00055, centerLon: 0.0005, radiusM: 150 },
      ],
      square,
      80000,
    )

    expect(area).toBeLessThanOrEqual(polygonAreaM2(square))
  })
})
