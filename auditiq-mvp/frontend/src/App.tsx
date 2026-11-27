import React, { useCallback, useEffect, useRef, useState } from 'react'
import { api, WS_MONITORING_URL } from './api/client'
import type {
  AnalyticsResponse,
  ConfigResponse,
  DashboardResponse,
  MonitoringResponse,
  PageId,
  QcResponse,
  QueueTicket,
  RoleProfile,
  TicketDetail,
  UserRole,
} from './types/auditiq'
import { IngestModal } from './components/IngestModal'
import { DashboardPage } from './pages/DashboardPage'
import { MonitoringPage } from './pages/MonitoringPage'
import { QueuePage } from './pages/QueuePage'
import { TicketDetailPage } from './pages/TicketDetailPage'
import { CopilotPage } from './pages/CopilotPage'
import { QcPage } from './pages/QcPage'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { KnowledgeBasePage } from './pages/KnowledgeBasePage'
import { ConfigPage } from './pages/ConfigPage'

const ROLE_PROFILES: Record<UserRole, RoleProfile> = {
  Auditor: {
    role: 'Auditor',
    userName: 'A. Rahman',
    initials: 'AR',
    department: 'Operations Governance Audit',
    capabilities: ['Review AI findings', 'Approve / override', 'Request evidence', 'Perform audits'],
  },
  'QC Reviewer': {
    role: 'QC Reviewer',
    userName: 'L. Chen',
    initials: 'LC',
    department: 'Audit Quality Control',
    capabilities: ['Review auditor decisions', 'Detect inconsistencies', 'Approve QC outcomes'],
  },
  'Operations Manager': {
    role: 'Operations Manager',
    userName: 'D. Morales',
    initials: 'DM',
    department: 'IT Operations Leadership',
    capabilities: ['View compliance', 'Monitor trends', 'Investigate high-risk teams'],
  },
  'Governance Administrator': {
    role: 'Governance Administrator',
    userName: 'R. Tan',
    initials: 'RT',
    department: 'Enterprise Governance Admin',
    capabilities: ['Configure audit rules', 'Manage policies', 'Configure AI thresholds'],
  },
}

const NAV_ITEMS: { id: PageId; label: string; section: 'OPERATIONS' | 'GOVERNANCE'; glyph: string }[] = [
  { id: 'dashboard', label: 'Executive Dashboard', section: 'OPERATIONS', glyph: '◫' },
  { id: 'monitoring', label: 'Live Monitoring', section: 'OPERATIONS', glyph: '◉' },
  { id: 'queue', label: 'Audit Queue', section: 'OPERATIONS', glyph: '▤' },
  { id: 'detail', label: 'Ticket Audit Detail', section: 'OPERATIONS', glyph: '◧' },
  { id: 'copilot', label: 'Auditor Copilot', section: 'OPERATIONS', glyph: '✦' },
  { id: 'qc', label: 'QC & Learning Loop', section: 'GOVERNANCE', glyph: '◎' },
  { id: 'analytics', label: 'Analytics & Insights', section: 'GOVERNANCE', glyph: '◔' },
  { id: 'knowledge', label: 'Policy Knowledge Base', section: 'GOVERNANCE', glyph: '§' },
  { id: 'config', label: 'Audit Configuration', section: 'GOVERNANCE', glyph: '⚙' },
]

export function App() {
  const [page, setPage] = useState<PageId>('dashboard')
  const [role, setRole] = useState<UserRole>('Auditor')
  const [selectedTicketId, setSelectedTicketId] = useState<string>('CR001992')
  const [queueRiskFilter, setQueueRiskFilter] = useState<string | undefined>(undefined)
  const [policySearchQuery, setPolicySearchQuery] = useState<string | undefined>(undefined)

  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null)
  const [monitoring, setMonitoring] = useState<MonitoringResponse | null>(null)
  const [allTickets, setAllTickets] = useState<QueueTicket[]>([])
  const [ticketDetail, setTicketDetail] = useState<TicketDetail | null>(null)
  const [qc, setQc] = useState<QcResponse | null>(null)
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null)
  const [config, setConfig] = useState<ConfigResponse | null>(null)

  const [wsConnected, setWsConnected] = useState(false)
  const [ingestOpen, setIngestOpen] = useState(false)
  const [refreshSignal, setRefreshSignal] = useState(0)
  const [toast, setToast] = useState<{ text: string; isError?: boolean } | null>(null)

  const selectedRef = useRef(selectedTicketId)
  selectedRef.current = selectedTicketId

  const notify = useCallback((text: string, isError = false) => {
    setToast({ text, isError })
  }, [])

  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(null), 4200)
    return () => clearTimeout(timer)
  }, [toast])

  const loadAll = useCallback(async () => {
    try {
      const [d, m, qList, td, qcData, anData, cfg] = await Promise.all([
        api.dashboard(),
        api.monitoring(),
        api.tickets(),
        api.ticketDetail(selectedRef.current),
        api.qc(),
        api.analytics(),
        api.config(),
      ])
      setDashboard(d)
      setMonitoring(m)
      setAllTickets(qList.items)
      setTicketDetail(td)
      setQc(qcData)
      setAnalytics(anData)
      setConfig(cfg)
      setRefreshSignal((s) => s + 1)
    } catch {
      notify('Backend API unreachable. Start FastAPI on port 8000.', true)
    }
  }, [notify])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  // Load ticket detail whenever selectedTicketId changes
  useEffect(() => {
    api
      .ticketDetail(selectedTicketId)
      .then(setTicketDetail)
      .catch(() => {})
  }, [selectedTicketId])

  // Real-Time WebSocket Monitoring Connection (Proposal Section 19)
  useEffect(() => {
    let ws: WebSocket | null = null
    let closedByUnmount = false
    let retryTimer: number | undefined

    function connect() {
      try {
        ws = new WebSocket(WS_MONITORING_URL)
        ws.onopen = () => setWsConnected(true)
        ws.onclose = () => {
          setWsConnected(false)
          if (!closedByUnmount) {
            retryTimer = window.setTimeout(connect, 4000)
          }
        }
        ws.onerror = () => setWsConnected(false)
        ws.onmessage = (evt) => {
          try {
            const msg = JSON.parse(evt.data)
            if (msg.event && msg.event !== 'connected' && msg.event !== 'pong') {
              loadAll()
            }
          } catch {
            // ignore malformed frame
          }
        }
      } catch {
        setWsConnected(false)
      }
    }

    connect()
    return () => {
      closedByUnmount = true
      if (retryTimer) window.clearTimeout(retryTimer)
      if (ws) ws.close()
    }
  }, [loadAll])

  const profile = ROLE_PROFILES[role]
  const activeNav = NAV_ITEMS.find((n) => n.id === page)

  function openTicket(ticketId: string) {
    setSelectedTicketId(ticketId)
    setPage('detail')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function navigate(target: PageId, riskFilter?: string) {
    if (target === 'queue') {
      setQueueRiskFilter(riskFilter)
    }
    setPage(target)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function openPolicySearch(query: string) {
    setPolicySearchQuery(query)
    setPage('knowledge')
  }

  async function handleResetDemo() {
    try {
      const res = await api.resetDemo()
      setSelectedTicketId('CR001992')
      await loadAll()
      notify(res.message)
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Demo reset failed.', true)
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="AuditIQ Navigation">
        <div className="brand-row">
          <div className="brand-mark">A</div>
          <div>
            <div className="brand-title">AuditIQ</div>
            <div className="brand-subtitle">Continuous Audit Intelligence</div>
          </div>
        </div>

        <div className="demo-status-box">
          <span className="status-indicator">
            <span className={`dot ${wsConnected ? 'live' : 'offline'}`} />
            {wsConnected ? 'Live Monitor Active' : 'Simulated Demo'}
          </span>
          <span className="mono" style={{ fontSize: 11, opacity: 0.7 }}>MVP</span>
        </div>

        <nav className="nav-list">
          <div className="nav-section-label">Operations</div>
          {NAV_ITEMS.filter((i) => i.section === 'OPERATIONS').map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav-btn ${page === item.id ? 'active' : ''}`}
              onClick={() => navigate(item.id)}
            >
              <span className="nav-icon" aria-hidden="true">{item.glyph}</span>
              <span>{item.label}</span>
              {item.id === 'monitoring' && dashboard && dashboard.aiAlerts > 0 ? (
                <span className="nav-count">{dashboard.aiAlerts}</span>
              ) : null}
            </button>
          ))}

          <div className="nav-section-label">Governance &amp; Intelligence</div>
          {NAV_ITEMS.filter((i) => i.section === 'GOVERNANCE').map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav-btn ${page === item.id ? 'active' : ''}`}
              onClick={() => navigate(item.id)}
            >
              <span className="nav-icon" aria-hidden="true">{item.glyph}</span>
              <span>{item.label}</span>
              {item.id === 'qc' && qc && qc.disputed > 0 ? (
                <span className="nav-count">{qc.disputed}</span>
              ) : null}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div>9 AI Agents · Deterministic Rules · RAG KB</div>
          <div style={{ opacity: 0.8 }}>Demo Dataset · Simulated ITSM Metrics</div>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <span className="breadcrumb">AuditIQ Governance / {activeNav?.section}</span>
            <h1>{activeNav?.label || 'AuditIQ'}</h1>
          </div>

          <div className="topbar-actions">
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setIngestOpen(true)}>
              + Ingest Tickets
            </button>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => loadAll()}>
              ↻ Sync
            </button>

            <div className="role-switcher" title={`Capabilities: ${profile.capabilities.join(' · ')}`}>
              <div className="role-avatar">{profile.initials}</div>
              <div>
                <select
                  aria-label="Switch Active User Role"
                  className="role-select"
                  value={role}
                  onChange={(e) => {
                    const next = e.target.value as UserRole
                    setRole(next)
                    notify(`Switched workspace persona to ${next} (${ROLE_PROFILES[next].userName}).`)
                  }}
                >
                  {(Object.keys(ROLE_PROFILES) as UserRole[]).map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
                <span className="role-sub">{profile.userName} · {profile.department}</span>
              </div>
            </div>
          </div>
        </header>

        <main className="page-container">
          {page === 'dashboard' ? (
            <DashboardPage
              data={dashboard}
              onOpenTicket={openTicket}
              onNavigate={navigate}
              onOpenIngest={() => setIngestOpen(true)}
            />
          ) : null}

          {page === 'monitoring' ? (
            <MonitoringPage
              data={monitoring}
              wsConnected={wsConnected}
              onOpenTicket={openTicket}
              onRefresh={loadAll}
              onNotify={notify}
              onOpenIngest={() => setIngestOpen(true)}
            />
          ) : null}

          {page === 'queue' ? (
            <QueuePage
              initialRiskFilter={queueRiskFilter}
              onOpenTicket={openTicket}
              onOpenIngest={() => setIngestOpen(true)}
              onNotify={notify}
              refreshSignal={refreshSignal}
            />
          ) : null}

          {page === 'detail' ? (
            <TicketDetailPage
              ticket={ticketDetail}
              allTickets={allTickets}
              profile={profile}
              onSelectTicket={(id) => setSelectedTicketId(id)}
              onBackToQueue={() => navigate('queue')}
              onTicketUpdated={(updated, msg) => {
                setTicketDetail(updated)
                loadAll()
                notify(msg)
              }}
              onOpenPolicySearch={openPolicySearch}
              onNavigate={navigate}
              onResetDemo={handleResetDemo}
              onNotify={notify}
            />
          ) : null}

          {page === 'copilot' ? (
            <CopilotPage
              selectedTicketId={selectedTicketId}
              allTickets={allTickets}
              profile={profile}
              onSelectTicket={(id) => setSelectedTicketId(id)}
              onOpenTicket={openTicket}
              onOpenPolicySearch={openPolicySearch}
            />
          ) : null}

          {page === 'qc' ? (
            <QcPage
              data={qc}
              profile={profile}
              onOpenTicket={openTicket}
              onRefresh={loadAll}
              onNotify={notify}
            />
          ) : null}

          {page === 'analytics' ? <AnalyticsPage data={analytics} /> : null}

          {page === 'knowledge' ? (
            <KnowledgeBasePage initialQuery={policySearchQuery} onNotify={notify} />
          ) : null}

          {page === 'config' ? (
            <ConfigPage
              data={config}
              profile={profile}
              onRefreshAll={loadAll}
              onNotify={notify}
            />
          ) : null}
        </main>
      </div>

      <IngestModal
        open={ingestOpen}
        onClose={() => setIngestOpen(false)}
        onCompleted={(msg, openId) => {
          loadAll()
          notify(msg)
          if (openId) openTicket(openId)
        }}
      />

      {toast ? (
        <div className={`toast ${toast.isError ? 'error' : ''}`} role="status">
          {toast.text}
        </div>
      ) : null}
    </div>
  )
}
export default App
