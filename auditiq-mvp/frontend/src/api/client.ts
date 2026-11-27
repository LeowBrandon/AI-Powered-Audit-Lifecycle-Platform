import type {
  AnalyticsResponse,
  ConfigResponse,
  CopilotResponse,
  DashboardResponse,
  KnowledgeResponse,
  MonitoringResponse,
  QcResponse,
  QueueResponse,
  RagHit,
  TicketDetail,
} from '../types/auditiq'

export const API_BASE = (
  import.meta.env.VITE_API_BASE || 'http://localhost:8000'
).replace(/\/$/, '')

export const WS_MONITORING_URL =
  API_BASE.replace(/^http/, 'ws') + '/ws/monitoring'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(init?.headers || {}),
    },
  })
  if (!res.ok) {
    let msg = `Request failed (${res.status})`
    try {
      const err = await res.json()
      if (err?.detail) msg = String(err.detail)
    } catch {
      // ignore non-json error body
    }
    throw new Error(msg)
  }
  return res.json() as Promise<T>
}

export interface QueueFilterParams {
  ticket_type?: string
  risk?: string
  business_unit?: string
  assignment_group?: string
  auditor?: string
  audit_status?: string
  violation_type?: string
  confidence_tier?: string
  date_from?: string
  date_to?: string
  search?: string
  only_attention?: boolean
}

export const api = {
  health: () =>
    request<{ status: string; version: string; aiModel: string; llmEnabled: boolean }>(
      '/api/health',
    ),

  dashboard: () => request<DashboardResponse>('/api/dashboard'),

  monitoring: () => request<MonitoringResponse>('/api/monitoring'),

  simulateLiveEvent: () =>
    request<{ message: string; ticket: TicketDetail }>('/api/monitoring/simulate', {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  updateAlertStatus: (alertId: string, status: 'Acknowledged' | 'Resolved') =>
    request<{ message: string }>(`/api/monitoring/alerts/${alertId}/status`, {
      method: 'POST',
      body: JSON.stringify({ status }),
    }),

  tickets: (filters: QueueFilterParams = {}) => {
    const qs = new URLSearchParams()
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== '' && v !== 'ALL' && v !== false) {
        qs.set(k, String(v))
      }
    })
    const suffix = qs.toString() ? `?${qs.toString()}` : ''
    return request<QueueResponse>(`/api/tickets${suffix}`)
  },

  ticketDetail: (ticketId: string) =>
    request<TicketDetail>(`/api/tickets/${encodeURIComponent(ticketId)}`),

  createTicket: (payload: Record<string, unknown>) =>
    request<{ message: string; ticket: TicketDetail }>('/api/tickets', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  uploadTicketsFile: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<{
      message: string
      processed: number
      ticketIds: string[]
      highRisk: number
      missingApprovals: number
      slaIssues: number
    }>('/api/tickets/upload', {
      method: 'POST',
      body: form,
    })
  },

  batchAuditAll: () =>
    request<{ message: string; processed: number; highRisk: number }>(
      '/api/tickets/batch-audit',
      { method: 'POST', body: JSON.stringify({}) },
    ),

  reanalyze: (ticketId: string) =>
    request<{ message: string; ticket: TicketDetail }>(
      `/api/reanalyze/${encodeURIComponent(ticketId)}`,
      { method: 'POST', body: JSON.stringify({}) },
    ),

  remediate: (
    ticketId: string,
    payload: {
      action_type:
        | 'business_approval'
        | 'technical_approval'
        | 'rollback_plan'
        | 'post_validation'
        | 'root_cause'
        | 'customer_communication'
        | 'work_note'
        | 'close_ticket'
      actor: string
      role: string
      approver?: string
      note?: string
      closure_code?: string
    },
  ) =>
    request<{ message: string; ticket: TicketDetail }>(
      `/api/tickets/${encodeURIComponent(ticketId)}/remediate`,
      { method: 'POST', body: JSON.stringify(payload) },
    ),

  findingAction: (
    ticketId: string,
    findingId: string,
    payload: {
      decision: 'APPROVE_FINDING' | 'OVERRIDE_PASS' | 'OVERRIDE_FAIL' | 'REQUEST_EVIDENCE'
      note: string
      auditor: string
      role: string
      improvement_target:
        | 'Audit Rules'
        | 'Prompts'
        | 'RAG Retrieval'
        | 'Evidence Extraction'
        | 'Confidence Thresholds'
    },
  ) =>
    request<{ message: string; ticket: TicketDetail }>(
      `/api/tickets/${encodeURIComponent(ticketId)}/findings/${encodeURIComponent(findingId)}/action`,
      { method: 'POST', body: JSON.stringify(payload) },
    ),

  askCopilot: (payload: {
    ticket_id: string | null
    question: string
    user_role: string
  }) =>
    request<CopilotResponse>('/api/copilot', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  qc: () => request<QcResponse>('/api/qc'),

  submitQcReview: (
    auditId: string,
    payload: { qc_status: 'Verified' | 'Disputed'; qc_reviewer: string; qc_note: string },
  ) =>
    request<{ message: string; qc: QcResponse }>(
      `/api/qc/reviews/${encodeURIComponent(auditId)}`,
      { method: 'POST', body: JSON.stringify(payload) },
    ),

  updateFeedbackStatus: (
    feedbackId: string,
    applied_status: 'Captured' | 'Queued for Tuning' | 'Applied',
  ) =>
    request<{ message: string }>(
      `/api/qc/feedback/${encodeURIComponent(feedbackId)}`,
      { method: 'PATCH', body: JSON.stringify({ applied_status }) },
    ),

  analytics: () => request<AnalyticsResponse>('/api/analytics'),

  knowledge: (category?: string, appliesTo?: string) => {
    const qs = new URLSearchParams()
    if (category && category !== 'ALL') qs.set('category', category)
    if (appliesTo && appliesTo !== 'ALL') qs.set('applies_to', appliesTo)
    const suffix = qs.toString() ? `?${qs.toString()}` : ''
    return request<KnowledgeResponse>(`/api/knowledge${suffix}`)
  },

  searchKnowledge: (q: string, ticketType?: string) => {
    const qs = new URLSearchParams({ q })
    if (ticketType && ticketType !== 'ALL') qs.set('ticket_type', ticketType)
    return request<{ query: string; hits: RagHit[] }>(`/api/knowledge/search?${qs.toString()}`)
  },

  createPolicy: (payload: Record<string, unknown>) =>
    request<{ message: string; policyId: string }>('/api/knowledge', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  config: () => request<ConfigResponse>('/api/config'),

  updateConfig: (payload: Record<string, unknown>) =>
    request<{ message: string; config: ConfigResponse }>('/api/config', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  updateCriterion: (criterionId: string, payload: Record<string, unknown>) =>
    request<{ message: string; config: ConfigResponse }>(
      `/api/config/criteria/${encodeURIComponent(criterionId)}`,
      { method: 'PATCH', body: JSON.stringify(payload) },
    ),

  createCriterion: (payload: Record<string, unknown>) =>
    request<{ message: string; config: ConfigResponse }>('/api/config/criteria', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  resetDemo: () =>
    request<{ message: string; tickets: number }>('/api/config/reset-demo', {
      method: 'POST',
      body: JSON.stringify({}),
    }),
}
