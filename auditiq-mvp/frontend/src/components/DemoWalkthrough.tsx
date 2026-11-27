import React from 'react'
import type { TicketDetail } from '../types/auditiq'

interface DemoWalkthroughProps {
  ticket: TicketDetail
  busy: boolean
  onRemediate: (actionType: 'business_approval' | 'rollback_plan' | 'post_validation' | 'close_ticket') => void
  onExplainBiz: () => void
  onOpenDashboard: () => void
  onResetDemo: () => void
}

export function DemoWalkthrough({
  ticket,
  busy,
  onRemediate,
  onExplainBiz,
  onOpenDashboard,
  onResetDemo,
}: DemoWalkthroughProps) {
  if (ticket.id !== 'CR001992') return null

  const bizPassed = ticket.results.some((r) => r.criterion === 'Business approval' && r.status === 'PASS')
  const rbPassed = ticket.results.some((r) => r.criterion === 'Rollback plan' && r.status === 'PASS')
  const pirPassed = ticket.results.some((r) => r.criterion === 'Post-implementation review' && r.status === 'PASS')
  const isClosed = ticket.state === 'Closed'
  const isLow = ticket.riskBand === 'LOW'

  const steps = [
    { n: 1, label: 'CR001992 arrives', done: true },
    { n: 2, label: 'AI extracts evidence', done: true },
    { n: 3, label: 'Score & risk assigned', done: true },
    { n: 4, label: 'Explain missing approval', done: true },
    { n: 5, label: 'Proactive alert issued', done: true },
    { n: 6, label: 'Upload business approval', done: bizPassed },
    { n: 7, label: 'Complete rollback & PIR', done: rbPassed && pirPassed },
    { n: 8, label: 'Risk drops HIGH → LOW', done: isLow },
    { n: 9, label: 'Close & audit record', done: isClosed },
    { n: 10, label: 'Dashboard updated', done: isClosed && isLow },
  ]

  const nextPendingIndex = steps.findIndex((s) => !s.done)

  return (
    <section className="demo-banner" aria-label="Proposal Section 29 End-to-End Demo Walkthrough">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
        <div>
          <span className="mono" style={{ fontSize: 11, color: 'hsl(214 80% 78%)', fontWeight: 600 }}>
            PROPOSAL SECTION 29 · INTERACTIVE 10-STEP END-TO-END DEMO
          </span>
          <h3 style={{ marginTop: 4 }}>
            Extraction → AI Reasoning → Proactive Monitoring → Remediation → Automated Audit → Analytics
          </h3>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {!bizPassed ? (
            <button type="button" className="btn btn-secondary btn-sm" onClick={onExplainBiz}>
              Step 4: Explain Gap
            </button>
          ) : null}
          {!bizPassed ? (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={busy}
              onClick={() => onRemediate('business_approval')}
            >
              Step 6: Upload Business Approval
            </button>
          ) : null}
          {bizPassed && !rbPassed ? (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={busy}
              onClick={() => onRemediate('rollback_plan')}
            >
              Step 7a: Attach Rollback Runbook
            </button>
          ) : null}
          {bizPassed && rbPassed && !pirPassed ? (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={busy}
              onClick={() => onRemediate('post_validation')}
            >
              Step 7b: Record PIR Validation
            </button>
          ) : null}
          {bizPassed && rbPassed && pirPassed && !isClosed ? (
            <button
              type="button"
              className="btn btn-success btn-sm"
              disabled={busy}
              onClick={() => onRemediate('close_ticket')}
            >
              Step 9: Close Ticket &amp; Finalize Audit
            </button>
          ) : null}
          {isClosed ? (
            <>
              <button type="button" className="btn btn-success btn-sm" onClick={onOpenDashboard}>
                Step 10: View Updated Dashboard →
              </button>
              <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={onResetDemo}>
                Reset Demo
              </button>
            </>
          ) : null}
        </div>
      </div>

      <div className="demo-steps-track">
        {steps.map((s, idx) => (
          <div
            key={s.n}
            className={`demo-step-pill ${s.done ? 'done' : idx === nextPendingIndex ? 'current' : ''}`}
          >
            <span className="mono">{s.done ? '✓' : `${s.n}.`}</span>
            <span>{s.label}</span>
          </div>
        ))}
      </div>
    </section>
  )
}
