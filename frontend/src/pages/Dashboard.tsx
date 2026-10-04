import React, { useEffect, useMemo, useState } from 'react'
import { getCustomerContext, listCustomers } from '../services/customerService'
import { Customer, CustomerContext, StartCallResponse, VoiceJoinResponse } from '../types'
import CallScreen from './CallScreen'
import CustomerDetail from './CustomerDetail'

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  return 'An unexpected error occurred.'
}

export default function Dashboard() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [total, setTotal] = useState(0)
  const [selected, setSelected] = useState<Customer | undefined>()
  const [context, setContext] = useState<CustomerContext | null>(null)
  const [activeCall, setActiveCall] = useState<{ call: StartCallResponse; voice: VoiceJoinResponse; ended: boolean } | undefined>()
  const [search, setSearch] = useState('')
  const [listLoading, setListLoading] = useState(true)
  const [listError, setListError] = useState('')
  const [contextLoading, setContextLoading] = useState(false)
  const [contextError, setContextError] = useState('')

  useEffect(() => {
    let cancelled = false
    listCustomers().then((result) => {
      if (cancelled) return
      setCustomers(result.items)
      setTotal(result.total)
    }).catch((error: unknown) => {
      if (!cancelled) setListError(errorMessage(error))
    }).finally(() => {
      if (!cancelled) setListLoading(false)
    })
    return () => { cancelled = true }
  }, [])

  const filteredCustomers = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) return customers
    return customers.filter((customer) => [customer.full_name, customer.customer_number, customer.phone_number, customer.city, customer.preferred_language]
      .some((field) => field?.toLowerCase().includes(query)))
  }, [customers, search])

  async function selectCustomer(customer: Customer) {
    setSelected(customer)
    setContext(null)
    setContextError('')
    setContextLoading(true)
    try {
      setContext(await getCustomerContext(customer.id))
    } catch (error) {
      setContextError(errorMessage(error))
    } finally {
      setContextLoading(false)
    }
  }

  return (
    <div className="grid">
      <section className="card" aria-labelledby="customers-title">
        <h3 id="customers-title">Customers <span className="muted">({total})</span></h3>
        <label className="muted" htmlFor="customer-search">Search by name, number, phone, city, or language</label>
        <input id="customer-search" className="input" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search customers" />
        {listLoading && <p role="status">Loading customers…</p>}
        {listError && <p className="error" role="alert">Could not load customers: {listError}</p>}
        {!listLoading && !listError && filteredCustomers.length === 0 && <p className="muted">{customers.length ? 'No customers match this search.' : 'No customers were returned by the API.'}</p>}
        <div className="customer-list">
          {filteredCustomers.map((customer) => (
            <button type="button" key={customer.id} className={`customer-row${selected?.id === customer.id ? ' selected' : ''}`} onClick={() => selectCustomer(customer)}>
              <span className="customer-row-main">
                <strong>{customer.full_name}</strong>
                <span>{customer.customer_number} · {customer.phone_number}</span>
                <span>{customer.city} · {customer.preferred_language}</span>
              </span>
              <span className="badge">#{customer.id}</span>
            </button>
          ))}
        </div>
      </section>

      <section>
        {!selected && <div className="card"><h3>Customer Overview</h3><p className="muted">Select a customer to load their profile and account context.</p></div>}
        {selected && contextLoading && <div className="card" role="status">Loading context for {selected.full_name}…</div>}
        {selected && contextError && <div className="card error" role="alert">Could not load customer context: {contextError}</div>}
        {selected && context && <CustomerDetail key={selected.id} customer={context.customer} context={context} callInProgress={Boolean(activeCall && !activeCall.ended)} onStartCall={(call, voice) => setActiveCall({ call, voice, ended: false })} />}
      </section>

      <section className="card voice-panel">
        {activeCall && selected && context ? <CallScreen
          key={activeCall.call.call_id}
          callId={activeCall.call.call_id}
          strategy={activeCall.call.strategy}
          customer={context.customer}
          context={context}
          voice={activeCall.voice}
          onCallEnded={async () => {
            const refreshed = await getCustomerContext(context.customer.id)
            setContext(refreshed)
            setActiveCall((current) => current ? { ...current, ended: true } : current)
          }}
        /> : <div className="voice-empty"><p className="eyebrow">Customer call</p><h3>Start a call with the selected customer</h3><p className="muted">The HDFC Bank AI Recovery Agent will join, speak first, and listen for the customer’s response.</p></div>}
      </section>
    </div>
  )
}
