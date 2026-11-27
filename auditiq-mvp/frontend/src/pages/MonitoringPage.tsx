import React, { useState } from 'react'
import type { MonitoringResponse } from '../types/auditiq'
import { api } from '../api/client'
import { RiskBadge, TypeChip } from '../components/Badges'

interface MonitoringPageProps {
  data: MonitoringResponse | null
  wsConnected: boolean
  onOpenTicket: (ticketId: string) => void
  onRefresh: () => Promise<void>
  onNotify: (msg: string, isError?: boolean) => void
  onOpenIngest: () => void
}

export function MonitoringPage({
  data,
  wsConnected,
  onOpenTicket,
  onRefresh,
  onNotify,
  onOpenIngest,
}: MonitoringPageProps) {
  const [simulating, setSimulating] = useState(false)
  const [busyAlert, setBusyAlert] = useState<string | null>(null)

  if (!data) {
    return <div className="empty-state">Loading Live Audit Monitor…</div>
  }

  async function handleSimulate() {
    setSimulating(true)
    try {
      const res = await api.simulateLiveEvent()
      await onRefresh()
      onNotify(res.message)
    } catch (err) {
      onNotify(err instanceof Error ? err.message : 'Simulation failed.', true)
    } finally {
      setSimulating(false)
    }
  }

  async function handleAlertAction(alertId: string, status: 'Acknowledged' | 'Resolved') {
    setBusyAlert(alertId)
    try {
      const res = await api.updateAlertStatus(alertId, status)
      await onRefresh()
      onNotify(res.message)
    } catch (err) {
      onNotify(err instanceof Error ? err.message : 'Failed to update alert.', true)
    } finally {
      setBusyAlert(null)
    }
  }

  return (
    <div className="stack-md">
      <section className="executive-strip">
        <div>
          <h2>Real-Time Continuous Monitoring &amp; Predictive Audit</h2>
          <p>
            Agent 6 continuously monitors active INC, SR, and CR tickets before implementation or
            closure so operations teams remediate missing approvals and rollback gaps before they
            become audit findings.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <span className={`badge ${wsConnected ? 'pass' : 'review'}`}>
            <span className={`dot ${wsConnected ? 'live' : 'offline'}`} />
            {wsConnected ? 'WebSocket Live Stream' : 'Polling Fallback'}
          </span>
          <button type="button" className="btn btn-primary" disabled={simulating} onClick={handleSimulate}>
            {simulating ? 'Simulating ITSM Event…' : 'Simulate Live Change Event'}
          </button>
          <button type="button" className="btn btn-secondary" onClick={onOpenIngest}>
            + Create Active Ticket
          </button>
        </div>
      </section>

      <section className="grid-kpi-4" aria-label="Active Tickets by Risk">
        <div className="kpi-card">
          <span className="kpi-label">Active Tickets Monitored</span>
          <span className="kpi-value">{data.activeTicketCount}</span>
          <span className="kpi-meta">Scheduled · Pending · In Progress</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Critical Active Risk</span>
          <span className={`kpi-value ${data.riskSummary.CRITICAL > 0 ? 'warn' : 'good'}`}>
            {data.riskSummary.CRITICAL}
          </span>
          <span className="kpi-meta">Immediate pre-closure escalation</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">High Active Risk</span>
          <span className={`kpi-value ${data.riskSummary.HIGH > 0 ? 'warn' : 'good'}`}>
            {data.riskSummary.HIGH}
          </span>
          <span className="kpi-meta">Owner alert issued</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Alerts Remediated</span>
          <span className="kpi-value good">{data.resolvedAlertsCount}</span>
          <span className="kpi-meta">Prevented before closure</span>
        </div>
      </section>

      <div className="grid-asymmetric">
        <section className="card">
          <div className="card-header">
            <div>
              <h3>Live Compliance Alerts</h3>
              <p className="card-subtitle">Proactive warnings triggered by Continuous Monitoring Agent.</p>
            </div>
            <span className="badge fail">{data.alerts.length} Open</span>
          </div>

          {data.alerts.length === 0 ? (
            <div className="empty-state">No open compliance alerts. Use &ldquo;Simulate Live Change Event&rdquo; to test real-time detection.</div>
          ) : (
            <div className="stack-sm">
              {data.alerts.map((al) => {
                const aid = al.alertId || al.alert_id || ''
                const tid = al.ticketId || al.ticket_id || ''
                return (
                  <div key={aid} className="explain-row" style={{ background: 'var(--bg-surface)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <TypeChip type={al.ticketType || 'CR'} />
                        <button type="button" className="btn-link mono" onClick={() => onOpenTicket(tid)}>
                          {tid}
                        </button>
                        <RiskBadge band={al.severity} />
                        <span className="badge neutral">{al.status}</span>
                      </div>
                      <span className="mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        Predicted Risk: <strong>{Math.round(al.predictedRisk || 0)}%</strong>
                      </span>
                    </div>

                    <div style={{ marginTop: 8, fontWeight: 600 }}>{al.title}</div>
                    <p style={{ marginTop: 3, fontSize: 13, color: 'var(--text-secondary)' }}>{al.message}</p>
                    <p style={{ marginTop: 6, fontSize: 12, color: 'var(--brand-ink)', fontWeight: 500 }}>
                      Recommendation: {al.recommendation}
                    </p>

                    <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
                      <button type="button" className="btn btn-primary btn-sm" onClick={() => onOpenTicket(tid)}>
                        Inspect &amp; Remediate →
                      </button>
                      {al.status === 'Active' ? (
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          disabled={busyAlert === aid}
                          onClick={() => handleAlertAction(aid, 'Acknowledged')}
                        >
                          Acknowledge
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        disabled={busyAlert === aid}
                        onClick={() => handleAlertAction(aid, 'Resolved')}
                      >
                        Dismiss / Mark Resolved
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </section>

        <section className="card">
          <div className="card-header">
            <div>
              <h3>Predictive Audit Risk (Pre-Closure)</h3>
              <p className="card-subtitle">Proposal Section 15 — tickets most likely to fail audit if closed as-is.</p>
            </div>
          </div>

          <div className="stack-sm">
            {data.predictiveAudits.map((p) => (
              <div
                key={p.ticketId}
                className="alert-row-clickable"
                onClick={() => onOpenTicket(p.ticketId)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') onOpenTicket(p.ticketId)
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <TypeChip type={p.ticketType} />
                    <strong className="mono">{p.ticketId}</strong>
                    <RiskBadge band={p.riskBand} />
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span className="mono" style={{ fontSize: 17, fontWeight: 700, color: p.predictedAuditRisk >= 70 ? 'var(--fail)' : 'var(--review)' }}>
                      {Math.round(p.predictedAuditRisk)}%
                    </span>
                    <span className="cell-sub">Predicted Failure</span>
                  </div>
                </div>
                <div style={{ fontSize: 13, fontWeight: 600, marginTop: 6 }}>{p.shortDescription}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                  {p.assignmentGroup} · {p.state} · Window: {p.targetWindow || 'Active'}
                </div>
                {p.factors.length > 0 ? (
                  <ul style={{ margin: '8px 0 0 18px', padding: 0, fontSize: 12, color: 'var(--text-secondary)' }}>
                    {p.factors.map((f) => (
                      <li key={f}>{f}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ))}
          </div>
        </section>
      </div>

      {data.recentEvents.length > 0 ? (
        <section className="card">
          <div className="card-header">
            <div>
              <h3>Live Event Stream Log</h3>
              <p className="card-subtitle">Real-time WebSocket audit orchestration events broadcast to connected monitors.</p>
            </div>
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Event Type</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {[...data.recentEvents].reverse().slice(0, 8).map((ev, idx) => (
                  <tr key={`${ev.timestamp}-${idx}`}>
                    <td className="mono" style={{ fontSize: 12 }}>{ev.timestamp.replace('T', ' ').slice(0, 19)} UTC</td>
                    <td><span className="badge brand">{ev.event}</span></td>
                    <td className="mono" style={{ fontSize: 12 }}>
                      {ev.payload ? JSON.stringify(ev.payload) : 'Connected'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </div>
  )
}
