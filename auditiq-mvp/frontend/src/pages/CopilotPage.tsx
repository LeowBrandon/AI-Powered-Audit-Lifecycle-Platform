import React, { useState } from 'react'
import { api } from '../api/client'
import type { CopilotSource, QueueTicket, RoleProfile } from '../types/auditiq'

interface CopilotPageProps {
  selectedTicketId: string
  allTickets: QueueTicket[]
  profile: RoleProfile
  onSelectTicket: (id: string) => void
  onOpenTicket: (id: string) => void
  onOpenPolicySearch: (q: string) => void
}

interface ChatItem {
  id: string
  role: 'user' | 'assistant'
  text: string
  sources?: CopilotSource[]
  referencedTickets?: string[]
  model?: string
}

const SUGGESTED_PROMPTS = [
  'Why did this ticket fail?',
  'What evidence supports this finding?',
  'Show me all tickets missing approval.',
  'Compare this ticket against similar tickets.',
  'Which audit rules caused the score to drop?',
  'Give me a summary for management.',
  'What does Change Governance Policy v3.2 require for rollback plans?',
]

const AGENT_ROSTER = [
  ['1', 'Ticket Intelligence Agent', 'Extracts 14 ITSM fields'],
  ['2', 'Evidence Extraction Agent', 'Parses notes & highlights'],
  ['3', 'Audit Rules Agent', 'Deterministic INC/SR/CR rules'],
  ['4', 'AI Audit Reasoning Agent', 'PASS / FAIL / REVIEW + confidence'],
  ['5', 'Risk Scoring Agent', '7-factor risk & predictive model'],
  ['6', 'Continuous Monitoring Agent', 'Pre-closure WebSocket alerts'],
  ['7', 'Auditor Copilot', 'Grounded Q&A & policy RAG'],
  ['8', 'QC Intelligence Agent', 'Variance & outlier detection'],
  ['9', 'Management Insight Agent', 'Executive root-cause briefings'],
]

export function CopilotPage({
  selectedTicketId,
  allTickets,
  profile,
  onSelectTicket,
  onOpenTicket,
  onOpenPolicySearch,
}: CopilotPageProps) {
  const [scope, setScope] = useState<string>(selectedTicketId || 'CR001992')
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState<ChatItem[]>([
    {
      id: 'welcome',
      role: 'assistant',
      text:
        'I am AuditIQ Auditor Copilot (Agent 7). Ask me why a ticket failed, inspect supporting evidence, compare historical peers, query all tickets missing approval, or retrieve requirements from the Audit Policy Knowledge Base.',
    },
  ])

  async function sendQuestion(questionText: string) {
    const q = questionText.trim()
    if (!q || loading) return
    const userMsg: ChatItem = { id: `u-${Date.now()}`, role: 'user', text: q }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)
    try {
      const res = await api.askCopilot({
        ticket_id: scope === 'ALL' ? null : scope,
        question: q,
        user_role: profile.role,
      })
      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: 'assistant',
          text: res.answer,
          sources: res.sources,
          referencedTickets: res.referencedTickets,
          model: res.model,
        },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          role: 'assistant',
          text: `Unable to reach Auditor Copilot backend: ${err instanceof Error ? err.message : 'Unknown error'}`,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="copilot-layout">
      <section className="card stack-md">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
          <div>
            <h2>Ask AuditIQ — Auditor Copilot</h2>
            <p className="card-subtitle">
              Grounded answers backed by live audit findings, extracted evidence, and RAG Policy Knowledge Base.
            </p>
          </div>
          <select
            aria-label="Copilot Ticket Scope"
            className="select"
            style={{ width: 'auto', minWidth: 230 }}
            value={scope}
            onChange={(e) => {
              setScope(e.target.value)
              if (e.target.value !== 'ALL') onSelectTicket(e.target.value)
            }}
          >
            <option value="ALL">All Tickets (Fleet-Wide Query)</option>
            {allTickets.map((t) => (
              <option key={t.id} value={t.id}>
                {t.id} · {t.type} · {t.riskBand} ({t.compliance}%)
              </option>
            ))}
          </select>
        </div>

        <div className="prompt-chips">
          {SUGGESTED_PROMPTS.map((p) => (
            <button key={p} type="button" className="prompt-chip" onClick={() => sendQuestion(p)}>
              {p}
            </button>
          ))}
        </div>

        <div className="chat-window" aria-live="polite">
          {messages.map((m) => (
            <div key={m.id} className={`chat-bubble ${m.role}`}>
              <div style={{ fontSize: 11, fontWeight: 700, opacity: 0.72, marginBottom: 4 }}>
                {m.role === 'user' ? `${profile.userName} (${profile.role})` : 'AuditIQ Copilot'}
              </div>
              <div>{m.text}</div>

              {m.referencedTickets && m.referencedTickets.length > 0 ? (
                <div className="source-pill-row">
                  {m.referencedTickets.map((tid) => (
                    <button key={tid} type="button" className="source-pill mono" onClick={() => onOpenTicket(tid)}>
                      Open {tid} →
                    </button>
                  ))}
                </div>
              ) : null}

              {m.sources && m.sources.length > 0 ? (
                <div className="source-pill-row">
                  {m.sources.map((src, idx) => (
                    <button
                      key={`${src.ref}-${idx}`}
                      type="button"
                      className="source-pill"
                      title={src.detail}
                      onClick={() => {
                        if (src.type === 'policy') onOpenPolicySearch(src.label)
                        else if (src.type === 'ticket') onOpenTicket(src.ref)
                      }}
                    >
                      Source: {src.label}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
          {loading ? <div className="chat-bubble assistant">Analyzing ticket evidence and policy knowledge base…</div> : null}
        </div>

        <form
          style={{ display: 'flex', gap: 10 }}
          onSubmit={(e) => {
            e.preventDefault()
            sendQuestion(input)
          }}
        >
          <input
            id="copilot-input"
            className="input"
            placeholder="Ask why a ticket failed, query missing approvals, or check enterprise policies…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
            Send
          </button>
        </form>
      </section>

      <aside className="card">
        <div className="card-header">
          <div>
            <h3>9-Agent Architecture</h3>
            <p className="card-subtitle">Active collaborative audit specialists.</p>
          </div>
        </div>
        <div className="stack-sm">
          {AGENT_ROSTER.map(([num, name, desc]) => (
            <div key={num} className="explain-row" style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
              <span className="type-chip">{num}</span>
              <div>
                <strong style={{ fontSize: 13 }}>{name}</strong>
                <span className="cell-sub">{desc}</span>
              </div>
            </div>
          ))}
        </div>
      </aside>
    </div>
  )
}
