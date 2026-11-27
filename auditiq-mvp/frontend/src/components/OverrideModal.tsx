import React, { useState } from 'react'
import type { AuditFinding, RoleProfile } from '../types/auditiq'
import { DecisionBadge } from './Badges'

export type FindingActionMode =
  | 'APPROVE_FINDING'
  | 'OVERRIDE_PASS'
  | 'OVERRIDE_FAIL'
  | 'REQUEST_EVIDENCE'

interface OverrideModalProps {
  ticketId: string
  finding: AuditFinding | null
  initialMode: FindingActionMode
  profile: RoleProfile
  onClose: () => void
  onSubmit: (payload: {
    decision: FindingActionMode
    note: string
    auditor: string
    role: string
    improvement_target:
      | 'Audit Rules'
      | 'Prompts'
      | 'RAG Retrieval'
      | 'Evidence Extraction'
      | 'Confidence Thresholds'
  }) => Promise<void>
}

export function OverrideModal({
  ticketId,
  finding,
  initialMode,
  profile,
  onClose,
  onSubmit,
}: OverrideModalProps) {
  const [decision, setDecision] = useState<FindingActionMode>(initialMode)
  const [note, setNote] = useState(
    initialMode === 'APPROVE_FINDING'
      ? 'Confirmed AI finding against ticket evidence and enterprise policy.'
      : initialMode === 'REQUEST_EVIDENCE'
        ? 'Requested missing documentation from ticket owner prior to closure.'
        : '',
  )
  const [target, setTarget] = useState<
    'Audit Rules' | 'Prompts' | 'RAG Retrieval' | 'Evidence Extraction' | 'Confidence Thresholds'
  >('Evidence Extraction')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  if (!finding) return null

  const isOverride = decision === 'OVERRIDE_PASS' || decision === 'OVERRIDE_FAIL'

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (note.trim().length < 3) {
      setErr('Please enter a governance rationale (minimum 3 characters) for the audit trail.')
      return
    }
    setBusy(true)
    setErr('')
    try {
      await onSubmit({
        decision,
        note: note.trim(),
        auditor: profile.userName,
        role: profile.role,
        improvement_target: target,
      })
      onClose()
    } catch (error) {
      setErr(error instanceof Error ? error.message : 'Failed to record governance action.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-label="Human-in-the-Loop Governance Decision">
      <form className="modal-card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <div className="modal-head">
          <div>
            <span className="breadcrumb">HUMAN-IN-THE-LOOP GOVERNANCE · {ticketId}</span>
            <h3 style={{ marginTop: 4 }}>Auditor Decision — {finding.criterion}</h3>
          </div>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
            Cancel
          </button>
        </div>

        <div className="explain-row">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <strong>AI Evaluation</strong>
            <DecisionBadge status={finding.aiStatus} />
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{finding.description}</div>
        </div>

        <div>
          <label className="field-label" htmlFor="hitl-decision">Governance Action</label>
          <select
            id="hitl-decision"
            className="select"
            value={decision}
            onChange={(e) => setDecision(e.target.value as FindingActionMode)}
          >
            <option value="APPROVE_FINDING">Approve Finding (Confirm AI Result)</option>
            <option value="OVERRIDE_PASS">Override AI → Mark PASS (Logs Closed-Loop Feedback)</option>
            <option value="OVERRIDE_FAIL">Override AI → Escalate as FAIL (Logs Closed-Loop Feedback)</option>
            <option value="REQUEST_EVIDENCE">Request Evidence from Ticket Owner</option>
          </select>
        </div>

        {isOverride ? (
          <div>
            <label className="field-label" htmlFor="hitl-target">Closed-Loop Learning Target (Why did AI differ?)</label>
            <select
              id="hitl-target"
              className="select"
              value={target}
              onChange={(e) =>
                setTarget(
                  e.target.value as
                    | 'Audit Rules'
                    | 'Prompts'
                    | 'RAG Retrieval'
                    | 'Evidence Extraction'
                    | 'Confidence Thresholds',
                )
              }
            >
              <option value="Evidence Extraction">Evidence Extraction (external or unparsed artifact)</option>
              <option value="Audit Rules">Audit Rules (policy exception or rule refinement)</option>
              <option value="Prompts">Prompts (AI reasoning clarity)</option>
              <option value="RAG Retrieval">RAG Retrieval (policy matching accuracy)</option>
              <option value="Confidence Thresholds">Confidence Thresholds (calibration adjustment)</option>
            </select>
          </div>
        ) : null}

        <div>
          <label className="field-label" htmlFor="hitl-note">
            Auditor Justification (recorded immutably in Audit Trail)
          </label>
          <textarea
            id="hitl-note"
            className="textarea"
            placeholder="Explain why you approved, overrode, or requested additional evidence..."
            value={note}
            onChange={(e) => setNote(e.target.value)}
            required
          />
        </div>

        {err ? <div style={{ color: 'var(--fail)', fontSize: 13, fontWeight: 500 }}>{err}</div> : null}

        <div className="modal-foot">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? 'Recording…' : 'Record Governance Decision'}
          </button>
        </div>
      </form>
    </div>
  )
}
