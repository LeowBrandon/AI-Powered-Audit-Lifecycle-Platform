export type PageId =
  | 'dashboard'
  | 'monitoring'
  | 'queue'
  | 'detail'
  | 'copilot'
  | 'qc'
  | 'analytics'
  | 'knowledge'
  | 'config'

export type UserRole =
  | 'Auditor'
  | 'QC Reviewer'
  | 'Operations Manager'
  | 'Governance Administrator'

export interface RoleProfile {
  role: UserRole
  userName: string
  initials: string
  department: string
  capabilities: string[]
}

export interface RiskDistribution {
  CRITICAL: number
  HIGH: number
  MEDIUM: number
  LOW: number
}

export interface SamplingBucket {
  tier: string
  risk: string
  count: number
}

export interface TrendPoint {
  period: string
  month: string
  value: number
  count: number
}

export interface MonitoringAlertItem {
  alertId?: string
  alert_id?: string
  ticketId?: string
  ticket_id?: string
  ticketType?: string
  ticket_type?: string
  shortDescription?: string
  short_description?: string
  assignmentGroup?: string
  assignment_group?: string
  ticketState?: string
  severity: string
  title: string
  message: string
  recommendation: string
  predictedRisk?: number
  predicted_risk?: number
  status: string
  createdAt?: string
  created_at?: string
}

export interface DashboardResponse {
  total: number
  auditCompletion: number
  compliance: number
  highRisk: number
  aiAlerts: number
  avgAuditTime: number
  autoAudited: number
  riskDistribution: RiskDistribution
  samplingDistribution: SamplingBucket[]
  trend: TrendPoint[]
  trendDelta: number
  managementInsight: {
    narrative: string
    topRiskArea: string
    topRootCause: string
    slaViolations: number
    approvalViolations: number
    documentationIssues: number
  }
  recentAlerts: MonitoringAlertItem[]
  isDemoData: boolean
}

export interface QueueTicket {
  id: string
  type: 'INC' | 'SR' | 'CR'
  shortDescription: string
  priority: string
  category: string
  businessUnit: string
  assignmentGroup: string
  owner: string
  state: string
  sla: string
  createdAt: string
  auditId: string
  compliance: number
  risk: number
  riskBand: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  decision: 'PASS' | 'FAIL' | 'REVIEW'
  samplingTier: string
  confidence: number
  auditStatus: string
  auditor: string
  qcStatus: string
  predictedFailureProb: number
  openFindings: number
  violations: string
}

export interface QueueFacets {
  businessUnits: string[]
  assignmentGroups: string[]
  auditors: string[]
  auditStatuses: string[]
  violationTypes: string[]
}

export interface AuditorWorkload {
  auditor: string
  total: number
  pending: number
  highRisk: number
}

export interface QueueResponse {
  items: QueueTicket[]
  total: number
  facets: QueueFacets
  workload: AuditorWorkload[]
}

export interface WorkNote {
  timestamp: string
  author: string
  text: string
}

export interface ApprovalRecord {
  type: string
  approver: string
  status: string
  timestamp: string
  note: string
}

export interface AttachmentRecord {
  name: string
  section: string
  content_summary: string
}

export interface AuditCriterionResult {
  resultId: string
  criterionId: string
  criterion: string
  requirement: string
  method: 'deterministic' | 'ai'
  policyRef: string
  status: 'PASS' | 'FAIL' | 'REVIEW'
  confidence: number
  confidenceTier: string
  reason: string
  detectedEvidence: string
  missingEvidence: string
  source: string
  searchedSources: string[]
  recommendation: string
}

export interface AuditFinding {
  findingId: string
  criterionId: string
  criterion: string
  policyRef: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  aiStatus: 'FAIL' | 'REVIEW'
  status: string
  confidence: number
  description: string
  detectedEvidence: string
  missingEvidence: string
  recommendation: string
  humanDecision: string
  humanNote: string
  decidedBy: string
  decidedAt: string | null
}

export interface AgentTraceStep {
  agentNumber: number
  agentName: string
  phase: string
  status: string
  durationMs: number
  summary: string
  model: string
  metrics: Record<string, string | number | boolean>
}

export interface EvidenceHighlight {
  sourceType: 'work_note' | 'attachment' | 'approval' | 'resolution'
  sourceIndex: number
  sourceLabel: string
  quote: string
  evidenceLabel: string
  status: 'PASS' | 'REVIEW' | 'FAIL'
  confidence: number
}

export interface AuditTrailEntry {
  trailId: string
  ticketId?: string
  who: string
  role: string
  what: string
  timestamp: string
  rule: string
  evidence: string
  aiModel: string
  confidence: number
  decision: string
  humanOverride: boolean
}

export interface TicketDetail {
  id: string
  type: 'INC' | 'SR' | 'CR'
  shortDescription: string
  description: string
  priority: string
  category: string
  businessUnit: string
  assignmentGroup: string
  requester: string
  owner: string
  resolver: string
  state: string
  sla: string
  closureCode: string
  resolution: string
  targetWindow: string
  createdAt: string
  updatedAt: string
  closedAt: string | null
  workNotes: WorkNote[]
  approvals: ApprovalRecord[]
  attachments: AttachmentRecord[]
  relatedTickets: string[]
  auditId: string
  compliance: number
  risk: number
  riskBand: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  riskBreakdown: Record<string, number>
  predictedFailureProb: number
  predictiveFactors: string[]
  decision: 'PASS' | 'FAIL' | 'REVIEW'
  samplingTier: string
  confidence: number
  aiSummary: string
  auditStatus: string
  auditor: string
  qcStatus: string
  qcReviewer: string
  qcNote: string
  agentTrace: AgentTraceStep[]
  highlights: EvidenceHighlight[]
  lastEvaluated: string
  results: AuditCriterionResult[]
  findings: AuditFinding[]
  auditTrail: AuditTrailEntry[]
  alerts: MonitoringAlertItem[]
}

export interface PredictiveAuditItem {
  ticketId: string
  ticketType: string
  shortDescription: string
  priority: string
  assignmentGroup: string
  state: string
  sla: string
  targetWindow: string
  compliance: number
  riskScore: number
  riskBand: string
  predictedAuditRisk: number
  factors: string[]
  summary: string
}

export interface LiveEventMessage {
  event: string
  timestamp: string
  payload?: Record<string, unknown>
}

export interface MonitoringResponse {
  activeTicketCount: number
  riskSummary: RiskDistribution
  alerts: MonitoringAlertItem[]
  resolvedAlertsCount: number
  predictiveAudits: PredictiveAuditItem[]
  wsClients: number
  recentEvents: LiveEventMessage[]
}

export interface CopilotSource {
  type: string
  label: string
  ref: string
  detail: string
}

export interface CopilotResponse {
  answer: string
  sources: CopilotSource[]
  referencedTickets: string[]
  ticketId: string | null
  model: string
}

export interface QcAuditorRow {
  name: string
  audits: number
  avgScore: number
  overrides: number
  disputed: number
  agreement: number
  variance: number
  status: 'OUTLIER' | 'REVIEW' | 'STABLE'
}

export interface QcExceptionRow {
  auditId: string
  ticketId: string
  ticketType: string
  shortDescription: string
  assignmentGroup: string
  auditor: string
  auditScore: number
  riskScore: number
  riskBand: string
  aiConfidence: number
  qcStatus: string
  qcReviewer: string
  qcNote: string
  exceptionReasons: string[]
}

export interface FeedbackLoopItem {
  feedback_id: string
  audit_id: string
  ticket_id: string
  criterion_name: string
  ai_decision: string
  auditor_decision: string
  reason: string
  improvement_target: string
  auditor: string
  applied_status: string
  created_at: string
}

export interface QcResponse {
  auditorVariance: number
  disputed: number
  aiHumanAgreement: number
  exceptionsCount: number
  feedbackCount: number
  auditors: QcAuditorRow[]
  exceptions: QcExceptionRow[]
  focusBuckets: { title: string; count: number; description: string }[]
  feedbackLoop: FeedbackLoopItem[]
}

export interface AnalyticsResponse {
  summary: {
    ticketsAudited: number
    complianceRate: number
    highRiskTickets: number
    slaViolations: number
    approvalViolations: number
    documentationIssues: number
    trendDelta: number
    topRiskArea: string
    topRootCause: string
    narrative: string
  }
  ticketType: { label: string; value: number; count: number }[]
  department: { label: string; value: number; count: number; highRisk: number }[]
  businessUnit: { label: string; value: number; count: number }[]
  failureCategories: { label: string; count: number; value: number }[]
  trend: TrendPoint[]
  riskDistribution: RiskDistribution
  samplingDistribution: SamplingBucket[]
  targetKpis: {
    category: string
    metric: string
    before: string
    target: string
    demoCurrent: string
  }[]
}

export interface PolicyDoc {
  policyId: string
  title: string
  category: string
  version: string
  effectiveDate: string
  owner: string
  appliesTo: string
  summary: string
  content: string
  tags: string[]
}

export interface RagHit {
  policyId: string
  title: string
  category: string
  version: string
  appliesTo: string
  score: number
  excerpt: string
  matchedTerms: string[]
}

export interface KnowledgeResponse {
  items: PolicyDoc[]
  categories: string[]
  total: number
}

export interface CriterionConfig {
  criterionId: string
  auditType: 'INC' | 'SR' | 'CR'
  criterionName: string
  requirement: string
  rule: string
  policyRef: string
  method: 'deterministic' | 'ai'
  weight: number
  severityIfFailed: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  active: boolean
}

export interface ConfigResponse {
  confidenceAuto: number
  confidenceRecommend: number
  criticalRisk: number
  highRisk: number
  mediumRisk: number
  sampling: number
  proactiveAlertsEnabled: boolean
  autoCloseLowRisk: boolean
  updatedBy: string
  updatedAt: string
  aiEngine: {
    llmEnabled: boolean
    modelLabel: string
    llmModel: string
  }
  rules: Record<string, CriterionConfig[]>
}
