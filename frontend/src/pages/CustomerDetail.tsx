import React, { useEffect, useRef, useState } from 'react'
import { CallStrategy, Customer, CustomerContext, StartCallResponse, VoiceJoinResponse } from '../types'
import { startCall, startVoiceSession } from '../services/callService'

function value(strategy: CallStrategy, key: keyof CallStrategy): React.ReactNode {
  const entry = strategy[key]
  if (Array.isArray(entry)) return <ul>{entry.map((item, index) => <li key={index}>{String(item)}</li>)}</ul>
  if (typeof entry === 'string' || typeof entry === 'number') return String(entry)
  return 'Not provided'
}

export default function CustomerDetail({ customer, context, onStartCall, callInProgress }: { customer: Customer; context: CustomerContext; onStartCall: (call: StartCallResponse, voice: VoiceJoinResponse) => void; callInProgress: boolean }) {
  const [callInfo, setCallInfo] = useState<StartCallResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const hadActiveCall = useRef(false)

  useEffect(() => {
    if (hadActiveCall.current && !callInProgress) setCallInfo(null)
    hadActiveCall.current = callInProgress
  }, [callInProgress])

  async function handleStartCall() {
    setLoading(true)
    setError('')
    try {
      const startedCall = callInfo ?? await startCall(customer.id)
      setCallInfo(startedCall)
      const voice = await startVoiceSession(startedCall.call_id)
      onStartCall(startedCall, voice)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not connect the customer call.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <div className="section-heading"><div><p className="eyebrow">Customer profile</p><h2>{customer.full_name}</h2></div><span className="badge">{customer.customer_number}</span></div>
      <dl className="detail-grid">
        <div><dt>Customer ID</dt><dd>{customer.id}</dd></div><div><dt>Phone</dt><dd>{customer.phone_number}</dd></div>
        <div><dt>Email</dt><dd>{customer.email}</dd></div><div><dt>City</dt><dd>{customer.city}</dd></div>
        <div><dt>Preferred language</dt><dd>{customer.preferred_language}</dd></div><div><dt>Bank</dt><dd>{customer.bank_name}</dd></div>
      </dl>

      <h3>Loans ({context.loans.length})</h3>
      {context.loans.length === 0 && <p className="muted">No loans returned.</p>}
      {context.loans.map((loan) => <article className="data-row" key={loan.id}>
        <div><strong>{loan.loan_number} · {loan.loan_type}</strong><p className="muted">Due {loan.due_date} · {loan.status} · EMI {loan.emi_amount}</p></div>
        <div className="amount">Outstanding<br />{loan.outstanding_amount}</div>
      </article>)}

      <h3>Payment history ({context.payments.length})</h3>
      {context.payments.length === 0 && <p className="muted">No payments returned.</p>}
      {context.payments.map((payment) => <article className="data-row" key={payment.id}>
        <div><strong>{payment.payment_date}</strong><p className="muted">Loan #{payment.loan_id} · {payment.payment_method} · {payment.status}</p></div>
        <div className="amount">{payment.amount}</div>
      </article>)}

      <h3>Previous calls ({context.previous_calls.length})</h3>
      {context.previous_calls.length === 0 && <p className="muted">No previous calls returned.</p>}
      {context.previous_calls.map((call) => <article className="data-row" key={call.id}>
        <div><strong>Call #{call.id} · {call.status}</strong><p className="muted">{call.started_at} · {call.duration_seconds ?? 'Duration unavailable'} seconds</p>
          {call.outcome && <p className="muted">Outcome: {call.outcome.outcome_type}{call.outcome.notes ? ` · ${call.outcome.notes}` : ''}</p>}
        </div>
        {call.metric && <div className="amount">{call.metric.total_turns} turns<br />{call.metric.tool_calls} tool calls</div>}
      </article>)}

      <div className="actions"><button className="btn" onClick={handleStartCall} disabled={loading || callInProgress}>{loading ? (callInfo ? 'Connecting call…' : 'Preparing call…') : callInfo ? 'Retry Call Connection' : 'Start Call'}</button>
      </div>
      {error && <p className="error" role="alert">Call setup failed: {error}</p>}
      {callInfo && <section className="brief" aria-label="Call brief">
        <p className="eyebrow">Call brief · Call #{callInfo.call_id}</p>
        <h3>Customer situation</h3>
        <p><strong>Priority issue:</strong> {value(callInfo.strategy, 'priority_issue')}</p>
        <p><strong>Risk context:</strong> {value(callInfo.strategy, 'customer_risk_context')}</p>
        <p><strong>Objective:</strong> {value(callInfo.strategy, 'objective')}</p>
        <p><strong>Recommended opening:</strong> {value(callInfo.strategy, 'recommended_opening')}</p>
        <p><strong>Response style:</strong> {value(callInfo.strategy, 'recommended_response_style')}</p>
        <p><strong>Payment commitment goal:</strong> {value(callInfo.strategy, 'payment_commitment_goal')}</p>
        <p><strong>Key facts</strong>{value(callInfo.strategy, 'key_facts_to_mention')}</p>
        <p><strong>Questions</strong>{value(callInfo.strategy, 'questions_to_ask')}</p>
        <p><strong>Possible objections</strong>{value(callInfo.strategy, 'possible_objections')}</p>
        <p><strong>Escalation conditions</strong>{value(callInfo.strategy, 'escalation_conditions')}</p>
        <p><strong>Topics to avoid</strong>{value(callInfo.strategy, 'topics_to_avoid')}</p>
      </section>}
    </div>
  )
}
