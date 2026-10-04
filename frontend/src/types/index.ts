export type Customer = {
  id: number
  customer_number: string
  full_name: string
  phone_number: string
  email: string
  date_of_birth: string
  city: string
  bank_name: string
  preferred_language: string
  created_at: string
}

export type Loan = {
  id: number
  customer_id: number
  loan_number: string
  loan_type: string
  principal_amount: string
  outstanding_amount: string
  interest_rate: string
  emi_amount: string
  due_date: string
  status: string
  created_at: string
}

export type Payment = {
  id: number
  loan_id: number
  amount: string
  payment_date: string
  payment_method: string
  status: string
  transaction_reference: string
  created_at: string
}

export type CallOutcome = {
  id: number
  call_id: number
  outcome_type: string
  promised_amount: string | null
  promised_date: string | null
  notes: string | null
  created_at: string
}

export type CallMetric = {
  id: number
  call_id: number
  total_turns: number
  user_turns: number
  agent_turns: number
  avg_response_latency_ms: string | null
  avg_stt_latency_ms: string | null
  avg_llm_latency_ms: string | null
  avg_tts_latency_ms: string | null
  user_interruptions: number
  agent_interruptions: number
  tool_calls: number
  tool_failures: number
  tokens_input: number
  tokens_output: number
  created_at: string
}

export type PreviousCall = {
  id: number
  customer_id: number
  started_at: string
  ended_at: string | null
  duration_seconds: number | null
  status: string
  agent_id: string
  created_at: string
  outcome: CallOutcome | null
  metric: CallMetric | null
}

export type CustomerContext = {
  customer: Customer
  loans: Loan[]
  payments: Payment[]
  previous_calls: PreviousCall[]
}

export type CustomerListResponse = {
  items: Customer[]
  total: number
  limit: number
  offset: number
}

export type CallStrategy = Record<string, unknown> & {
  objective?: string
  priority_issue?: string
  customer_risk_context?: string
  recommended_opening?: string
  key_facts_to_mention?: string[]
  questions_to_ask?: string[]
  possible_objections?: string[]
  recommended_response_style?: string
  payment_commitment_goal?: string
  escalation_conditions?: string[]
  topics_to_avoid?: string[]
}

export type StartCallResponse = {
  call_id: number
  customer: Record<string, unknown>
  strategy: CallStrategy
}

export type ToolCallResult = {
  tool: string
  success: boolean
  result?: unknown
  error?: string
}

export type CallMessageResponse = {
  call_id: number
  response: string
  turn_number: number
  tool_calls: ToolCallResult[]
}

export type EndCallResponse = {
  call_id: number
  status: string
  outcome: {
    outcome?: string
    outcome_type?: string
    summary?: string
    notes?: string | null
    payment_commitment?: string | null
    commitment_amount?: string | number | null
    commitment_date?: string | null
    reason_for_nonpayment?: string | null
    objection?: string | null
    customer_sentiment?: string
    cooperation_level?: string
    promise_to_pay?: boolean
    follow_up_required?: boolean
    escalation_required?: boolean
    key_events?: string[]
  }
  metrics: {
    duration_seconds?: number | null
    total_turns?: number
    tool_calls?: number
    user_turns?: number
    agent_turns?: number
    tool_failures?: number
  }
}

export type VoiceJoinResponse = {
  call_id: number
  room_name: string
  livekit_url: string
  token: string
}
