import React, { useState } from 'react'
import { api } from '../api/client'
import type { QcExceptionRow, QcResponse, RoleProfile } from '../types/auditiq'
import { DecisionBadge, RiskBadge, TypeChip } from '../components/Badges'

interface QcPageProps {
  data: QcResponse | null
  profile: RoleProfile
  onOpenTicket: (ticketId: string) => void
  onRefresh: () => Promise<void>
  onNotify: (msg: string, isError?: boolean) => void
}

export function QcPage({ data, profile, onOpenTicket, onRefresh, onNotify }: QcPageProps) {
  const [reviewTarget, setReviewTarget] = useState<QcExceptionRow | null>(null)
  const [qcStatus, setQcStatus] = useState<'Verified' | 'Disputed'>('Verified')
  const [qcNote, setQcNote] = useState('')
  const [busy, setBusy] = useState(false)

  if (!data) {
    return <div className="empty-state">Loading QC Intelligence Dashboard…</div>
  }

  async function handleQcSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!reviewTarget || qcNote.trim().length < 3) return
    setBusy(true)
    try {
      const res = await api.submitQcReview(reviewTarget.auditId, {
        qc_status: qcStatus,
        qc_reviewer: profile.userName,
        qc_note: qcNote.trim(),
      })
      setReviewTarget(null)
      setQcNote('')
      await onRefresh()
      onNotify(res.message)
    } catch (err) {
      onNotify(err instanceof Error ? err.message : 'Failed to save QC outcome.', true)
    } finally {
      setBusy(false)
    }
  }

  async function handleFeedbackAdvance(feedbackId: string, nextStatus: 'Queued for Tuning' | 'Applied') {
    try {
      const res = await api.updateFeedbackStatus(feedbackId, nextStatus)
      await onRefresh()
      onNotify(res.message)
    } catch (err) {
      onNotify(err instanceof Error ? err.message : 'Failed to update feedback status.', true)
    }
  }

  return (
    <div className="stack-md">
      <div>
        <h2 style={{ fontSize: 20 }}>QC Intelligence &amp; Closed-Loop Learning</h2>
        <p className="card-subtitle">
          Agent 8 surfaces auditor scoring variance, low-confidence AI decisions, disputed outcomes, and human overrides so QC reviewers focus on exceptions rather than checking every audit equally.
        </p>
      </div>

      <section className="grid-kpi-4">
        <div className="kpi-card">
          <span className="kpi-label">Avg Auditor Variance</span>
          <span className={`kpi-value ${data.auditorVariance > 9 ? 'warn' : ''}`}>{data.auditorVariance}%</span>
          <span className="kpi-meta">Target: significantly reduced</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">AI-Human Agreement</span>
          <span className="kpi-value good">{data.aiHumanAgreement}%</span>
          <span className="kpi-meta">Across audited demo dataset</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Disputed Findings</span>
          <span className={`kpi-value ${data.disputed > 0 ? 'warn' : 'good'}`}>{data.disputed}</span>
          <span className="kpi-meta">Requires QC calibration</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Closed-Loop Overrides</span>
          <span className="kpi-value">{data.feedbackCount}</span>
          <span className="kpi-meta">Captured in Feedback Store</span>
        </div>
      </section>

      <section className="grid-kpi-4" aria-label="QC Exception Categories">
        {data.focusBuckets.map((b) => (
          <div key={b.title} className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong style={{ fontSize: 14 }}>{b.title}</strong>
              <span className={`badge ${b.count > 0 ? 'review' : 'pass'}`}>{b.count}</span>
            </div>
            <p className="card-subtitle" style={{ marginTop: 8 }}>{b.description}</p>
          </div>
        ))}
      </section>

      {/* Auditor Consistency Table */}
      <section className="card card-flush">
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
          <h3>Auditor Consistency &amp; Outlier Detection</h3>
          <p className="card-subtitle">Dynamically calculated from live assignments, overrides, and QC outcomes.</p>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Auditor</th>
                <th>Audits Assigned</th>
                <th>Avg Score</th>
                <th>AI Overrides</th>
                <th>QC Disputed</th>
                <th>AI-Human Agreement</th>
                <th>Scoring Variance</th>
                <th>QC Focus</th>
              </tr>
            </thead>
            <tbody>
              {data.auditors.map((a) => (
                <tr key={a.name}>
                  <td><strong>{a.name}</strong></td>
                  <td className="mono">{a.audits}</td>
                  <td className="mono">{a.avgScore}%</td>
                  <td className="mono">{a.overrides}</td>
                  <td className="mono">{a.disputed}</td>
                  <td className="mono">{a.agreement}%</td>
                  <td className="mono" style={{ fontWeight: 700, color: a.variance >= 10 ? 'var(--fail)' : undefined }}>
                    {a.variance}%
                  </td>
                  <td><DecisionBadge status={a.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* QC Exception Review Queue */}
      <section className="card card-flush">
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
          <h3>Targeted QC Exception Queue</h3>
          <p className="card-subtitle">Verify or dispute high-risk audits, AI-human overrides, and low-confidence findings.</p>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Auditor</th>
                <th>Score / Risk</th>
                <th>Exception Drivers</th>
                <th>QC Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {data.exceptions.map((ex) => (
                <tr key={ex.auditId}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <TypeChip type={ex.ticketType} />
                      <button type="button" className="btn-link mono" onClick={() => onOpenTicket(ex.ticketId)}>
                        {ex.ticketId}
                      </button>
                    </div>
                    <span className="cell-sub">{ex.shortDescription}</span>
                  </td>
                  <td>{ex.auditor}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span className="mono">{ex.auditScore}%</span>
                      <RiskBadge band={ex.riskBand} />
                    </div>
                  </td>
                  <td>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {ex.exceptionReasons.map((r) => (
                        <span key={r} className="badge neutral">{r}</span>
                      ))}
                    </div>
                  </td>
                  <td>
                    <DecisionBadge status={ex.qcStatus} />
                    {ex.qcNote ? <span className="cell-sub">{ex.qcNote}</span> : null}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => {
                        setReviewTarget(ex)
                        setQcStatus(ex.qcStatus === 'Disputed' ? 'Verified' : 'Disputed')
                        setQcNote(ex.qcNote || '')
                      }}
                    >
                      QC Review
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Closed-Loop Learning Feedback Store (Proposal Section 24) */}
      <section className="card card-flush">
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
          <h3>Closed-Loop Learning Feedback Store</h3>
          <p className="card-subtitle">
            Proposal Section 24: AI Decision → Auditor Review → Override → Feedback Store → Rule / Prompt / Retrieval Refinement.
          </p>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Ticket &amp; Criterion</th>
                <th>AI → Auditor</th>
                <th>Why AI Differed</th>
                <th>Refinement Target</th>
                <th>Auditor</th>
                <th>Loop Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {data.feedbackLoop.length === 0 ? (
                <tr>
                  <td colSpan={7} className="empty-state">No overrides logged yet. Override any finding in Ticket Detail to feed the learning loop.</td>
                </tr>
              ) : (
                data.feedbackLoop.map((fb) => (
                  <tr key={fb.feedback_id}>
                    <td>
                      <button type="button" className="btn-link mono" onClick={() => onOpenTicket(fb.ticket_id)}>
                        {fb.ticket_id}
                      </button>
                      <span className="cell-sub">{fb.criterion_name}</span>
                    </td>
                    <td>
                      <span className="mono">{fb.ai_decision} → <strong>{fb.auditor_decision}</strong></span>
                    </td>
                    <td style={{ maxWidth: 300 }}>{fb.reason}</td>
                    <td><span className="badge brand">{fb.improvement_target}</span></td>
                    <td>{fb.auditor}</td>
                    <td><DecisionBadge status={fb.applied_status} /></td>
                    <td>
                      {fb.applied_status === 'Captured' ? (
                        <button
                          type="button"
                          className="btn btn-subtle btn-sm"
                          onClick={() => handleFeedbackAdvance(fb.feedback_id, 'Queued for Tuning')}
                        >
                          Queue Tuning
                        </button>
                      ) : fb.applied_status === 'Queued for Tuning' ? (
                        <button
                          type="button"
                          className="btn btn-success btn-sm"
                          onClick={() => handleFeedbackAdvance(fb.feedback_id, 'Applied')}
                        >
                          Mark Applied
                        </button>
                      ) : (
                        <span style={{ fontSize: 12, color: 'var(--pass)', fontWeight: 600 }}>Tuned</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* QC Review Modal */}
      {reviewTarget ? (
        <div className="modal-backdrop" onClick={() => setReviewTarget(null)} role="dialog" aria-modal="true">
          <form className="modal-card" onClick={(e) => e.stopPropagation()} onSubmit={handleQcSubmit}>
            <div className="modal-head">
              <div>
                <span className="breadcrumb">QC REVIEW · {reviewTarget.ticketId}</span>
                <h3 style={{ marginTop: 4 }}>Approve or Dispute Audit Outcome</h3>
              </div>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setReviewTarget(null)}>
                Close
              </button>
            </div>
            <div>
              <label className="field-label" htmlFor="qc-outcome">QC Determination</label>
              <select
                id="qc-outcome"
                className="select"
                value={qcStatus}
                onChange={(e) => setQcStatus(e.target.value as 'Verified' | 'Disputed')}
              >
                <option value="Verified">Verified — Audit Quality Approved</option>
                <option value="Disputed">Disputed — Flag Inconsistency for Recalibration</option>
              </select>
            </div>
            <div>
              <label className="field-label" htmlFor="qc-note">QC Reviewer Notes</label>
              <textarea
                id="qc-note"
                className="textarea"
                placeholder="Document QC observations, scoring variance notes, or policy alignment feedback…"
                value={qcNote}
                onChange={(e) => setQcNote(e.target.value)}
                required
              />
            </div>
            <div className="modal-foot">
              <button type="button" className="btn btn-secondary" onClick={() => setReviewTarget(null)}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={busy}>
                {busy ? 'Saving…' : 'Save QC Outcome'}
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </div>
  )
}
