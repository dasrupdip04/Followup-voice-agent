import api from './api'
import axios from 'axios'
import { CallMessageResponse, EndCallResponse, StartCallResponse, VoiceJoinResponse } from '../types'

export async function startCall(customer_id: number): Promise<StartCallResponse> {
  const res = await api.post<StartCallResponse>('/api/v1/agent/calls/start', { customer_id })
  return res.data
}

export async function sendMessage(call_id: number, message: string): Promise<CallMessageResponse> {
  const res = await api.post<CallMessageResponse>(`/api/v1/agent/calls/${call_id}/message`, { message })
  return res.data
}

export async function endCall(call_id: number): Promise<EndCallResponse> {
  const res = await api.post<EndCallResponse>(`/api/v1/agent/calls/${call_id}/end`)
  return res.data
}

export async function startVoiceSession(call_id: number): Promise<VoiceJoinResponse> {
  try {
    const res = await api.post<VoiceJoinResponse>(`/api/v1/agent/calls/${call_id}/voice`)
    return res.data
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail ?? error.message)
    }
    throw error
  }
}
