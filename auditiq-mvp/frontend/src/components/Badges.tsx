import React from 'react'

export function RiskBadge({ band, score }: { band: string; score?: number }) {
  const cls = band.toLowerCase()
  return (
    <span className={`badge ${cls}`}>
      {score !== undefined ? <span className="mono">{Math.round(score)}</span> : null}
      <span>{band}</span>
    </span>
  )
}

export function DecisionBadge({ status }: { status: string }) {
  const low = status.toLowerCase()
  const cls =
    low === 'pass' || low === 'verified' || low === 'approved' || low === 'auto-closed' || low === 'applied' || low === 'stable'
      ? 'pass'
      : low === 'fail' || low === 'disputed' || low === 'escalated' || low === 'outlier' || low === 'critical' || low === 'high'
        ? 'fail'
        : low === 'review' || low === 'needs review' || low === 'pending' || low === 'evidence requested' || low === 'queued for tuning' || low === 'in review'
          ? 'review'
          : 'neutral'
  return <span className={`badge ${cls}`}>{status}</span>
}

export function TypeChip({ type }: { type: string }) {
  return <span className="type-chip">{type}</span>
}

export function ConfidenceBadge({ confidence, tier }: { confidence: number; tier?: string }) {
  const cls = confidence >= 95 ? 'pass' : confidence >= 80 ? 'brand' : 'review'
  return (
    <span className={`badge ${cls}`} title={tier || 'AI Confidence'}>
      <span className="mono">{Math.round(confidence)}%</span>
      {tier ? <span>· {tier}</span> : null}
    </span>
  )
}
