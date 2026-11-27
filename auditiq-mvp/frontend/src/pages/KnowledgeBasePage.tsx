import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { KnowledgeResponse, RagHit } from '../types/auditiq'
import { TypeChip } from '../components/Badges'

interface KnowledgeBasePageProps {
  initialQuery?: string
  onNotify: (msg: string, isError?: boolean) => void
}

export function KnowledgeBasePage({ initialQuery, onNotify }: KnowledgeBasePageProps) {
  const [kb, setKb] = useState<KnowledgeResponse | null>(null)
  const [category, setCategory] = useState('ALL')
  const [query, setQuery] = useState(initialQuery || 'business approval rollback plan')
  const [ragHits, setRagHits] = useState<RagHit[]>([])
  const [searching, setSearching] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>('POL-CHG-3.2')

  // Add policy modal state
  const [showAdd, setShowAdd] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newCategory, setNewCategory] = useState('Audit SOP')
  const [newApplies, setNewApplies] = useState<'ALL' | 'INC' | 'SR' | 'CR'>('CR')
  const [newSummary, setNewSummary] = useState('')
  const [newContent, setNewContent] = useState('')
  const [saving, setSaving] = useState(false)

  async function loadPolicies() {
    const res = await api.knowledge(category)
    setKb(res)
  }

  useEffect(() => {
    loadPolicies().catch((err) =>
      onNotify(err instanceof Error ? err.message : 'Failed to load policies.', true),
    )
  }, [category])

  useEffect(() => {
    if (initialQuery) {
      setQuery(initialQuery)
      runSearch(initialQuery)
    }
  }, [initialQuery])

  async function runSearch(qText: string) {
    if (qText.trim().length < 2) return
    setSearching(true)
    try {
      const res = await api.searchKnowledge(qText.trim())
      setRagHits(res.hits)
    } catch (err) {
      onNotify(err instanceof Error ? err.message : 'RAG search failed.', true)
    } finally {
      setSearching(false)
    }
  }

  async function handleCreatePolicy(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const res = await api.createPolicy({
        title: newTitle.trim(),
        category: newCategory,
        applies_to: newApplies,
        summary: newSummary.trim(),
        content: newContent.trim(),
        tags: [newCategory.toLowerCase(), newApplies.toLowerCase()],
      })
      setShowAdd(false)
      setNewTitle('')
      setNewSummary('')
      setNewContent('')
      await loadPolicies()
      onNotify(res.message)
    } catch (err) {
      onNotify(err instanceof Error ? err.message : 'Could not save policy.', true)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="stack-md">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
        <div>
          <h2 style={{ fontSize: 20 }}>Audit Policy Knowledge Base (RAG Layer)</h2>
          <p className="card-subtitle">
            Proposal Section 17 — enterprise policies, SOPs, ITIL standards, and historical findings indexed for Retrieval-Augmented Generation.
          </p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => setShowAdd(true)}>
          + Add Policy Document
        </button>
      </div>

      {/* Interactive RAG Retrieval Tester */}
      <section className="card">
        <div className="card-header">
          <div>
            <h3>Live RAG Policy Retrieval Tester</h3>
            <p className="card-subtitle">
              Query → TF-IDF Cosine Similarity Vector Search → Top Governing Policy Passages → Audit Reasoning.
            </p>
          </div>
        </div>
        <form
          style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}
          onSubmit={(e) => {
            e.preventDefault()
            runSearch(query)
          }}
        >
          <input
            id="rag-query"
            className="input"
            style={{ flex: 1, minWidth: 260 }}
            placeholder="e.g. When is business approval required before production change implementation?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="btn btn-primary" disabled={searching}>
            {searching ? 'Retrieving…' : 'Search Knowledge Base'}
          </button>
        </form>

        {ragHits.length > 0 ? (
          <div className="stack-sm" style={{ marginTop: 14 }}>
            {ragHits.map((hit) => (
              <div key={hit.policyId} className="explain-row" style={{ background: 'var(--bg-surface)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <TypeChip type={hit.appliesTo} />
                    <strong>{hit.title}</strong>
                    <span className="mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>({hit.version})</span>
                  </div>
                  <span className="badge pass">Match {(hit.score * 100).toFixed(0)}%</span>
                </div>
                <p style={{ marginTop: 6, fontSize: 13, color: 'var(--text-secondary)' }}>{hit.excerpt}</p>
                {hit.matchedTerms.length > 0 ? (
                  <div style={{ marginTop: 6, fontSize: 11, color: 'var(--text-muted)' }}>
                    Matched terms: <span className="mono">{hit.matchedTerms.join(', ')}</span>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}
      </section>

      {/* Policy Repository */}
      <section className="card">
        <div className="card-header">
          <div>
            <h3>Enterprise Policy &amp; SOP Repository ({kb?.total ?? 0})</h3>
            <p className="card-subtitle">Active documents grounding Agents 3, 4, and 7.</p>
          </div>
          <select
            aria-label="Filter policies by category"
            className="select"
            style={{ width: 'auto', minWidth: 210 }}
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="ALL">All Categories</option>
            {(kb?.categories || []).map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div className="stack-sm">
          {(kb?.items || []).map((doc) => {
            const open = expandedId === doc.policyId
            return (
              <div key={doc.policyId} className="explain-row" style={{ background: 'var(--bg-surface)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      <span className="mono" style={{ fontSize: 12, fontWeight: 700, color: 'var(--brand-ink)' }}>{doc.policyId}</span>
                      <TypeChip type={doc.appliesTo} />
                      <span className="badge neutral">{doc.category}</span>
                      <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        {doc.version} · Effective {doc.effectiveDate}
                      </span>
                    </div>
                    <h4 style={{ marginTop: 6, fontSize: 15 }}>{doc.title}</h4>
                    <p style={{ marginTop: 3, fontSize: 13, color: 'var(--text-secondary)' }}>{doc.summary}</p>
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setExpandedId(open ? null : doc.policyId)}
                  >
                    {open ? 'Hide Clauses' : 'Read Policy'}
                  </button>
                </div>
                {open ? (
                  <pre
                    style={{
                      marginTop: 12,
                      padding: 12,
                      borderRadius: 8,
                      background: 'var(--bg-subtle)',
                      border: '1px solid var(--border)',
                      whiteSpace: 'pre-wrap',
                      fontFamily: 'var(--font-body)',
                      fontSize: 13,
                      lineHeight: 1.6,
                    }}
                  >
                    {doc.content}
                  </pre>
                ) : null}
              </div>
            )
          })}
        </div>
      </section>

      {showAdd ? (
        <div className="modal-backdrop" onClick={() => setShowAdd(false)} role="dialog" aria-modal="true">
          <form className="modal-card" onClick={(e) => e.stopPropagation()} onSubmit={handleCreatePolicy}>
            <div className="modal-head">
              <div>
                <span className="breadcrumb">KNOWLEDGE BASE ADMIN</span>
                <h3 style={{ marginTop: 4 }}>Add Enterprise Policy / SOP Document</h3>
              </div>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowAdd(false)}>Close</button>
            </div>
            <div>
              <label className="field-label" htmlFor="pol-title">Policy Title</label>
              <input id="pol-title" className="input" required value={newTitle} onChange={(e) => setNewTitle(e.target.value)} placeholder="e.g. Emergency Change Governance Addendum v1.1" />
            </div>
            <div className="grid-2">
              <div>
                <label className="field-label" htmlFor="pol-cat">Category</label>
                <input id="pol-cat" className="input" value={newCategory} onChange={(e) => setNewCategory(e.target.value)} />
              </div>
              <div>
                <label className="field-label" htmlFor="pol-applies">Applies To</label>
                <select id="pol-applies" className="select" value={newApplies} onChange={(e) => setNewApplies(e.target.value as 'ALL' | 'INC' | 'SR' | 'CR')}>
                  <option value="ALL">ALL</option>
                  <option value="CR">CR</option>
                  <option value="INC">INC</option>
                  <option value="SR">SR</option>
                </select>
              </div>
            </div>
            <div>
              <label className="field-label" htmlFor="pol-sum">Summary</label>
              <input id="pol-sum" className="input" required value={newSummary} onChange={(e) => setNewSummary(e.target.value)} placeholder="Short description of governance scope" />
            </div>
            <div>
              <label className="field-label" htmlFor="pol-content">Policy Clauses (immediately indexed for RAG)</label>
              <textarea id="pol-content" className="textarea" style={{ minHeight: 120 }} required value={newContent} onChange={(e) => setNewContent(e.target.value)} placeholder="Section 1: ..." />
            </div>
            <div className="modal-foot">
              <button type="button" className="btn btn-secondary" onClick={() => setShowAdd(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Indexing…' : 'Save & Index Policy'}
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </div>
  )
}
