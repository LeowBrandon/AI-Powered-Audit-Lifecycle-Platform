import React, { useMemo, useState } from 'react'
import { api } from '../api/client'
import type {
  AuditCriterionResult,
  AuditFinding,
  EvidenceHighlight,
  PageId,
  QueueTicket,
  RoleProfile,
  TicketDetail,
} from '../types/auditiq'
import { ConfidenceBadge, DecisionBadge, RiskBadge, TypeChip } from '../components/Badges'
import { RiskBreakdownChart, ScoreRing } from '../components/Charts'
import { DemoWalkthrough } from '../components/DemoWalkthrough'
import { ExplainModal } from '../components/ExplainModal'
import { type FindingActionMode, OverrideModal } from '../components/OverrideModal'

interface TicketDetailPageProps {
  ticket: TicketDetail | null
  allTickets: QueueTicket[]
  profile: RoleProfile
  onSelectTicket: (id: string) => void
  onBackToQueue: () => void
  onTicketUpdated: (updated: TicketDetail, message: string) => void
  onOpenPolicySearch: (query: string) => void
  onNavigate: (page: PageId) => void
  onResetDemo: () => Promise<void>
  onNotify: (msg: string, isError?: boolean) => void
}

function renderHighlightedText(text: string, highlights: EvidenceHighlight[]) {
  if (!highlights.length) return text
  const match = highlights.find((h) => text.toLowerCase().includes(h.quote.toLowerCase()))
  if (!match) return text
  const idx = text.toLowerCase().indexOf(match.quote.toLowerCase())
  if (idx === -1) return text
  const before = text.slice(0, idx)
  const mid = text.slice(idx, idx + match.quote.length)
  const after = text.slice(idx + match.quote.length)
  return (
    <>
      {before}
      <mark className={`inline-highlight ${match.status.toLowerCase()}`}>{mid}</mark>
      {after}
    </>
  )
}

export function TicketDetailPage({
  ticket,
  allTickets,
  profile,
  onSelectTicket,
  onBackToQueue,
  onTicketUpdated,
  onOpenPolicySearch,
  onNavigate,
  onResetDemo,
  onNotify,
}: TicketDetailPageProps) {
  const [tab, setTab] = useState<'criteria' | 'evidence' | 'remediate' | 'trace' | 'trail'>('criteria')
  const [explainResult, setExplainResult] = useState<AuditCriterionResult | null>(null)
  const [overrideTarget, setOverrideTarget] = useState<{ finding: AuditFinding; mode: FindingActionMode } | null>(null)
  const [activeHighlightIdx, setActiveHighlightIdx] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)

  // Quick remediation form inputs
  const [approverName, setApproverName] = useState('VP Finance Applications')
  const [customNote, setCustomNote] = useState('')

  const findingByCriterion = useMemo(() => {
    const map: Record<string, AuditFinding> = {}
    for (const f of ticket?.findings || []) {
      map[f.criterion] = f
    }
    return map
  }, [ticket])

  if (!ticket) {
    return <div className="empty-state">Loading ticket audit workspace…</div>
  }

  async function handleReanalyze() {
    if (!ticket) return
    setBusy(true)
    try {
      const res = await api.reanalyze(ticket.id)
      onTicketUpdated(res.ticket, res.message)
    } catch (err) {
      onNotify(err instanceof Error ? err.message : 'Re-analysis failed.', true)
    } finally {
      setBusy(false)
    }
  }

  async function handleRemediate(
    actionType:
      | 'business_approval'
      | 'technical_approval'
      | 'rollback_plan'
      | 'post_validation'
      | 'root_cause'
      | 'customer_communication'
      | 'work_note'
      | 'close_ticket',
    noteOverride?: string,
  ) {
    if (!ticket) return
    setBusy(true)
    try {
      const res = await api.remediate(ticket.id, {
        action_type: actionType,
        actor: profile.userName,
        role: profile.role,
        approver: approverName,
        note: noteOverride ?? customNote,
      })
      setCustomNote('')
      onTicketUpdated(res.ticket, res.message)
    } catch (err) {
      onNotify(err instanceof Error ? err.message : 'Remediation action failed.', true)
    } finally {
      setBusy(false)
    }
  }

  const bizResult = ticket.results.find((r) => r.criterion === 'Business approval') || null
  const activeHighlight = activeHighlightIdx !== null ? ticket.highlights[activeHighlightIdx] : null

  return (
    <div className="stack-md">
      {/* Guided Section 29 10-Step Demo Banner when inspecting CR001992 */}
      <DemoWalkthrough
        ticket={ticket}
        busy={busy}
        onRemediate={(act) => handleRemediate(act)}
        onExplainBiz={() => bizResult && setExplainResult(bizResult)}
        onOpenDashboard={() => onNavigate('dashboard')}
        onResetDemo={onResetDemo}
      />

      {/* Top Ticket Header */}
      <section className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <button type="button" className="btn btn-secondary btn-sm" onClick={onBackToQueue}>
                ← Audit Queue
              </button>
              <select
                aria-label="Switch ticket"
                className="select"
                style={{ width: 'auto', minWidth: 210, padding: '5px 10px' }}
                value={ticket.id}
                onChange={(e) => onSelectTicket(e.target.value)}
              >
                {allTickets.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.id} · {t.type} · {t.riskBand} ({t.compliance}%)
                  </option>
                ))}
              </select>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <TypeChip type={ticket.type} />
              <h2 className="mono" style={{ fontSize: 22 }}>{ticket.id}</h2>
              <RiskBadge band={ticket.riskBand} score={ticket.risk} />
              <DecisionBadge status={ticket.auditStatus} />
              <span className="badge neutral">{ticket.samplingTier}</span>
            </div>
            <p style={{ marginTop: 6, fontSize: 15, fontWeight: 600 }}>{ticket.shortDescription}</p>
            <p style={{ marginTop: 3, fontSize: 13, color: 'var(--text-muted)' }}>
              {ticket.assignmentGroup} · {ticket.businessUnit} · Priority {ticket.priority} · State: <strong>{ticket.state}</strong> · SLA: <strong>{ticket.sla}</strong>
            </p>
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button type="button" className="btn btn-secondary" disabled={busy} onClick={handleReanalyze}>
              {busy ? 'Auditing…' : '↻ Re-Run Multi-Agent Audit'}
            </button>
            <button type="button" className="btn btn-subtle" onClick={() => onNavigate('copilot')}>
              Ask Auditor Copilot →
            </button>
            {ticket.type === 'CR' && bizResult?.status !== 'PASS' ? (
              <button
                type="button"
                className="btn btn-primary"
                disabled={busy}
                onClick={() => handleRemediate('business_approval')}
              >
                Upload Business Approval
              </button>
            ) : null}
          </div>
        </div>
      </section>

      {/* Score Ring + AI Summary + 7-Factor Risk Breakdown */}
      <div className="grid-detail-top">
        <section className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: 16 }}>
          <ScoreRing score={ticket.compliance} label="Compliance Score" />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, textAlign: 'center' }}>
            <div className="explain-row">
              <div className="explain-row-label">Risk</div>
              <strong className="mono">{Math.round(ticket.risk)}/100</strong>
            </div>
            <div className="explain-row">
              <div className="explain-row-label">AI Conf</div>
              <strong className="mono">{Math.round(ticket.confidence)}%</strong>
            </div>
            <div className="explain-row">
              <div className="explain-row-label">Decision</div>
              <strong className="mono">{ticket.decision}</strong>
            </div>
          </div>
        </section>

        <section className="card">
          <div className="card-header">
            <div>
              <h3>AI Audit Summary &amp; 7-Factor Risk Scoring Breakdown</h3>
              <p className="card-subtitle">{ticket.aiSummary}</p>
            </div>
            <span className="badge brand">Predicted Failure: {Math.round(ticket.predictedFailureProb)}%</span>
          </div>
          <RiskBreakdownChart breakdown={ticket.riskBreakdown} />
        </section>
      </div>

      {/* Workspace Tabs */}
      <div className="tab-bar" role="tablist">
        <button type="button" role="tab" className={`tab-btn ${tab === 'criteria' ? 'active' : ''}`} onClick={() => setTab('criteria')}>
          Audit Criteria &amp; Findings ({ticket.results.length})
        </button>
        <button type="button" role="tab" className={`tab-btn ${tab === 'evidence' ? 'active' : ''}`} onClick={() => setTab('evidence')}>
          AI Evidence Viewer ({ticket.highlights.length} Highlights)
        </button>
        <button type="button" role="tab" className={`tab-btn ${tab === 'remediate' ? 'active' : ''}`} onClick={() => setTab('remediate')}>
          Ticket Data &amp; Remediation
        </button>
        <button type="button" role="tab" className={`tab-btn ${tab === 'trace' ? 'active' : ''}`} onClick={() => setTab('trace')}>
          Multi-Agent Trace ({ticket.agentTrace.length} Agents)
        </button>
        <button type="button" role="tab" className={`tab-btn ${tab === 'trail' ? 'active' : ''}`} onClick={() => setTab('trail')}>
          Governance Audit Trail ({ticket.auditTrail.length})
        </button>
      </div>

      {/* TAB 1: AUDIT CRITERIA & HUMAN-IN-THE-LOOP FINDINGS */}
      {tab === 'criteria' ? (
        <section className="card card-flush">
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Criterion</th>
                  <th>Method &amp; Policy</th>
                  <th>AI Decision</th>
                  <th>Confidence</th>
                  <th>Evidence Summary</th>
                  <th>Governance Actions</th>
                </tr>
              </thead>
              <tbody>
                {ticket.results.map((r) => {
                  const finding = findingByCriterion[r.criterion]
                  return (
                    <tr key={r.resultId}>
                      <td>
                        <strong>{r.criterion}</strong>
                        <span className="cell-sub">{r.requirement}</span>
                      </td>
                      <td>
                        <span className="badge neutral">
                          {r.method === 'deterministic' ? 'Rules Engine' : 'AI Reasoning'}
                        </span>
                        <span className="cell-sub mono">{r.policyRef}</span>
                      </td>
                      <td>
                        <DecisionBadge status={r.status} />
                        {finding && finding.status !== 'Open' ? (
                          <span className="cell-sub">Human: {finding.status}</span>
                        ) : null}
                      </td>
                      <td><ConfidenceBadge confidence={r.confidence} tier={r.confidenceTier} /></td>
                      <td style={{ maxWidth: 340 }}>
                        <div style={{ fontSize: 13 }}>{r.reason}</div>
                        <span className="cell-sub">Source: {r.source}</span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                          <button
                            type="button"
                            className="btn btn-subtle btn-sm"
                            onClick={() => setExplainResult(r)}
                          >
                            Explain
                          </button>
                          {finding ? (
                            <>
                              <button
                                type="button"
                                className="btn btn-secondary btn-sm"
                                onClick={() => setOverrideTarget({ finding, mode: 'APPROVE_FINDING' })}
                              >
                                Approve
                              </button>
                              <button
                                type="button"
                                className="btn btn-secondary btn-sm"
                                onClick={() => setOverrideTarget({ finding, mode: 'OVERRIDE_PASS' })}
                              >
                                Override
                              </button>
                              <button
                                type="button"
                                className="btn btn-secondary btn-sm"
                                onClick={() => setOverrideTarget({ finding, mode: 'REQUEST_EVIDENCE' })}
                              >
                                Request Evidence
                              </button>
                            </>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {/* TAB 2: AI EVIDENCE VIEWER (PROPOSAL SECTION 12) */}
      {tab === 'evidence' ? (
        <div className="evidence-split">
          <section className="card">
            <div className="card-header">
              <div>
                <h3>Ticket Source Record (Work Notes, Approvals &amp; Attachments)</h3>
                <p className="card-subtitle">Click any AI Highlight tag on the right to spotlight its exact origin.</p>
              </div>
            </div>

            <div className="stack-sm">
              <div className="explain-row-label">Timestamped Work Notes</div>
              {ticket.workNotes.length === 0 ? (
                <div className="empty-state">No work notes logged yet.</div>
              ) : (
                ticket.workNotes.map((n, idx) => {
                  const noteHighlights = ticket.highlights.filter(
                    (h) => h.sourceType === 'work_note' && h.sourceIndex === idx,
                  )
                  const isFocused =
                    activeHighlight?.sourceType === 'work_note' &&
                    activeHighlight?.sourceIndex === idx
                  return (
                    <div
                      key={`${n.timestamp}-${idx}`}
                      className={`work-note-item ${isFocused ? 'active-highlight' : ''}`}
                    >
                      <div className="work-note-meta">
                        <strong className="mono">{n.timestamp}</strong>
                        <span>{n.author}</span>
                      </div>
                      <div style={{ fontSize: 13.5 }}>{renderHighlightedText(n.text, noteHighlights)}</div>
                    </div>
                  )
                })
              )}

              <div className="explain-row-label" style={{ marginTop: 10 }}>Approval Records</div>
              {ticket.approvals.length === 0 ? (
                <div className="explain-row">No approval records present on this ticket.</div>
              ) : (
                ticket.approvals.map((a, idx) => {
                  const isFocused =
                    activeHighlight?.sourceType === 'approval' &&
                    activeHighlight?.sourceIndex === idx
                  return (
                    <div key={`${a.approver}-${idx}`} className={`work-note-item ${isFocused ? 'active-highlight' : ''}`}>
                      <div className="work-note-meta">
                        <strong>{a.type} Approval — {a.approver}</strong>
                        <DecisionBadge status={a.status === 'Approved' ? 'PASS' : 'FAIL'} />
                      </div>
                      <div style={{ fontSize: 13 }}>{a.note || 'Recorded in ITSM approval log.'}</div>
                    </div>
                  )
                })
              )}

              {ticket.attachments.length > 0 ? (
                <>
                  <div className="explain-row-label" style={{ marginTop: 10 }}>Attachments &amp; Plans</div>
                  {ticket.attachments.map((att, idx) => {
                    const isFocused =
                      activeHighlight?.sourceType === 'attachment' &&
                      activeHighlight?.sourceIndex === idx
                    return (
                      <div key={`${att.name}-${idx}`} className={`work-note-item ${isFocused ? 'active-highlight' : ''}`}>
                        <div className="work-note-meta">
                          <strong>{att.name}</strong>
                          <span className="mono">{att.section}</span>
                        </div>
                        <div style={{ fontSize: 13 }}>{att.content_summary}</div>
                      </div>
                    )
                  })}
                </>
              ) : null}
            </div>
          </section>

          <section className="card">
            <div className="card-header">
              <div>
                <h3>AI Highlight Mapping</h3>
                <p className="card-subtitle">Extracted evidence spans linked to governance criteria.</p>
              </div>
            </div>
            <div className="stack-sm">
              {ticket.highlights.length === 0 ? (
                <div className="empty-state">No highlight spans extracted yet.</div>
              ) : (
                ticket.highlights.map((h, idx) => (
                  <button
                    key={`${h.sourceLabel}-${idx}`}
                    type="button"
                    className={`highlight-map-btn ${activeHighlightIdx === idx ? 'selected' : ''}`}
                    onClick={() => setActiveHighlightIdx(idx)}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                      <strong style={{ fontSize: 13 }}>→ {h.evidenceLabel}</strong>
                      <DecisionBadge status={h.status} />
                    </div>
                    <div style={{ fontSize: 12.5, color: 'var(--text-secondary)' }}>
                      &ldquo;{h.quote}&rdquo;
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)' }}>
                      <span className="mono">{h.sourceLabel}</span>
                      <span className="mono">{h.confidence}% confidence</span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </section>
        </div>
      ) : null}

      {/* TAB 3: TICKET METADATA & LIVE REMEDIATION */}
      {tab === 'remediate' ? (
        <div className="grid-2">
          <section className="card">
            <div className="card-header">
              <div>
                <h3>ITSM Ticket Record</h3>
                <p className="card-subtitle">Normalized by Agent 1 (Ticket Intelligence Agent).</p>
              </div>
            </div>
            <div className="grid-2" style={{ gap: 10 }}>
              {[
                ['Ticket ID', ticket.id],
                ['Type', ticket.type],
                ['Priority', ticket.priority],
                ['Category', ticket.category],
                ['Business Unit', ticket.businessUnit],
                ['Assignment Group', ticket.assignmentGroup],
                ['Requester', ticket.requester],
                ['Owner', ticket.owner],
                ['State', ticket.state],
                ['SLA Status', ticket.sla],
                ['Target Window', ticket.targetWindow || '—'],
                ['Closure Code', ticket.closureCode || 'Not Closed'],
              ].map(([k, v]) => (
                <div className="explain-row" key={k}>
                  <div className="explain-row-label">{k}</div>
                  <strong style={{ fontSize: 13 }}>{v}</strong>
                </div>
              ))}
            </div>
            <div className="explain-row" style={{ marginTop: 12 }}>
              <div className="explain-row-label">Full Description</div>
              <p style={{ fontSize: 13 }}>{ticket.description || ticket.shortDescription}</p>
            </div>
          </section>

          <section className="card">
            <div className="card-header">
              <div>
                <h3>Live Remediation &amp; Evidence Upload</h3>
                <p className="card-subtitle">
                  Simulate operational updates and watch all 6 AI agents re-evaluate risk in real time.
                </p>
              </div>
            </div>

            <div className="stack-sm">
              <div>
                <label className="field-label" htmlFor="rem-approver">Approver Name (for Approval uploads)</label>
                <input
                  id="rem-approver"
                  className="input"
                  value={approverName}
                  onChange={(e) => setApproverName(e.target.value)}
                />
              </div>

              <div>
                <label className="field-label" htmlFor="rem-note">Evidence Note / Details (optional)</label>
                <textarea
                  id="rem-note"
                  className="textarea"
                  placeholder="Enter custom evidence, rollback runbook summary, or root cause note…"
                  value={customNote}
                  onChange={(e) => setCustomNote(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 4 }}>
                <button type="button" className="btn btn-primary btn-sm" disabled={busy} onClick={() => handleRemediate('business_approval')}>
                  + Upload Business Approval
                </button>
                <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={() => handleRemediate('rollback_plan')}>
                  + Attach Verified Rollback Plan
                </button>
                <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={() => handleRemediate('post_validation')}>
                  + Record Post-Impl Validation
                </button>
                <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={() => handleRemediate('root_cause')}>
                  + Add Root Cause Analysis
                </button>
                <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={() => handleRemediate('customer_communication')}>
                  + Log Customer Confirmation
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  disabled={busy || !customNote.trim()}
                  onClick={() => handleRemediate('work_note')}
                >
                  + Append Work Note
                </button>
                {ticket.state !== 'Closed' ? (
                  <button type="button" className="btn btn-success btn-sm" disabled={busy} onClick={() => handleRemediate('close_ticket')}>
                    Close Ticket &amp; Finalize Audit
                  </button>
                ) : null}
              </div>
            </div>
          </section>
        </div>
      ) : null}

      {/* TAB 4: MULTI-AGENT EXECUTION TRACE */}
      {tab === 'trace' ? (
        <section className="card">
          <div className="card-header">
            <div>
              <h3>Multi-Agent Orchestration Pipeline Trace</h3>
              <p className="card-subtitle">
                Proposal Section 21 — step-by-step telemetry across Agents 1 to 6 during the last evaluation ({ticket.lastEvaluated.replace('T', ' ').slice(0, 19)} UTC).
              </p>
            </div>
          </div>
          <div className="trace-grid">
            {ticket.agentTrace.map((step) => (
              <div key={step.agentNumber} className="trace-step">
                <div className="trace-step-head">
                  <span className="badge brand">Agent {step.agentNumber}</span>
                  <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {step.durationMs} ms
                  </span>
                </div>
                <strong style={{ fontSize: 14, marginTop: 2 }}>{step.agentName}</strong>
                <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>{step.phase}</span>
                <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 4 }}>{step.summary}</p>
                <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 'auto', paddingTop: 6 }}>
                  {step.model}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {/* TAB 5: IMMUTABLE GOVERNANCE AUDIT TRAIL (SECTION 22) */}
      {tab === 'trail' ? (
        <section className="card card-flush">
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
            <h3>Immutable Governance Audit Trail</h3>
            <p className="card-subtitle">
              Proposal Section 22 — every AI evaluation and human override records Who, What, When, Rule, Evidence, AI Model, Confidence, and Decision.
            </p>
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>When (UTC)</th>
                  <th>Who &amp; Role</th>
                  <th>Action &amp; Evidence</th>
                  <th>Rule / Policy</th>
                  <th>AI Model</th>
                  <th>Confidence</th>
                  <th>Decision</th>
                </tr>
              </thead>
              <tbody>
                {ticket.auditTrail.map((tr) => (
                  <tr key={tr.trailId}>
                    <td className="mono" style={{ fontSize: 12 }}>{tr.timestamp.replace('T', ' ').slice(0, 19)}</td>
                    <td>
                      <strong>{tr.who}</strong>
                      <span className="cell-sub">{tr.role}</span>
                    </td>
                    <td style={{ maxWidth: 320 }}>
                      <div>{tr.what}</div>
                      {tr.evidence ? <span className="cell-sub">{tr.evidence}</span> : null}
                    </td>
                    <td className="mono" style={{ fontSize: 12 }}>{tr.rule}</td>
                    <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{tr.aiModel}</td>
                    <td className="mono">{Math.round(tr.confidence)}%</td>
                    <td>
                      <DecisionBadge status={tr.decision || 'LOGGED'} />
                      {tr.humanOverride ? <span className="cell-sub" style={{ color: 'var(--review)', fontWeight: 600 }}>Human Override</span> : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {/* Explainable AI Modal */}
      <ExplainModal
        ticketId={ticket.id}
        result={explainResult}
        onClose={() => setExplainResult(null)}
        onOpenPolicy={onOpenPolicySearch}
      />

      {/* Human-in-the-Loop Override / Approve / Request Evidence Modal */}
      <OverrideModal
        ticketId={ticket.id}
        finding={overrideTarget?.finding || null}
        initialMode={overrideTarget?.mode || 'APPROVE_FINDING'}
        profile={profile}
        onClose={() => setOverrideTarget(null)}
        onSubmit={async (payload) => {
          if (!overrideTarget) return
          const res = await api.findingAction(ticket.id, overrideTarget.finding.findingId, payload)
          onTicketUpdated(res.ticket, res.message)
        }}
      />
    </div>
  )
}
