import api from './api'
import { Customer, CustomerContext, CustomerListResponse } from '../types'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function validateCustomer(value: unknown): Customer {
  if (!isRecord(value) || typeof value.id !== 'number' || typeof value.full_name !== 'string' || typeof value.customer_number !== 'string') {
    throw new Error('The customers API returned a customer with an unexpected shape.')
  }
  return value as Customer
}

export async function listCustomers(limit = 100, offset = 0): Promise<CustomerListResponse> {
  const { data } = await api.get<unknown>('/customers', { params: { limit, offset } })
  if (!isRecord(data) || !Array.isArray(data.items) || typeof data.total !== 'number' || typeof data.limit !== 'number' || typeof data.offset !== 'number') {
    throw new Error('The customers API response did not match { items, total, limit, offset }.')
  }
  return { items: data.items.map(validateCustomer), total: data.total, limit: data.limit, offset: data.offset }
}

export async function getCustomer(customerId: number): Promise<Customer> {
  const { data } = await api.get<unknown>(`/customers/${customerId}`)
  return validateCustomer(data)
}

export async function getCustomerContext(customerId: number): Promise<CustomerContext> {
  const { data } = await api.get<unknown>(`/customers/${customerId}/context`)
  if (!isRecord(data) || !Array.isArray(data.loans) || !Array.isArray(data.payments) || !Array.isArray(data.previous_calls)) {
    throw new Error('The customer context API returned an unexpected shape.')
  }
  return {
    customer: validateCustomer(data.customer),
    loans: data.loans as CustomerContext['loans'],
    payments: data.payments as CustomerContext['payments'],
    previous_calls: data.previous_calls as CustomerContext['previous_calls'],
  }
}
