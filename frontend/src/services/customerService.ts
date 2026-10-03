import api from './api'
import { Customer, CustomerContext, CustomerListResponse } from '../types'

export async function listCustomers(limit=20, offset=0){
  const res = await api.get('/customers', {params:{limit,offset}})
  return res.data as CustomerListResponse
}

export async function getCustomer(customer_id:number){
  const res = await api.get(`/customers/${customer_id}`)
  return res.data as Customer
}

export async function getCustomerContext(customer_id:number){
  const res = await api.get(`/customers/${customer_id}/context`)
  return res.data as CustomerContext
}
