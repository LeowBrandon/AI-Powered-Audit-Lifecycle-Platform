import React from 'react'
import type { DashboardResponse, PageId } from '../types/auditiq'
import { RiskBadge, TypeChip } from '../components/Badges'
import { ComplianceTrendChart } from '../components/Charts'

interface DashboardPageProps {
  data: DashboardResponse | null
  onOpenTicket: (ticketId: string) => void
  onNavigate: (page: PageId, riskFilter?: string) => void
  onOpenIngest: () => void
}

export function DashboardPage({
  data,
  onOpenTicket,
  onNavigate,
  onOpenIngest,
}: DashboardPageProps) {
  if (!data) {
    return <div className="empty-state">Loading Executive Dashboard…</div>
  }

  const dist = data.riskDistribution
  const totalRisk = Math.max(1, dist.CRITICAL + dist.HIGH + dist.MEDIUM + dist.LOW)

  return (
    <div className="stack-md">
      <section className="executive-strip">
        <div>
          <h2>From Manual Ticket Audits to Continuous Audit Intelligence</h2>
          <p>
            AuditIQ orchestrates 9 specialized AI agents with deterministic enterprise rules to
            extract evidence, detect pre-closure compliance risk, and keep auditors firmly in control
            of governance decisions.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => onOpenTicket('CR001992')}
          >
            Launch CR001992 E2E Demo →
          </button>
          <button type="button" className="btn btn-secondary" onClick={onOpenIngest}>
            + Ingest Tickets
          </button>
        </div>
      </section>

      <section className="grid-kpi-6" aria-label="Executive Audit KPIs">
        <div className="kpi-card">
          <span className="kpi-label">Tickets Audited</span>
          <span className="kpi-value">{data.total}</span>
          <span className="kpi-meta">Simulated INC · SR · CR</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Compliance Rate</span>
          <span className={`kpi-value ${data.compliance >= 90 ? 'good' : ''}`}>
            {data.compliance}%
          </span>
          <span className="kpi-meta">
            {data.trendDelta >= 0 ? `↑ +${data.trendDelta}%` : `↓ ${data.trendDelta}%`} over 6 months
          </span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">High &amp; Critical Risk</span>
          <span className={`kpi-value ${data.highRisk > 0 ? 'warn' : 'good'}`}>
            {data.highRisk}
          </span>
          <span className="kpi-meta">Mandatory audit / escalation</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Active AI Alerts</span>
          <span className={`kpi-value ${data.aiAlerts > 0 ? 'warn' : 'good'}`}>
            {data.aiAlerts}
          </span>
          <span className="kpi-meta">Pre-closure signals</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Avg Audit Time</span>
          <span className="kpi-value">{data.avgAuditTime}m</span>
          <span className="kpi-meta">Target &lt;5–10m (was 20–30m)</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Auto-Audited</span>
          <span className="kpi-value">{data.autoAudited}%</span>
          <span className="kpi-meta">Target 70–90% low-risk auto</span>
        </div>
      </section>

      <section className="insight-callout" aria-label="Agent 9 Management Insight">
        <span className="insight-callout-title">Agent 9 · Management Insight Narrative</span>
        <p>{data.managementInsight.narrative}</p>
        <div className="insight-chips">
          <span>
            <strong>Top Risk Area:</strong> {data.managementInsight.topRiskArea}
          </span>
          <span>
            <strong>Top Root Cause:</strong> {data.managementInsight.topRootCause}
          </span>
          <span>
            <strong>Approval Gaps:</strong> {data.managementInsight.approvalViolations}
          </span>
          <span>
            <strong>SLA Issues:</strong> {data.managementInsight.slaViolations}
          </span>
          <span>
            <strong>Documentation Gaps:</strong> {data.managementInsight.documentationIssues}
          </span>
        </div>
      </section>

      <div className="grid-asymmetric">
        <section className="card">
          <div className="card-header">
            <div>
              <h3>Compliance Trend (6-Month Window)</h3>
              <p className="card-subtitle">Hover points to inspect monthly compliance score and ticket volume.</p>
            </div>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => onNavigate('analytics')}>
              Full Analytics →
            </button>
          </div>
          <ComplianceTrendChart data={data.trend} />
        </section>

        <section className="card">
          <div className="card-header">
            <div>
              <h3>Risk Distribution</h3>
              <p className="card-subtitle">Click any risk tier to open filtered Audit Queue.</p>
            </div>
          </div>
          <div className="stack-sm">
            {(
              [
                ['CRITICAL', dist.CRITICAL, 'critical', 'Immediate Escalation'],
                ['HIGH', dist.HIGH, 'fail', 'Mandatory Human Audit'],
                ['MEDIUM', dist.MEDIUM, 'review', 'Dynamic Sampled Review'],
                ['LOW', dist.LOW, 'pass', 'Automated AI Audit'],
              ] as const
            ).map(([band, count, tone, route]) => {
              const pct = Math.round((count / totalRisk) * 100)
              return (
                <button
                  key={band}
                  type="button"
                  className="alert-row-clickable"
                  style={{ width: '100%', textAlign: 'left' }}
                  onClick={() => onNavigate('queue', band)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <RiskBadge band={band} />
                      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{route}</span>
                    </div>
                    <strong className="mono">{count} ({pct}%)</strong>
                  </div>
                  <div className="bar-track">
                    <div className={`bar-fill ${tone}`} style={{ width: `${Math.max(2, pct)}%` }} />
                  </div>
                </button>
              )
            })}
          </div>
        </section>
      </div>

      <div className="grid-2">
        <section className="card">
          <div className="card-header">
            <div>
              <h3>Live Proactive AI Alerts</h3>
              <p className="card-subtitle">Issues surfaced by Agent 6 before ticket closure or production execution.</p>
            </div>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => onNavigate('monitoring')}>
              Open Live Monitor →
            </button>
          </div>
          {data.recentAlerts.length === 0 ? (
            <div className="empty-state">All proactive governance alerts have been resolved.</div>
          ) : (
            <div className="stack-sm">
              {data.recentAlerts.map((al) => {
                const tid = al.ticketId || al.ticket_id || ''
                const ttype = al.ticketType || al.ticket_type || 'CR'
                const pred = al.predictedRisk ?? al.predicted_risk ?? 0
                return (
                  <div
                    key={al.alertId || al.alert_id || tid}
                    className="alert-row-clickable"
                    onClick={() => onOpenTicket(tid)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') onOpenTicket(tid)
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <TypeChip type={ttype} />
                        <strong className="mono">{tid}</strong>
                        <RiskBadge band={al.severity} />
                      </div>
                      <span className="mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        {Math.round(pred)}% risk
                      </span>
                    </div>
                    <p style={{ marginTop: 6, fontSize: 13, fontWeight: 500 }}>{al.title}</p>
                    <p style={{ marginTop: 2, fontSize: 12, color: 'var(--text-muted)' }}>{al.recommendation}</p>
                  </div>
                )
              })}
            </div>
          )}
        </section>

        <section className="card">
          <div className="card-header">
            <div>
              <h3>Continuous Assurance Modes &amp; Transformation</h3>
              <p className="card-subtitle">Proposal positioning: Prevent, Audit, and Improve under human oversight.</p>
            </div>
          </div>

          <div className="mode-row" style={{ marginBottom: 16 }}>
            <div className="mode-tile">
              <span className="mode-tile-num">01 · Prevent</span>
              <h4>Real-Time Warnings</h4>
              <p>Detect missing approvals, rollback gaps, and SLA risk before closure.</p>
            </div>
            <div className="mode-tile">
              <span className="mode-tile-num">02 · Audit</span>
              <h4>Rules + AI Reasoning</h4>
              <p>Automate evidence extraction and Three-Way PASS/FAIL/REVIEW scoring.</p>
            </div>
            <div className="mode-tile">
              <span className="mode-tile-num">03 · Improve</span>
              <h4>Closed-Loop Insights</h4>
              <p>Feed QC findings and auditor overrides back into rules and operations.</p>
            </div>
          </div>

          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Traditional Manual Audit</th>
                  <th>AuditIQ Continuous Governance</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Closed-ticket retrospective review</td>
                  <td><strong>Continuous pre-closure monitoring</strong></td>
                </tr>
                <tr>
                  <td>Separate Audit &amp; QC silos</td>
                  <td><strong>Integrated lifecycle + QC intelligence</strong></td>
                </tr>
                <tr>
                  <td>Manual evidence collection</td>
                  <td><strong>Automated extraction &amp; AI Evidence Viewer</strong></td>
                </tr>
                <tr>
                  <td>Predefined random sampling</td>
                  <td><strong>Dynamic 4-tier risk-based sampling</strong></td>
                </tr>
                <tr>
                  <td>Static spreadsheets &amp; limited reasoning</td>
                  <td><strong>Explainable AI + real-time analytics</strong></td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  )
}
