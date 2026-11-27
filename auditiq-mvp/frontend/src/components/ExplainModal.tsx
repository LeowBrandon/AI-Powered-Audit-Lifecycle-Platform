import React from 'react'
import type { AuditCriterionResult } from '../types/auditiq'
import { ConfidenceBadge, DecisionBadge } from './Badges'

interface ExplainModalProps {
  ticketId: string
  result: AuditCriterionResult | null
  onClose: () => void
  onOpenPolicy: (policyQuery: string) => void
}

export function ExplainModal({ ticketId, result, onClose, onOpenPolicy }: ExplainModalProps) {
  if (!result) return null

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-label="Explainable AI Decision">
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <span className="breadcrumb">EXPLAINABLE AI · {ticketId}</span>
            <h3 style={{ marginTop: 4 }}>Why did AuditIQ mark &ldquo;{result.criterion}&rdquo; as {result.status}?</h3>
          </div>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
            Close
          </button>
        </div>

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <DecisionBadge status={result.status} />
          <ConfidenceBadge confidence={result.confidence} tier={result.confidenceTier} />
          <span className="badge neutral">
            {result.method === 'deterministic' ? 'Deterministic Rule Engine' : 'AI Reasoning Agent'}
          </span>
        </div>

        <div className="stack-sm">
          <div className="explain-row">
            <div className="explain-row-label">Audit Requirement</div>
            <div>{result.requirement} — {result.reason}</div>
          </div>

          <div className="explain-row">
            <div className="explain-row-label">Detected Evidence ({result.source})</div>
            <div>{result.detectedEvidence || 'None detected.'}</div>
          </div>

          {result.missingEvidence ? (
            <div className="explain-row" style={{ borderColor: 'hsl(0 72% 85%)', background: 'var(--fail-soft)' }}>
              <div className="explain-row-label" style={{ color: 'var(--fail)' }}>Missing Evidence</div>
              <div>{result.missingEvidence}</div>
            </div>
          ) : null}

          <div className="explain-row">
            <div className="explain-row-label">Governing Policy Reference</div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <span className="mono">{result.policyRef}</span>
              <button
                type="button"
                className="btn btn-subtle btn-sm"
                onClick={() => {
                  onClose()
                  onOpenPolicy(result.criterion)
                }}
              >
                View in Policy KB →
              </button>
            </div>
          </div>

          <div className="explain-row">
            <div className="explain-row-label">Sources Inspected by Evidence Extraction Agent</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
              {result.searchedSources.map((src) => (
                <span key={src} className="type-chip">
                  {src}
                </span>
              ))}
            </div>
          </div>

          <div className="explain-row">
            <div className="explain-row-label">Recommended Governance Action</div>
            <div>{result.recommendation}</div>
          </div>
        </div>

        <div className="modal-foot">
          <button type="button" className="btn btn-primary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
