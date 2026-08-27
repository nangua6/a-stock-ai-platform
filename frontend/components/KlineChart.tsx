'use client'

import { useRef, useEffect, useState } from 'react'
import type { KlineBar } from '@/lib/types'

interface KlineChartProps {
  data: KlineBar[]
  width?: number
  height?: number
}

/**
 * Lightweight candlestick K-line chart using SVG.
 * No external charting library dependency.
 */
export function KlineChart({ data, width = 800, height = 400 }: KlineChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [w, setW] = useState(width)

  useEffect(() => {
    if (!containerRef.current) return
    const obs = new ResizeObserver(entries => {
      const entry = entries[0]
      if (entry) setW(Math.floor(entry.contentRect.width))
    })
    obs.observe(containerRef.current)
    return () => obs.disconnect()
  }, [])

  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-neutral-400 text-sm">
        NO DATA
      </div>
    )
  }

  const margin = { top: 10, right: 60, bottom: 30, left: 10 }
  const chartH = height * 0.65
  const volH = height * 0.2
  const gapH = height * 0.05
  const innerW = w - margin.left - margin.right
  const totalBars = data.length
  const barWidth = Math.max(1, (innerW / totalBars) * 0.7)
  const barGap = innerW / totalBars

  // Price range
  const allHighs = data.map(d => d.high)
  const allLows = data.map(d => d.low)
  const priceHigh = Math.max(...allHighs)
  const priceLow = Math.min(...allLows)
  const pricePad = (priceHigh - priceLow) * 0.05 || 1
  const pHigh = priceHigh + pricePad
  const pLow = priceLow - pricePad

  // Volume range
  const allVols = data.map(d => d.volume)
  const maxVol = Math.max(...allVols) || 1

  const priceToY = (p: number) => margin.top + (1 - (p - pLow) / (pHigh - pLow)) * chartH
  const volToY = (v: number) => margin.top + chartH + gapH + (1 - v / maxVol) * volH
  const barX = (i: number) => margin.left + i * barGap + barGap / 2

  // MA lines
  const ma5 = computeMA(data, 5)
  const ma10 = computeMA(data, 10)
  const ma20 = computeMA(data, 20)

  return (
    <div ref={containerRef} className="w-full overflow-hidden">
      <svg width={w} height={height} className="select-none">
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map(ratio => {
          const y = margin.top + ratio * chartH
          const price = pHigh - ratio * (pHigh - pLow)
          return (
            <g key={ratio}>
              <line x1={margin.left} y1={y} x2={w - margin.right} y2={y}
                stroke="#f0f0f0" strokeWidth={0.5} />
              <text x={w - margin.right + 4} y={y + 4} fontSize={10} fill="#999">
                {price.toFixed(2)}
              </text>
            </g>
          )
        })}

        {/* Candlesticks */}
        {data.map((bar, i) => {
          const x = barX(i)
          const isUp = bar.close >= bar.open
          const color = isUp ? '#ef4444' : '#22c55e'
          const bodyTop = priceToY(Math.max(bar.open, bar.close))
          const bodyBot = priceToY(Math.min(bar.open, bar.close))
          const bodyH = Math.max(1, bodyBot - bodyTop)

          return (
            <g key={i}>
              {/* Wick */}
              <line
                x1={x} y1={priceToY(bar.high)}
                x2={x} y2={priceToY(bar.low)}
                stroke={color} strokeWidth={1}
              />
              {/* Body */}
              <rect
                x={x - barWidth / 2} y={bodyTop}
                width={barWidth} height={bodyH}
                fill={isUp ? color : color}
                stroke={color} strokeWidth={0.5}
              />
              {/* Volume bar */}
              <rect
                x={x - barWidth / 2} y={volToY(bar.volume)}
                width={barWidth}
                height={margin.top + chartH + gapH + volH - volToY(bar.volume)}
                fill={isUp ? '#fca5a5' : '#86efac'}
                opacity={0.6}
              />
            </g>
          )
        })}

        {/* MA lines */}
        <PolylineMA data={ma5} color="#f59e0b" barX={barX} priceToY={priceToY} />
        <PolylineMA data={ma10} color="#3b82f6" barX={barX} priceToY={priceToY} />
        <PolylineMA data={ma20} color="#8b5cf6" barX={barX} priceToY={priceToY} />

        {/* Volume label */}
        <text x={margin.left + 4} y={margin.top + chartH + gapH + 12} fontSize={10} fill="#999">
          VOL
        </text>

        {/* Date labels */}
        {data.filter((_, i) => i % Math.max(1, Math.floor(totalBars / 6)) === 0).map((bar, _, arr) => {
          const idx = data.indexOf(bar)
          const x = barX(idx)
          return (
            <text key={idx} x={x} y={height - 4} fontSize={9} fill="#999" textAnchor="middle">
              {bar.trade_date.slice(5)}
            </text>
          )
        })}

        {/* MA legend */}
        <g transform={`translate(${margin.left + 40}, ${margin.top + 12})`}>
          <line x1={0} y1={0} x2={12} y2={0} stroke="#f59e0b" strokeWidth={1.5} />
          <text x={16} y={4} fontSize={10} fill="#f59e0b">MA5</text>
          <line x1={50} y1={0} x2={62} y2={0} stroke="#3b82f6" strokeWidth={1.5} />
          <text x={66} y={4} fontSize={10} fill="#3b82f6">MA10</text>
          <line x1={108} y1={0} x2={120} y2={0} stroke="#8b5cf6" strokeWidth={1.5} />
          <text x={124} y={4} fontSize={10} fill="#8b5cf6">MA20</text>
        </g>
      </svg>
    </div>
  )
}

function computeMA(data: KlineBar[], period: number): (number | null)[] {
  return data.map((_, i) => {
    if (i < period - 1) return null
    let sum = 0
    for (let j = i - period + 1; j <= i; j++) sum += data[j].close
    return sum / period
  })
}

function PolylineMA({
  data, color, barX, priceToY,
}: {
  data: (number | null)[]
  color: string
  barX: (i: number) => number
  priceToY: (p: number) => number
}) {
  const points: string[] = []
  data.forEach((val, i) => {
    if (val !== null) {
      points.push(`${barX(i)},${priceToY(val)}`)
    }
  })
  if (points.length < 2) return null
  return (
    <polyline
      points={points.join(' ')}
      fill="none"
      stroke={color}
      strokeWidth={1}
      opacity={0.8}
    />
  )
}
