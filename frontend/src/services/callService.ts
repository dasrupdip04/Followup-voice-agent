import api from './api'

export async function startCall(customer_id:number){
  const res = await api.post('/api/v1/agent/calls/start', {customer_id})
  return res.data
}

export async function sendMessage(call_id:number, message:string){
  const res = await api.post(`/api/v1/agent/calls/${call_id}/message`, {message})
  return res.data
}

export async function endCall(call_id:number){
  const res = await api.post(`/api/v1/agent/calls/${call_id}/end`)
  return res.data
}
