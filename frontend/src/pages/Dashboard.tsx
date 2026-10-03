import React, {useEffect, useState} from 'react'
import { listCustomers, getCustomerContext } from '../services/customerService'
import { Customer } from '../types'
import CallScreen from './CallScreen'
import CustomerDetail from './CustomerDetail'

export default function Dashboard(){
  const [customers,setCustomers] = useState<Customer[]>([])
  const [selected,setSelected] = useState<Customer|undefined>()
  const [context,setContext] = useState<any>(null)
  const [activeCall,setActiveCall] = useState<{call_id:number, strategy?:any}|undefined>()
  const [search,setSearch] = useState('')

  useEffect(()=>{fetchList()},[])

  async function fetchList(){
    const res = await listCustomers()
    setCustomers(res.items)
  }

  async function selectCustomer(c:Customer){
    setSelected(c)
    setContext(null)
    const ctx = await getCustomerContext(c.id)
    setContext(ctx)
  }

  function filteredCustomers(){
    if(!search) return customers
    const s = search.toLowerCase()
    return customers.filter(c=> (c.full_name||'').toLowerCase().includes(s) || (c.customer_number||'').toLowerCase().includes(s) )
  }

  return (
    <div className="grid">
        <div className="card">
          <h3>Customers</h3>
          <div style={{marginBottom:8}}>
            <input className="input" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search name or customer number" />
          </div>
          <div>
          {filteredCustomers().map(c=> (
            <div key={c.id} className="list-item" onClick={()=>selectCustomer(c)} style={{cursor:'pointer'}}>
              <div>
                <div><strong>{c.full_name}</strong></div>
                <div className="muted">{c.city} • {c.customer_number}</div>
              </div>
              <div className="badge">{c.id}</div>
            </div>
          ))}
        </div>
      </div>

      <div>
        {!selected && <div className="card"><h3>Customer Overview</h3><div className="muted">Select a customer to inspect details</div></div>}
        {selected && context && <CustomerDetail customer={selected} context={context} onStartCall={(call_id:number, strategy?:any)=>setActiveCall({call_id, strategy})} />}
        {selected && !context && <div className="card">Loading...</div>}
      </div>

      <div>
        <div className="card">
          <h3>Agent Activity</h3>
          <div className="muted">Text Test Mode available on call screen.</div>
        </div>
        <div style={{height:16}} />
        <div className="card">
          <h3>Call Console</h3>
          {activeCall ? <CallScreen callId={activeCall.call_id} strategy={activeCall.strategy} /> : <div className="muted">Generate a call brief and open console</div>}
        </div>
      </div>
    </div>
  )
}
