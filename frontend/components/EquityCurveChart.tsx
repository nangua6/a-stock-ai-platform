'use client'

import { useRef, useEffect, useState } from 'react'
import { formatPrice } from '@/lib/utils'

interface EquityCurveChartProps {
  data: { date: string; equity: number }[]
  initialCapital: number
}

/**
 * Lightweight equity curve chart using SVG.
 */
export function EquityCurveChart({ data, initialCapital }: EquityCurveChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [w, setW] = useState(800)
  const h = 250

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
    return <div className="h-48 flex items-center justify-center text-neutral-400 text-sm">NO DATA</div>
  }

  const margin = { top: 10, right: 60, bottom: 25, left: 10 }
  const innerW = w - margin.left - margin.right
  const innerH = h - margin.top - margin.bottom

  const equities = data.map(d => d.equity)
  const minEq = Math.min(...equities, initialCapital)
  const maxEq = Math.max(...equities, initialCapital)
  const pad = (maxEq - minEq) * 0.1 || 1
  const yMin = minEq - pad
  const yMax = maxEq + pad

  const xScale = (i: number) => margin.left + (i / (data.length - 1)) * innerW
  const yScale = (v: number) => margin.top + (1 - (v - yMin) / (yMax - yMin)) * innerH

  // Build line path
  const linePath = data
    .map((d, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(d.equity)}`)
    .join(' ')

  // Build fill area
  const areaPath = `${linePath} L ${xScale(data.length - 1)} ${yScale(yMin)} L ${xScale(0)} ${yScale(yMin)} Z`

  // Initial capital reference line
  const refY = yScale(initialCapital)

  return (
    <div ref={containerRef} className="w-full overflow-hidden">
      <svg width={w} height={h} className="select-none">
        {/* Grid */}
        {[0, 0.25, 0.5, 0.75, 1].map(ratio => {
          const y = margin.top + ratio * innerH
          const val = yMax - ratio * (yMax - yMin)
          return (
            <g key={ratio}>
              <line x1={margin.left} y1={y} x2={w - margin.right} y2={y} stroke="#f0f0f0" strokeWidth={0.5} />
              <text x={w - margin.right + 4} y={y + 4} fontSize={10} fill="#999">
                {formatPrice(val)}
              </text>
            </g>
          )
        })}

        {/* Reference line (initial capital) */}
        <line
          x1={margin.left} y1={refY} x2={w - margin.right} y2={refY}
          stroke="#d1d5db" strokeWidth={1} strokeDasharray="4 4"
        />
        <text x={margin.left + 4} y={refY - 4} fontSize={9} fill="#9ca3af">
          初始资金
        </text>

        {/* Area fill */}
        <path d={areaPath} fill="url(#eqGradient)" />

        {/* Line */}
        <path d={linePath} fill="none" stroke="#3b82f6" strokeWidth={1.5} />

        {/* Data points */}
        {data.map((d, i) => (
          <circle
            key={i}
            cx={xScale(i)} cy={yScale(d.equity)}
            r={2} fill="#3b82f6" opacity={0.6}
          >
            <title>{d.date}: {formatPrice(d.equity)}</title>
          </circle>
        ))}

        {/* Date labels */}
        {data.filter((_, i) => i % Math.max(1, Math.floor(data.length / 5)) === 0).map((d, _, arr) => {
          const idx = data.indexOf(d)
          return (
            <text key={idx} x={xScale(idx)} y={h - 4} fontSize={9} fill="#999" textAnchor="middle">
              {d.date.slice(5)}
            </text>
          )
        })}

        {/* Gradient definition */}
        <defs>
          <linearGradient id="eqGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.15} />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.02} />
          </linearGradient>
        </defs>
      </svg>
    </div>
  )
}
