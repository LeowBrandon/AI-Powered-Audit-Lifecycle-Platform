import React, { useState } from 'react'
import type { TrendPoint } from '../types/auditiq'

export function ComplianceTrendChart({ data }: { data: TrendPoint[] }) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null)
  if (!data || data.length === 0) {
    return <div className="empty-state">No trend data available yet.</div>
  }

  const width = 580
  const height = 210
  const padL = 40
  const padR = 20
  const padT = 18
  const padB = 34
  const plotW = width - padL - padR
  const plotH = height - padT - padB

  const values = data.map((d) => d.value)
  const minY = Math.max(50, Math.floor((Math.min(...values) - 6) / 5) * 5)
  const maxY = 100
  const spanY = Math.max(10, maxY - minY)

  const coords = data.map((d, i) => {
    const x =
      data.length === 1
        ? padL + plotW / 2
        : padL + (i / (data.length - 1)) * plotW
    const y = padT + ((maxY - d.value) / spanY) * plotH
    return { ...d, x, y }
  })

  const linePath = coords
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(' ')
  const areaPath = `${linePath} L ${coords[coords.length - 1].x.toFixed(1)} ${(padT + plotH).toFixed(1)} L ${coords[0].x.toFixed(1)} ${(padT + plotH).toFixed(1)} Z`

  const ticks = [maxY, Math.round(minY + spanY * 0.66), Math.round(minY + spanY * 0.33), minY]

  return (
    <div className="svg-chart-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="215" role="img" aria-label="Compliance trend line chart">
        <defs>
          <linearGradient id="auditTrendFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(221 83% 48%)" stopOpacity="0.18" />
            <stop offset="100%" stopColor="hsl(221 83% 48%)" stopOpacity="0.01" />
          </linearGradient>
        </defs>
        {ticks.map((t) => {
          const ty = padT + ((maxY - t) / spanY) * plotH
          return (
            <g key={t}>
              <line x1={padL} y1={ty} x2={width - padR} y2={ty} stroke="hsl(214 24% 90%)" strokeWidth="1" />
              <text x={padL - 8} y={ty + 4} textAnchor="end" fontSize="11" fill="hsl(215 15% 48%)">
                {t}%
              </text>
            </g>
          )
        })}
        <path d={areaPath} fill="url(#auditTrendFill)" />
        <path d={linePath} fill="none" stroke="hsl(221 83% 48%)" strokeWidth="2.8" strokeLinejoin="round" strokeLinecap="round" />
        {coords.map((p, idx) => {
          const active = hoverIdx === idx
          return (
            <g
              key={p.period}
              onMouseEnter={() => setHoverIdx(idx)}
              onMouseLeave={() => setHoverIdx(null)}
              style={{ cursor: 'pointer' }}
            >
              <circle
                cx={p.x}
                cy={p.y}
                r={active ? 6 : 4.2}
                fill="#fff"
                stroke="hsl(221 83% 48%)"
                strokeWidth={active ? 3 : 2.5}
              />
              <text x={p.x} y={height - 10} textAnchor="middle" fontSize="11" fill="hsl(215 15% 48%)" fontWeight={active ? 700 : 500}>
                {p.month}
              </text>
              {active ? (
                <g>
                  <rect
                    x={Math.min(Math.max(p.x - 46, padL), width - 102)}
                    y={Math.max(p.y - 40, 4)}
                    width="92"
                    height="28"
                    rx="6"
                    fill="hsl(222 47% 11%)"
                  />
                  <text
                    x={Math.min(Math.max(p.x, padL + 46), width - 56)}
                    y={Math.max(p.y - 22, 22)}
                    textAnchor="middle"
                    fontSize="11"
                    fontWeight="700"
                    fill="#fff"
                  >
                    {p.value}% ({p.count})
                  </text>
                </g>
              ) : null}
            </g>
          )
        })}
      </svg>
    </div>
  )
}

export function HorizontalBarList({
  items,
  maxValue = 100,
  suffix = '%',
  toneFn,
}: {
  items: { label: string; value: number; sub?: string }[]
  maxValue?: number
  suffix?: string
  toneFn?: (val: number) => 'pass' | 'review' | 'fail' | 'critical' | ''
}) {
  if (!items.length) {
    return <div className="empty-state">No records in this category.</div>
  }
  return (
    <div className="bar-list">
      {items.map((item) => {
        const pct = Math.max(2, Math.min(100, (item.value / maxValue) * 100))
        const tone = toneFn ? toneFn(item.value) : ''
        return (
          <div className="bar-item" key={item.label}>
            <div>
              <div className="bar-label" title={item.label}>
                {item.label}
              </div>
              {item.sub ? <span className="cell-sub">{item.sub}</span> : null}
            </div>
            <div className="bar-track">
              <div className={`bar-fill ${tone}`} style={{ width: `${pct}%` }} />
            </div>
            <div className="bar-val">
              {item.value}
              {suffix}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function ScoreRing({ score, label = 'Compliance' }: { score: number; label?: string }) {
  const clamped = Math.max(0, Math.min(100, score))
  const color =
    clamped >= 90
      ? 'hsl(160 84% 30%)'
      : clamped >= 75
        ? 'hsl(35 92% 40%)'
        : 'hsl(0 72% 46%)'

  return (
    <div className="score-ring-box">
      <div
        className="score-ring"
        style={{
          background: `conic-gradient(${color} ${clamped * 3.6}deg, hsl(214 28% 91%) 0deg)`,
        }}
      >
        <div className="score-ring-inner">
          <span className="score-ring-num num">{Math.round(clamped)}%</span>
          <span className="score-ring-sub">{label}</span>
        </div>
      </div>
    </div>
  )
}

export function RiskBreakdownChart({ breakdown }: { breakdown: Record<string, number> }) {
  const entries = Object.entries(breakdown || {})
  const maxVal = Math.max(25, ...entries.map(([, v]) => v))
  return (
    <div className="bar-list">
      {entries.map(([factor, pts]) => {
        const pct = Math.min(100, (pts / maxVal) * 100)
        const tone = pts >= 18 ? 'fail' : pts >= 8 ? 'review' : ''
        return (
          <div className="bar-item" key={factor}>
            <div className="bar-label">{factor}</div>
            <div className="bar-track">
              <div className={`bar-fill ${tone}`} style={{ width: `${pct}%` }} />
            </div>
            <div className="bar-val">+{pts}</div>
          </div>
        )
      })}
    </div>
  )
}
