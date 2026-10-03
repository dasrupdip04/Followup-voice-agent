import React, {useState} from 'react'
import { Customer, CustomerContext } from '../types'
import { startCall } from '../services/callService'

/*
  CustomerDetail
  - Shows customer profile, loans, payments and previous calls.
  - Adds a "Generate Call Brief" action which calls the backend StartCall endpoint.
    The StartCall endpoint returns a `call_id` and `strategy` (pre-call analysis).
  - We store the returned `strategy` and `call_id` and surface a dedicated
    "Open Call Console" button to actually open the live/text call console.

  Rationale:
  - This keeps pre-call analysis generation tied to the backend Phase 6 logic,
    ensures the strategy is produced once per call, and prevents repeatedly
    calling the LLM for every UI component.
*/

export default function CustomerDetail({customer,context,onStartCall}:{customer:Customer,context:CustomerContext,onStartCall:(id:number)=>void}){
  const [callInfo,setCallInfo] = useState<{call_id:number, strategy:any}|null>(null)
  const [loading,setLoading] = useState(false)

  async function handleGenerateBrief(){
    setLoading(true)
    try{
      const res = await startCall(customer.id)
      // expected: { call_id, customer, strategy }
      setCallInfo({call_id: res.call_id, strategy: res.strategy})
    }catch(e:any){
      console.error('failed to generate brief',e)
      alert('Failed to generate call brief')
    }finally{setLoading(false)}
  }

  function openConsole(){
    if(!callInfo) return
    onStartCall(callInfo.call_id, callInfo.strategy)
  }

  return (
    <div className="card">
      <h3>{customer.full_name}</h3>
      <div className="muted">{customer.customer_number} • {customer.city} • {customer.preferred_language}</div>
      <hr />
      <h4>Loans</h4>
      {context.loans.map((l:any)=> (
        <div key={l.id} className="list-item">
          <div>
            <div><strong>{l.loan_number}</strong> • {l.loan_type}</div>
            <div className="muted">Due {l.due_date} • {l.status}</div>
          </div>
          <div className="badge">{l.outstanding_amount}</div>
        </div>
      ))}

      <h4>Payment History</h4>
      {context.payments.map((p:any)=> (
        <div key={p.id} className="list-item">
          <div>{new Date(p.payment_date).toLocaleString()} • {p.payment_method}</div>
          <div className="muted">{p.amount}</div>
        </div>
      ))}

      <h4>Previous Calls</h4>
      {context.previous_calls.map((c:any)=> (
        <div key={c.id} className="list-item">
          <div>{new Date(c.started_at).toLocaleString()}</div>
          <div className="muted">{c.status} • {c.duration_seconds ?? '-' }s</div>
        </div>
      ))}

      <div style={{marginTop:12, display:'flex', gap:8}}>
        <button className="btn" onClick={handleGenerateBrief} disabled={loading}>{loading? 'Generating...' : 'Generate Call Brief'}</button>
        {callInfo && (
          <>
            <button className="btn outline" onClick={openConsole}>Open Call Console</button>
          </>
        )}
      </div>

      {callInfo && (
        <div style={{marginTop:16}} className="card muted">
          <h4>Call Brief</h4>
          <div><strong>Objective:</strong> {callInfo.strategy?.objective ?? '—'}</div>
          <div style={{marginTop:8}}><strong>Recommended Opening:</strong><div className="muted">{callInfo.strategy?.opening ?? '—'}</div></div>
          <div style={{marginTop:8}}><strong>Suggested Strategy:</strong><div className="muted">{callInfo.strategy?.strategy_text ?? '—'}</div></div>
        </div>
      )}
    </div>
  )
}
