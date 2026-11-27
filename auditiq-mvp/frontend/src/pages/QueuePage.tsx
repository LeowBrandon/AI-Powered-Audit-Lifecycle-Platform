import React, { useEffect, useState } from 'react'
import { api, type QueueFilterParams } from '../api/client'
import type { QueueResponse } from '../types/auditiq'
import { ConfidenceBadge, DecisionBadge, RiskBadge, TypeChip } from '../components/Badges'

interface QueuePageProps {
  initialRiskFilter?: string
  onOpenTicket: (ticketId: string) => void
  onOpenIngest: () => void
  onNotify: (msg: string, isError?: boolean) => void
  refreshSignal: number
}

export function QueuePage({
  initialRiskFilter,
  onOpenTicket,
  onOpenIngest,
  onNotify,
  refreshSignal,
}: QueuePageProps) {
  const [filters, setFilters] = useState<QueueFilterParams>({
    ticket_type: 'ALL',
    risk: initialRiskFilter || 'ALL',
    business_unit: 'ALL',
    assignment_group: 'ALL',
    auditor: 'ALL',
    audit_status: 'ALL',
    violation_type: 'ALL',
    confidence_tier: 'ALL',
    date_from: '',
    date_to: '',
    search: '',
    only_attention: false,
  })
  const [data, setData] = useState<QueueResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [batchBusy, setBatchBusy] = useState(false)

  useEffect(() => {
    if (initialRiskFilter) {
      setFilters((prev) => ({ ...prev, risk: initialRiskFilter }))
    }
  }, [initialRiskFilter])

  useEffect(() => {
    let active = true
    setLoading(true)
    api
      .tickets(filters)
      .then((res) => {
        if (active) setData(res)
      })
      .catch((err) => onNotify(err instanceof Error ? err.message : 'Failed to load queue.', true))
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [filters, refreshSignal])

  function resetFilters() {
    setFilters({
      ticket_type: 'ALL',
      risk: 'ALL',
      business_unit: 'ALL',
      assignment_group: 'ALL',
      auditor: 'ALL',
      audit_status: 'ALL',
      violation_type: 'ALL',
      confidence_tier: 'ALL',
      date_from: '',
      date_to: '',
      search: '',
      only_attention: false,
    })
  }

  async function handleBatchAudit() {
    setBatchBusy(true)
    try {
      const res = await api.batchAuditAll()
      onNotify(res.message)
      const refreshed = await api.tickets(filters)
      setData(refreshed)
    } catch (err) {
      onNotify(err instanceof Error ? err.message : 'Batch audit failed.', true)
    } finally {
      setBatchBusy(false)
    }
  }

  return (
    <div className="stack-md">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
        <div>
          <h2 style={{ fontSize: 20 }}>Human-in-the-Loop Audit Queue</h2>
          <p className="card-subtitle">
            Risk-prioritized worklist across INC, SR, and CR tickets with all 9 governance filters and auditor workload visibility.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-secondary" disabled={batchBusy} onClick={handleBatchAudit}>
            {batchBusy ? 'Auditing Fleet…' : '↻ Re-Audit All Tickets'}
          </button>
          <button type="button" className="btn btn-primary" onClick={onOpenIngest}>
            + Ingest / Upload CSV
          </button>
        </div>
      </div>

      {/* Auditor Workload Strip (Proposal Screen 3) */}
      {data && data.workload.length > 0 ? (
        <section className="grid-kpi-4" aria-label="Auditor Workload">
          {data.workload.map((w) => (
            <button
              key={w.auditor}
              type="button"
              className="kpi-card"
              style={{
                textAlign: 'left',
                cursor: 'pointer',
                borderColor: filters.auditor === w.auditor ? 'var(--brand)' : undefined,
              }}
              onClick={() =>
                setFilters((f) => ({
                  ...f,
                  auditor: f.auditor === w.auditor ? 'ALL' : w.auditor,
                }))
              }
            >
              <span className="kpi-label">Auditor Workload · {w.auditor}</span>
              <span className="kpi-value">{w.pending} <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-muted)' }}>pending</span></span>
              <span className="kpi-meta">{w.total} assigned · {w.highRisk} high/critical</span>
            </button>
          ))}
        </section>
      ) : null}

      {/* Proposal Section 9 — All 9 Filters */}
      <section className="filter-panel" aria-label="Audit Queue Filters">
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            id="queue-search"
            className="input"
            style={{ maxWidth: 320 }}
            placeholder="Search ticket ID, summary, or group…"
            value={filters.search || ''}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          />
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 500, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={Boolean(filters.only_attention)}
              onChange={(e) => setFilters({ ...filters, only_attention: e.target.checked })}
            />
            Needs Human Attention Only
          </label>
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Showing {data?.total ?? 0} tickets
            </span>
            <button type="button" className="btn btn-secondary btn-sm" onClick={resetFilters}>
              Reset Filters
            </button>
          </div>
        </div>

        <div className="filter-grid">
          <select
            aria-label="Filter by Ticket Type"
            className="select"
            value={filters.ticket_type || 'ALL'}
            onChange={(e) => setFilters({ ...filters, ticket_type: e.target.value })}
          >
            <option value="ALL">All Ticket Types</option>
            <option value="CR">CR — Change Request</option>
            <option value="INC">INC — Incident</option>
            <option value="SR">SR — Service Request</option>
          </select>

          <select
            aria-label="Filter by Risk Band"
            className="select"
            value={filters.risk || 'ALL'}
            onChange={(e) => setFilters({ ...filters, risk: e.target.value })}
          >
            <option value="ALL">All Risk Bands</option>
            <option value="CRITICAL">Critical Risk</option>
            <option value="HIGH">High Risk</option>
            <option value="MEDIUM">Medium Risk</option>
            <option value="LOW">Low Risk</option>
          </select>

          <select
            aria-label="Filter by Business Unit"
            className="select"
            value={filters.business_unit || 'ALL'}
            onChange={(e) => setFilters({ ...filters, business_unit: e.target.value })}
          >
            <option value="ALL">All Business Units</option>
            {(data?.facets.businessUnits || []).map((bu) => (
              <option key={bu} value={bu}>{bu}</option>
            ))}
          </select>

          <select
            aria-label="Filter by Assignment Group"
            className="select"
            value={filters.assignment_group || 'ALL'}
            onChange={(e) => setFilters({ ...filters, assignment_group: e.target.value })}
          >
            <option value="ALL">All Assignment Groups</option>
            {(data?.facets.assignmentGroups || []).map((g) => (
              <option key={g} value={g}>{g}</option>
            ))}
          </select>

          <select
            aria-label="Filter by Auditor"
            className="select"
            value={filters.auditor || 'ALL'}
            onChange={(e) => setFilters({ ...filters, auditor: e.target.value })}
          >
            <option value="ALL">All Auditors</option>
            {(data?.facets.auditors || []).map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>

          <select
            aria-label="Filter by Audit Status"
            className="select"
            value={filters.audit_status || 'ALL'}
            onChange={(e) => setFilters({ ...filters, audit_status: e.target.value })}
          >
            <option value="ALL">All Audit Statuses</option>
            {(data?.facets.auditStatuses || []).map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          <select
            aria-label="Filter by Violation Type"
            className="select"
            value={filters.violation_type || 'ALL'}
            onChange={(e) => setFilters({ ...filters, violation_type: e.target.value })}
          >
            <option value="ALL">All Violation Types</option>
            {(data?.facets.violationTypes || []).map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>

          <select
            aria-label="Filter by AI Confidence Tier"
            className="select"
            value={filters.confidence_tier || 'ALL'}
            onChange={(e) => setFilters({ ...filters, confidence_tier: e.target.value })}
          >
            <option value="ALL">All AI Confidence Tiers</option>
            <option value="AUTO">95–100% (Auto Decision)</option>
            <option value="RECOMMEND">80–94% (AI Recommendation)</option>
            <option value="REVIEW">&lt;80% (Human Review)</option>
          </select>

          <input
            aria-label="Date From"
            type="date"
            className="input"
            value={filters.date_from || ''}
            onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
          />

          <input
            aria-label="Date To"
            type="date"
            className="input"
            value={filters.date_to || ''}
            onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
          />
        </div>
      </section>

      <section className="card card-flush">
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Type</th>
                <th>Summary &amp; Group</th>
                <th>Risk</th>
                <th>Score</th>
                <th>AI Confidence</th>
                <th>Sampling Action</th>
                <th>Audit Status</th>
                <th>Auditor</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && !data ? (
                <tr>
                  <td colSpan={10} className="empty-state">Loading audit queue…</td>
                </tr>
              ) : data && data.items.length === 0 ? (
                <tr>
                  <td colSpan={10} className="empty-state">No tickets match the selected filters.</td>
                </tr>
              ) : (
                (data?.items || []).map((t) => (
                  <tr key={t.id}>
                    <td>
                      <button type="button" className="btn-link mono" onClick={() => onOpenTicket(t.id)}>
                        {t.id}
                      </button>
                      <span className="cell-sub">{t.priority} · {t.state}</span>
                    </td>
                    <td><TypeChip type={t.type} /></td>
                    <td>
                      <strong>{t.shortDescription}</strong>
                      <span className="cell-sub">
                        {t.assignmentGroup} · {t.businessUnit}
                        {t.violations ? ` · Gaps: ${t.violations}` : ''}
                      </span>
                    </td>
                    <td><RiskBadge band={t.riskBand} score={t.risk} /></td>
                    <td className="mono" style={{ fontWeight: 700 }}>{t.compliance}%</td>
                    <td><ConfidenceBadge confidence={t.confidence} /></td>
                    <td><span className="badge neutral">{t.samplingTier}</span></td>
                    <td><DecisionBadge status={t.auditStatus} /></td>
                    <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{t.auditor}</td>
                    <td>
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => onOpenTicket(t.id)}>
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
