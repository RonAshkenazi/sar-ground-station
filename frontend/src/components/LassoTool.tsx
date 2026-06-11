import { useEffect, useRef, useState } from 'react'
import { Polyline, useMap, useMapEvents } from 'react-leaflet'

interface Props {
  active: boolean
  onComplete: (polygon: [number, number][]) => void
  onCancel: () => void
}

export default function LassoTool({ active, onComplete, onCancel }: Props) {
  const map = useMap()
  const drawing = useRef(false)
  const points = useRef<[number, number][]>([])
  const lastPixel = useRef<{ x: number; y: number } | null>(null)
  const [livePoints, setLivePoints] = useState<[number, number][]>([])

  useEffect(() => {
    if (!active) {
      drawing.current = false
      points.current = []
      lastPixel.current = null
      setLivePoints([])
      map.dragging.enable()
      return
    }

    map.dragging.disable()
    drawing.current = false
    points.current = []
    lastPixel.current = null
    setLivePoints([])

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Escape' || !drawing.current) return
      drawing.current = false
      points.current = []
      lastPixel.current = null
      setLivePoints([])
      map.dragging.enable()
      onCancel()
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      drawing.current = false
      map.dragging.enable()
    }
  }, [active, map, onCancel])

  useMapEvents({
    mousedown(event) {
      if (!active) return
      event.originalEvent.preventDefault()
      drawing.current = true
      const point: [number, number] = [event.latlng.lat, event.latlng.lng]
      points.current = [point]
      const pixel = map.latLngToContainerPoint(event.latlng)
      lastPixel.current = { x: pixel.x, y: pixel.y }
      setLivePoints([point])
    },
    mousemove(event) {
      if (!active || !drawing.current) return
      const pixel = map.latLngToContainerPoint(event.latlng)
      const previous = lastPixel.current
      if (previous) {
        const distance = Math.hypot(pixel.x - previous.x, pixel.y - previous.y)
        if (distance < 8) return
      }
      const point: [number, number] = [event.latlng.lat, event.latlng.lng]
      points.current = [...points.current, point]
      lastPixel.current = { x: pixel.x, y: pixel.y }
      setLivePoints(points.current)
    },
    mouseup() {
      if (!active || !drawing.current) return
      drawing.current = false
      map.dragging.enable()
      const polygon = points.current
      points.current = []
      lastPixel.current = null
      setLivePoints([])
      if (polygon.length >= 3) onComplete(polygon)
      else onCancel()
    },
  })

  if (!active) return null
  return <Polyline positions={livePoints} pathOptions={{ color: '#facc15', weight: 2, dashArray: '6 4', opacity: 0.85 }} />
}
