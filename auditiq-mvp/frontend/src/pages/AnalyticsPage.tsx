import React from 'react'
import type { AnalyticsResponse } from '../types/auditiq'
import { ComplianceTrendChart, HorizontalBarList } from '../components/Charts'

export function AnalyticsPage({ data }: { data: AnalyticsResponse | null }) {
  if (!data) {
    return <div className="empty-state">Loading Analytics &amp; Management Insights…</div>
  }

  return (
    <div className="stack-md">
      <div>
        <h2 style={{ fontSize: 20 }}>Analytics, Compliance Trends &amp; Management Insights</h2>
        <p className="card-subtitle">
          Agent 9 converts live audit outcomes into operational governance intelligence by ticket type, department, business unit, and recurring failure root cause.
        </p>
      </div>

      <section className="insight-callout">
        <span className="insight-callout-title">Executive Intelligence Summary (Simulated Demo Data)</span>
        <p>{data.summary.narrative}</p>
        <div className="insight-chips">
          <span><strong>Tickets Audited:</strong> {data.summary.ticketsAudited}</span>
          <span><strong>Compliance Rate:</strong> {data.summary.complianceRate}%</span>
          <span><strong>High/Critical Risk:</strong> {data.summary.highRiskTickets}</span>
          <span><strong>Top Risk Area:</strong> {data.summary.topRiskArea}</span>
          <span><strong>Top Root Cause:</strong> {data.summary.topRootCause}</span>
        </div>
      </section>

      <div className="grid-2">
        <section className="card">
          <div className="card-header">
            <div>
              <h3>Monthly Compliance Trend</h3>
              <p className="card-subtitle">
                Trajectory across seeded 6-month reporting period ({data.summary.trendDelta >= 0 ? `+${data.summary.trendDelta}%` : `${data.summary.trendDelta}%`}).
              </p>
            </div>
          </div>
          <ComplianceTrendChart data={data.trend} />
        </section>

        <section className="card">
          <div className="card-header">
            <div>
              <h3>Top Audit Failure Categories</h3>
              <p className="card-subtitle">Share of active findings by recurring compliance gap.</p>
            </div>
          </div>
          <HorizontalBarList
            items={data.failureCategories.map((f) => ({
              label: f.label,
              value: f.value,
              sub: `${f.count} findings`,
            }))}
            maxValue={Math.max(40, ...data.failureCategories.map((f) => f.value))}
            toneFn={(v) => (v >= 28 ? 'fail' : v >= 16 ? 'review' : '')}
          />
        </section>
      </div>

      <div className="grid-3">
        <section className="card">
          <div className="card-header">
            <div>
              <h3>Compliance by Ticket Type</h3>
              <p className="card-subtitle">INC vs. SR vs. CR governance posture.</p>
            </div>
          </div>
          <HorizontalBarList
            items={data.ticketType.map((x) => ({
              label: `${x.label} Tickets`,
              value: x.value,
              sub: `${x.count} audited`,
            }))}
            toneFn={(v) => (v >= 92 ? 'pass' : v >= 85 ? 'review' : 'fail')}
          />
        </section>

        <section className="card">
          <div className="card-header">
            <div>
              <h3>Compliance by Department</h3>
              <p className="card-subtitle">Assignment group performance ranked lowest-first.</p>
            </div>
          </div>
          <HorizontalBarList
            items={data.department.map((x) => ({
              label: x.label,
              value: x.value,
              sub: `${x.count} tickets · ${x.highRisk} high-risk`,
            }))}
            toneFn={(v) => (v >= 92 ? 'pass' : v >= 85 ? 'review' : 'fail')}
          />
        </section>

        <section className="card">
          <div className="card-header">
            <div>
              <h3>Compliance by Business Unit</h3>
              <p className="card-subtitle">Enterprise portfolio governance visibility.</p>
            </div>
          </div>
          <HorizontalBarList
            items={data.businessUnit.map((x) => ({
              label: x.label,
              value: x.value,
              sub: `${x.count} tickets`,
            }))}
            toneFn={(v) => (v >= 92 ? 'pass' : v >= 85 ? 'review' : 'fail')}
          />
        </section>
      </div>

      {/* Proposal Section 25 Target KPIs */}
      <section className="card card-flush">
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
          <h3>Business Impact &amp; Target KPIs (Proposal Section 25)</h3>
          <p className="card-subtitle">
            Presented transparently as proposal target KPIs alongside current simulated demo dataset figures — not production claims.
          </p>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>KPI Category</th>
                <th>Metric</th>
                <th>Before (Manual Audit)</th>
                <th>Proposal Target KPI</th>
                <th>Current Demo Dataset</th>
              </tr>
            </thead>
            <tbody>
              {data.targetKpis.map((kpi) => (
                <tr key={kpi.metric}>
                  <td><span className="badge brand">{kpi.category}</span></td>
                  <td><strong>{kpi.metric}</strong></td>
                  <td style={{ color: 'var(--text-muted)' }}>{kpi.before}</td>
                  <td><strong>{kpi.target}</strong></td>
                  <td className="mono">{kpi.demoCurrent}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
