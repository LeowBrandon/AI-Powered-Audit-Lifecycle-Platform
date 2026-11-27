import React, { useState } from 'react'
import { api } from '../api/client'

interface IngestModalProps {
  open: boolean
  onClose: () => void
  onCompleted: (message: string, openTicketId?: string) => void
}

export function IngestModal({ open, onClose, onCompleted }: IngestModalProps) {
  const [mode, setMode] = useState<'create' | 'upload'>('create')
  const [ticketType, setTicketType] = useState<'CR' | 'INC' | 'SR'>('CR')
  const [shortDesc, setShortDesc] = useState('')
  const [priority, setPriority] = useState<'P1' | 'P2' | 'P3' | 'P4'>('P1')
  const [group, setGroup] = useState('Infrastructure')
  const [bu, setBu] = useState('Core Operations')
  const [state, setState] = useState<'Scheduled' | 'Pending Approval' | 'In Progress' | 'Closed'>('Scheduled')
  const [sla, setSla] = useState<'Within SLA' | 'At Risk' | 'Met' | 'Breached'>('At Risk')
  const [workNote, setWorkNote] = useState('')
  const [includeBizApproval, setIncludeBizApproval] = useState(false)
  const [includeTechApproval, setIncludeTechApproval] = useState(true)

  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  if (!open) return null

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (shortDesc.trim().length < 4) {
      setErr('Please provide a short ticket description.')
      return
    }
    setBusy(true)
    setErr('')
    try {
      const approvals = []
      if (includeTechApproval) {
        approvals.push({ type: 'Technical', approver: `${group} Principal`, status: 'Approved', note: 'Technical review completed.' })
      }
      if (includeBizApproval) {
        approvals.push({ type: 'Business', approver: `VP ${bu}`, status: 'Approved', note: 'Business owner approval granted.' })
      }
      const res = await api.createTicket({
        ticket_type: ticketType,
        short_description: shortDesc.trim(),
        description: shortDesc.trim(),
        priority,
        category: group === 'Network Operations' ? 'Network' : group === 'Service Desk' ? 'End User' : group,
        business_unit: bu,
        assignment_group: group,
        status: state,
        sla_status: sla,
        target_window: state === 'Closed' ? 'Closed' : 'Upcoming Window',
        work_notes: workNote.trim() ? [{ author: `${group} Engineer`, text: workNote.trim() }] : [],
        approvals,
      })
      onCompleted(res.message, res.ticket.id)
      onClose()
    } catch (error) {
      setErr(error instanceof Error ? error.message : 'Ticket ingestion failed.')
    } finally {
      setBusy(false)
    }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault()
    if (!file) {
      setErr('Select a CSV or JSON ticket dataset file first.')
      return
    }
    setBusy(true)
    setErr('')
    try {
      const res = await api.uploadTicketsFile(file)
      onCompleted(
        `${res.processed} tickets ingested & audited (${res.highRisk} high-risk, ${res.missingApprovals} missing approvals, ${res.slaIssues} SLA issues).`,
      )
      onClose()
    } catch (error) {
      setErr(error instanceof Error ? error.message : 'File upload failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-label="Ingest ITSM Tickets">
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <span className="breadcrumb">PHASE 1 — ITSM TICKET INGESTION</span>
            <h3 style={{ marginTop: 4 }}>Ingest &amp; Auto-Audit ITSM Tickets</h3>
          </div>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="tab-bar">
          <button type="button" className={`tab-btn ${mode === 'create' ? 'active' : ''}`} onClick={() => setMode('create')}>
            Create Single Ticket
          </button>
          <button type="button" className={`tab-btn ${mode === 'upload' ? 'active' : ''}`} onClick={() => setMode('upload')}>
            Bulk Upload (CSV / JSON)
          </button>
        </div>

        {mode === 'create' ? (
          <form className="stack-sm" onSubmit={handleCreate}>
            <div className="grid-2">
              <div>
                <label className="field-label" htmlFor="ing-type">Ticket Type</label>
                <select id="ing-type" className="select" value={ticketType} onChange={(e) => setTicketType(e.target.value as 'CR' | 'INC' | 'SR')}>
                  <option value="CR">CR — Change Request</option>
                  <option value="INC">INC — Incident</option>
                  <option value="SR">SR — Service Request</option>
                </select>
              </div>
              <div>
                <label className="field-label" htmlFor="ing-priority">Priority</label>
                <select id="ing-priority" className="select" value={priority} onChange={(e) => setPriority(e.target.value as 'P1' | 'P2' | 'P3' | 'P4')}>
                  <option value="P1">P1 — Critical</option>
                  <option value="P2">P2 — High</option>
                  <option value="P3">P3 — Moderate</option>
                  <option value="P4">P4 — Low</option>
                </select>
              </div>
            </div>

            <div>
              <label className="field-label" htmlFor="ing-desc">Short Description</label>
              <input
                id="ing-desc"
                className="input"
                placeholder="e.g. Production database cluster patch deployment"
                value={shortDesc}
                onChange={(e) => setShortDesc(e.target.value)}
                required
              />
            </div>

            <div className="grid-2">
              <div>
                <label className="field-label" htmlFor="ing-group">Assignment Group</label>
                <select id="ing-group" className="select" value={group} onChange={(e) => setGroup(e.target.value)}>
                  <option value="Infrastructure">Infrastructure</option>
                  <option value="Applications">Applications</option>
                  <option value="Security">Security</option>
                  <option value="Network Operations">Network Operations</option>
                  <option value="Service Desk">Service Desk</option>
                </select>
              </div>
              <div>
                <label className="field-label" htmlFor="ing-bu">Business Unit</label>
                <select id="ing-bu" className="select" value={bu} onChange={(e) => setBu(e.target.value)}>
                  <option value="Core Operations">Core Operations</option>
                  <option value="Retail Banking">Retail Banking</option>
                  <option value="Digital Channels">Digital Channels</option>
                  <option value="Enterprise IT">Enterprise IT</option>
                  <option value="Corporate Services">Corporate Services</option>
                </select>
              </div>
            </div>

            <div className="grid-2">
              <div>
                <label className="field-label" htmlFor="ing-state">Ticket State</label>
                <select id="ing-state" className="select" value={state} onChange={(e) => setState(e.target.value as 'Scheduled' | 'Pending Approval' | 'In Progress' | 'Closed')}>
                  <option value="Scheduled">Scheduled (Pre-Closure)</option>
                  <option value="Pending Approval">Pending Approval</option>
                  <option value="In Progress">In Progress</option>
                  <option value="Closed">Closed</option>
                </select>
              </div>
              <div>
                <label className="field-label" htmlFor="ing-sla">SLA Status</label>
                <select id="ing-sla" className="select" value={sla} onChange={(e) => setSla(e.target.value as 'Within SLA' | 'At Risk' | 'Met' | 'Breached')}>
                  <option value="Within SLA">Within SLA</option>
                  <option value="At Risk">At Risk</option>
                  <option value="Met">Met</option>
                  <option value="Breached">Breached</option>
                </select>
              </div>
            </div>

            <div>
              <label className="field-label" htmlFor="ing-note">Initial Work Notes (parsed by Evidence Extraction Agent)</label>
              <textarea
                id="ing-note"
                className="textarea"
                placeholder="e.g. Risk assessment completed. Implementation window reserved for 22:00 UTC. No rollback plan detected yet."
                value={workNote}
                onChange={(e) => setWorkNote(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap', fontSize: 13 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                <input type="checkbox" checked={includeTechApproval} onChange={(e) => setIncludeTechApproval(e.target.checked)} />
                Include Technical Approval
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                <input type="checkbox" checked={includeBizApproval} onChange={(e) => setIncludeBizApproval(e.target.checked)} />
                Include Business / Manager Approval
              </label>
            </div>

            {err ? <div style={{ color: 'var(--fail)', fontSize: 13 }}>{err}</div> : null}

            <div className="modal-foot">
              <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={busy}>
                {busy ? 'Running 6-Agent Audit…' : 'Ingest & Run AI Audit'}
              </button>
            </div>
          </form>
        ) : (
          <form className="stack-sm" onSubmit={handleUpload}>
            <div className="explain-row">
              <div className="explain-row-label">Supported Format</div>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                Upload a <code>.csv</code> or <code>.json</code> ITSM export containing columns such as{' '}
                <code>ticket_id</code>, <code>ticket_type</code> (INC/SR/CR), <code>short_description</code>,{' '}
                <code>priority</code>, <code>assignment_group</code>, <code>work_notes</code>, and <code>approvals</code>.
                See <code>sample-data/sample_tickets.csv</code> in the repository.
              </p>
            </div>
            <div>
              <label className="field-label" htmlFor="ing-file">Select CSV or JSON File</label>
              <input
                id="ing-file"
                type="file"
                accept=".csv,.json"
                className="input"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </div>
            {err ? <div style={{ color: 'var(--fail)', fontSize: 13 }}>{err}</div> : null}
            <div className="modal-foot">
              <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={busy || !file}>
                {busy ? 'Ingesting & Auditing…' : 'Upload & Auto-Audit Batch'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
