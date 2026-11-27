import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { ConfigResponse, CriterionConfig, RoleProfile } from '../types/auditiq'
import { DecisionBadge } from '../components/Badges'

interface ConfigPageProps {
  data: ConfigResponse | null
  profile: RoleProfile
  onRefreshAll: () => Promise<void>
  onNotify: (msg: string, isError?: boolean) => void
}

export function ConfigPage({ data, profile, onRefreshAll, onNotify }: ConfigPageProps) {
  const [form, setForm] = useState({
    confidence_auto: 95,
    confidence_recommend: 80,
    critical_risk_threshold: 80,
    high_risk_threshold: 60,
    medium_risk_threshold: 35,
    medium_sampling_pct: 25,
    proactive_alerts_enabled: true,
    auto_close_low_risk: true,
  })
  const [saving, setSaving] = useState(false)
  const [resetting, setResetting] = useState(false)

  // Add custom criterion form
  const [showAddRule, setShowAddRule] = useState(false)
  const [ruleType, setRuleType] = useState<'INC' | 'SR' | 'CR'>('CR')
  const [ruleName, setRuleName] = useState('')
  const [ruleReq, setRuleReq] = useState('Required')
  const [ruleText, setRuleText] = useState('')
  const [ruleMethod, setRuleMethod] = useState<'deterministic' | 'ai'>('ai')
  const [ruleWeight, setRuleWeight] = useState(1.2)

  useEffect(() => {
    if (data) {
      setForm({
        confidence_auto: data.confidenceAuto,
        confidence_recommend: data.confidenceRecommend,
        critical_risk_threshold: data.criticalRisk,
        high_risk_threshold: data.highRisk,
        medium_risk_threshold: data.mediumRisk,
        medium_sampling_pct: data.sampling,
        proactive_alerts_enabled: data.proactiveAlertsEnabled,
        auto_close_low_risk: data.autoCloseLowRisk,
      })
    }
  }, [data])

  if (!data) {
    return <div className="empty-state">Loading Audit Configuration…</div>
  }

  async function saveThresholds(reEvaluateAll: boolean) {
    setSaving(true)
    try {
      const res = await api.updateConfig({
        ...form,
        updated_by: profile.userName,
        re_evaluate_all: reEvaluateAll,
      })
      await onRefreshAll()
      onNotify(res.message)
    } catch (err) {
      onNotify(err instanceof Error ? err.message : 'Failed to save configuration.', true)
    } finally {
      setSaving(false)
    }
  }

  async function toggleRule(rule: CriterionConfig) {
    try {
      const res = await api.updateCriterion(rule.criterionId, { active: !rule.active })
      await onRefreshAll()
      onNotify(res.message)
    } catch (err) {
      onNotify(err instanceof Error ? err.message : 'Failed to update rule.', true)
    }
  }

  async function updateRuleWeight(rule: CriterionConfig, weight: number) {
    if (Number.isNaN(weight) || weight < 0.2 || weight > 5) return
    try {
      await api.updateCriterion(rule.criterionId, { weight })
      await onRefreshAll()
      onNotify(`Updated ${rule.criterionName} weight to ${weight}x.`)
    } catch (err) {
      onNotify(err instanceof Error ? err.message : 'Failed to update weight.', true)
    }
  }

  async function handleCreateRule(e: React.FormEvent) {
    e.preventDefault()
    try {
      const res = await api.createCriterion({
        audit_type: ruleType,
        criterion_name: ruleName.trim(),
        requirement: ruleReq.trim(),
        rule: ruleText.trim(),
        method: ruleMethod,
        weight: ruleWeight,
      })
      setShowAddRule(false)
      setRuleName('')
      setRuleText('')
      await onRefreshAll()
      onNotify(res.message)
    } catch (err) {
      onNotify(err instanceof Error ? err.message : 'Could not add criterion.', true)
    }
  }

  async function handleResetDemo() {
    setResetting(true)
    try {
      const res = await api.resetDemo()
      await onRefreshAll()
      onNotify(res.message)
    } catch (err) {
      onNotify(err instanceof Error ? err.message : 'Reset failed.', true)
    } finally {
      setResetting(false)
    }
  }

  return (
    <div className="stack-md">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
        <div>
          <h2 style={{ fontSize: 20 }}>Audit Configuration &amp; Governance Administration</h2>
          <p className="card-subtitle">
            Enterprise Policy always remains above AI interpretation. Configure AI confidence bands, risk thresholds, sampling rates, and INC/SR/CR audit rules.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-secondary" onClick={() => setShowAddRule(true)}>
            + Add Audit Criterion
          </button>
          <button type="button" className="btn btn-danger" disabled={resetting} onClick={handleResetDemo}>
            {resetting ? 'Resetting…' : 'Reset 60-Ticket Demo Dataset'}
          </button>
        </div>
      </div>

      {/* Governance Hierarchy & AI Engine Status */}
      <div className="grid-asymmetric">
        <section className="card">
          <div className="card-header">
            <div>
              <h3>AI Confidence Framework &amp; Risk Thresholds</h3>
              <p className="card-subtitle">
                Proposal Section 23: Auto Decision ({form.confidence_auto}–100%), AI Recommendation ({form.confidence_recommend}–{form.confidence_auto - 1}%), Human Review (&lt;{form.confidence_recommend}%).
              </p>
            </div>
          </div>

          <div className="grid-3" style={{ gap: 12 }}>
            <div>
              <label className="field-label" htmlFor="cfg-auto">Auto Decision Confidence (%)</label>
              <input
                id="cfg-auto"
                type="number"
                className="input mono"
                value={form.confidence_auto}
                onChange={(e) => setForm({ ...form, confidence_auto: Number(e.target.value) })}
              />
            </div>
            <div>
              <label className="field-label" htmlFor="cfg-rec">AI Recommendation Min (%)</label>
              <input
                id="cfg-rec"
                type="number"
                className="input mono"
                value={form.confidence_recommend}
                onChange={(e) => setForm({ ...form, confidence_recommend: Number(e.target.value) })}
              />
            </div>
            <div>
              <label className="field-label" htmlFor="cfg-samp">Medium-Risk Sampling (%)</label>
              <input
                id="cfg-samp"
                type="number"
                className="input mono"
                value={form.medium_sampling_pct}
                onChange={(e) => setForm({ ...form, medium_sampling_pct: Number(e.target.value) })}
              />
            </div>
            <div>
              <label className="field-label" htmlFor="cfg-crit">Critical Risk Threshold</label>
              <input
                id="cfg-crit"
                type="number"
                className="input mono"
                value={form.critical_risk_threshold}
                onChange={(e) => setForm({ ...form, critical_risk_threshold: Number(e.target.value) })}
              />
            </div>
            <div>
              <label className="field-label" htmlFor="cfg-high">High Risk Threshold</label>
              <input
                id="cfg-high"
                type="number"
                className="input mono"
                value={form.high_risk_threshold}
                onChange={(e) => setForm({ ...form, high_risk_threshold: Number(e.target.value) })}
              />
            </div>
            <div>
              <label className="field-label" htmlFor="cfg-med">Medium Risk Threshold</label>
              <input
                id="cfg-med"
                type="number"
                className="input mono"
                value={form.medium_risk_threshold}
                onChange={(e) => setForm({ ...form, medium_risk_threshold: Number(e.target.value) })}
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: 20, marginTop: 14, flexWrap: 'wrap', fontSize: 13 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={form.proactive_alerts_enabled}
                onChange={(e) => setForm({ ...form, proactive_alerts_enabled: e.target.checked })}
              />
              Enable Proactive Pre-Closure Monitoring Alerts (Agent 6)
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={form.auto_close_low_risk}
                onChange={(e) => setForm({ ...form, auto_close_low_risk: e.target.checked })}
              />
              Auto-Close Verified Low-Risk PASS Audits
            </label>
          </div>

          <div style={{ display: 'flex', gap: 10, marginTop: 18, flexWrap: 'wrap' }}>
            <button type="button" className="btn btn-secondary" disabled={saving} onClick={() => saveThresholds(false)}>
              Save Thresholds
            </button>
            <button type="button" className="btn btn-primary" disabled={saving} onClick={() => saveThresholds(true)}>
              {saving ? 'Re-Evaluating Fleet…' : 'Save & Re-Evaluate All Tickets'}
            </button>
          </div>
        </section>

        <section className="card stack-sm">
          <div>
            <h3>Governance Control Hierarchy</h3>
            <p className="card-subtitle">Proposal Section 22 — AI never overrides enterprise policy.</p>
          </div>
          {['1. Enterprise Policy (Policy Knowledge Base)', '2. Deterministic Rules Engine', '3. AI Interpretation & Evidence Extraction', '4. Explainable Evidence & Confidence Score', '5. Human Oversight & Audit Trail'].map((step) => (
            <div key={step} className="explain-row" style={{ fontWeight: 600, fontSize: 13 }}>
              {step}
            </div>
          ))}
          <div className="explain-row" style={{ marginTop: 6 }}>
            <div className="explain-row-label">Active AI Reasoning Engine</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
              <strong style={{ fontSize: 13 }}>{data.aiEngine.modelLabel}</strong>
              <DecisionBadge status={data.aiEngine.llmEnabled ? 'PASS' : 'REVIEW'} />
            </div>
            <span className="cell-sub">
              Set <code>LLM_API_KEY</code> in <code>backend/.env</code> to augment with an external enterprise LLM API.
            </span>
          </div>
        </section>
      </div>

      {/* INC / SR / CR Criteria Tables */}
      <div className="grid-3">
        {(['INC', 'SR', 'CR'] as const).map((tType) => (
          <section key={tType} className="card">
            <div className="card-header">
              <div>
                <h3>{tType} Audit Criteria</h3>
                <p className="card-subtitle">{(data.rules[tType] || []).length} configured rules</p>
              </div>
            </div>
            <div className="stack-sm">
              {(data.rules[tType] || []).map((rule) => (
                <div key={rule.criterionId} className="explain-row" style={{ opacity: rule.active ? 1 : 0.55 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                    <strong style={{ fontSize: 13 }}>{rule.criterionName}</strong>
                    <button
                      type="button"
                      className={`btn btn-sm ${rule.active ? 'btn-secondary' : 'btn-subtle'}`}
                      onClick={() => toggleRule(rule)}
                    >
                      {rule.active ? 'Active' : 'Disabled'}
                    </button>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>{rule.requirement}</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8, gap: 8 }}>
                    <span className="badge neutral">
                      {rule.method === 'deterministic' ? 'Rule Engine' : 'AI Reasoning'}
                    </span>
                    <label style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 12 }}>
                      Weight:
                      <input
                        type="number"
                        step="0.1"
                        min="0.2"
                        max="5"
                        defaultValue={rule.weight}
                        onBlur={(e) => updateRuleWeight(rule, Number(e.target.value))}
                        className="input mono"
                        style={{ width: 62, padding: '3px 6px' }}
                      />
                    </label>
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>

      {showAddRule ? (
        <div className="modal-backdrop" onClick={() => setShowAddRule(false)} role="dialog" aria-modal="true">
          <form className="modal-card" onClick={(e) => e.stopPropagation()} onSubmit={handleCreateRule}>
            <div className="modal-head">
              <div>
                <span className="breadcrumb">AUDIT RULES ENGINE</span>
                <h3 style={{ marginTop: 4 }}>Add Custom Governance Criterion</h3>
              </div>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowAddRule(false)}>Close</button>
            </div>
            <div className="grid-2">
              <div>
                <label className="field-label" htmlFor="nr-type">Ticket Type</label>
                <select id="nr-type" className="select" value={ruleType} onChange={(e) => setRuleType(e.target.value as 'INC' | 'SR' | 'CR')}>
                  <option value="CR">CR — Change Request</option>
                  <option value="INC">INC — Incident</option>
                  <option value="SR">SR — Service Request</option>
                </select>
              </div>
              <div>
                <label className="field-label" htmlFor="nr-method">Evaluation Method</label>
                <select id="nr-method" className="select" value={ruleMethod} onChange={(e) => setRuleMethod(e.target.value as 'deterministic' | 'ai')}>
                  <option value="ai">AI Reasoning</option>
                  <option value="deterministic">Deterministic Rules Engine</option>
                </select>
              </div>
            </div>
            <div>
              <label className="field-label" htmlFor="nr-name">Criterion Name</label>
              <input id="nr-name" className="input" required value={ruleName} onChange={(e) => setRuleName(e.target.value)} placeholder="e.g. Security Scan Evidence" />
            </div>
            <div className="grid-2">
              <div>
                <label className="field-label" htmlFor="nr-req">Requirement</label>
                <input id="nr-req" className="input" required value={ruleReq} onChange={(e) => setRuleReq(e.target.value)} />
              </div>
              <div>
                <label className="field-label" htmlFor="nr-wt">Score Weight</label>
                <input id="nr-wt" type="number" step="0.1" className="input mono" value={ruleWeight} onChange={(e) => setRuleWeight(Number(e.target.value))} />
              </div>
            </div>
            <div>
              <label className="field-label" htmlFor="nr-rule">Policy Rule Statement</label>
              <textarea id="nr-rule" className="textarea" required value={ruleText} onChange={(e) => setRuleText(e.target.value)} placeholder="Describe what evidence satisfies this criterion…" />
            </div>
            <div className="modal-foot">
              <button type="button" className="btn btn-secondary" onClick={() => setShowAddRule(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary">Add Criterion</button>
            </div>
          </form>
        </div>
      ) : null}
    </div>
  )
}
