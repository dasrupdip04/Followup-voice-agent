export type Customer = {
  id:number
  customer_number:string
  full_name:string
  city?:string
  preferred_language?:string
}

export type Loan = {
  id:number
  loan_number:string
  loan_type:string
  outstanding_amount:number
  due_date:string
  status:string
}

export type Payment = {
  id:number
  loan_id:number
  amount:number
  payment_date:string
  payment_method:string
  status:string
}

export type PreviousCall = {id:number, started_at:string, duration_seconds:number|null, status:string}

export type CustomerContext = {
  customer: Customer
  loans: Loan[]
  payments: Payment[]
  previous_calls: PreviousCall[]
}

export type CustomerListResponse = {
  items: Customer[]
  total:number
  limit:number
  offset:number
}
