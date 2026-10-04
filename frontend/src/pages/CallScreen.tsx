import React, { useEffect, useMemo, useRef, useState } from 'react'
import { createLocalAudioTrack, Room, RoomEvent, Track, TranscriptionSegment } from 'livekit-client'
import { endCall } from '../services/callService'
import { getCustomerContext } from '../services/customerService'
import { CallStrategy, Customer, CustomerContext, EndCallResponse, VoiceJoinResponse } from '../types'

type TranscriptItem = { id: string; speaker: 'CUSTOMER' | 'AGENT'; text: string }
type ConnectionState = 'Connecting' | 'Connected' | 'Agent speaking' | 'Listening' | 'Processing' | 'Completed'

function isAgent(identity: string) {
  return identity.startsWith('agent-') || identity.includes('followup-voice-agent')
}

function formatMoney(amount: string | number | undefined) {
  if (amount === undefined) return 'Not available'
  const numeric = Number(amount)
  return Number.isFinite(numeric) ? `₹${numeric.toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : String(amount)
}

export default function CallScreen({
  callId,
  strategy,
  customer,
  context,
  voice,
  onCallEnded,
}: {
  callId: number
  strategy: CallStrategy
  customer: Customer
  context: CustomerContext
  voice: VoiceJoinResponse
  onCallEnded: () => Promise<void>
}) {
  const [connectionState, setConnectionState] = useState<ConnectionState>('Connecting')
  const [connected, setConnected] = useState(false)
  const [agentConnected, setAgentConnected] = useState(false)
  const [microphoneOn, setMicrophoneOn] = useState(false)
  const [audioBlocked, setAudioBlocked] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [transcript, setTranscript] = useState<TranscriptItem[]>([])
  const [endedResult, setEndedResult] = useState<EndCallResponse | null>(null)
  const [ending, setEnding] = useState(false)
  const [error, setError] = useState('')
  const roomRef = useRef<Room | null>(null)
  const connectionStateRef = useRef(connectionState)
  const agentConnectedRef = useRef(agentConnected)
  const micTrackRef = useRef<Awaited<ReturnType<typeof createLocalAudioTrack>> | null>(null)
  const audioElementsRef = useRef<Map<string, HTMLMediaElement>>(new Map())
  const processingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  connectionStateRef.current = connectionState
  agentConnectedRef.current = agentConnected

  const focusLoan = useMemo(() => {
    const match = String(strategy.priority_issue ?? '').match(/[A-Z]{2}-\d{4}-\d{3}/)
    return (match && context.loans.find((loan) => loan.loan_number === match[0]))
      ?? context.loans.find((loan) => loan.status.toUpperCase() === 'OVERDUE')
      ?? context.loans[0]
  }, [context.loans, strategy.priority_issue])

  useEffect(() => {
    let disposed = false
    const room = new Room({ adaptiveStream: true, dynacast: true })
    roomRef.current = room

    function markAgentConnected() {
      agentConnectedRef.current = true
      setAgentConnected(true)
      setConnectionState((current) => current === 'Agent speaking' ? current : 'Connected')
    }

    room.on(RoomEvent.ParticipantConnected, (participant) => {
      if (isAgent(participant.identity)) markAgentConnected()
    })
    room.on(RoomEvent.TrackSubscribed, (track, _publication, participant) => {
      if (track.kind !== Track.Kind.Audio || !isAgent(participant.identity)) return
      const element = track.attach()
      element.autoplay = true
      element.muted = false
      if (element instanceof HTMLAudioElement) element.playsInline = true
      document.body.appendChild(element)
      audioElementsRef.current.set(track.sid, element)
      void element.play().catch(() => setAudioBlocked(true))
      markAgentConnected()
    })
    room.on(RoomEvent.TrackUnsubscribed, (track) => {
      const element = audioElementsRef.current.get(track.sid)
      if (element) {
        track.detach(element)
        element.remove()
        audioElementsRef.current.delete(track.sid)
      }
    })
    room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
      const agentTalking = speakers.some((participant) => isAgent(participant.identity))
      const customerTalking = speakers.some((participant) => participant.identity === room.localParticipant.identity)
      if (agentTalking) {
        if (processingTimeoutRef.current) clearTimeout(processingTimeoutRef.current)
        setConnectionState('Agent speaking')
      } else if (customerTalking) {
        setConnectionState('Listening')
      } else if (connectionStateRef.current === 'Processing') {
        // Keep the processing state until the response arrives or the timer expires.
      } else if (agentConnectedRef.current) {
        setConnectionState('Listening')
      }
    })
    room.on(RoomEvent.TranscriptionReceived, (segments: TranscriptionSegment[], participant) => {
      const speaker: TranscriptItem['speaker'] = participant?.identity === room.localParticipant.identity ? 'CUSTOMER' : 'AGENT'
      const finalized = segments.filter((segment) => segment.final && segment.text.trim())
      if (!finalized.length) return
      setTranscript((current) => {
        const next = [...current]
        for (const segment of finalized) {
          if (!next.some((item) => item.id === segment.id)) next.push({ id: segment.id, speaker, text: segment.text.trim() })
        }
        return next
      })
      if (speaker === 'CUSTOMER') {
        setConnectionState('Processing')
        if (processingTimeoutRef.current) clearTimeout(processingTimeoutRef.current)
        processingTimeoutRef.current = setTimeout(() => setConnectionState('Listening'), 12000)
      }
    })
    room.on(RoomEvent.Disconnected, () => {
      if (!disposed) setConnected(false)
    })

    async function connect() {
      try {
        await room.connect(voice.livekit_url, voice.token, { autoSubscribe: true })
        if (disposed) return
        setConnected(true)
        await room.startAudio().catch(() => setAudioBlocked(true))
        const microphone = await createLocalAudioTrack({
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        })
        if (disposed) {
          microphone.stop()
          return
        }
        micTrackRef.current = microphone
        await room.localParticipant.publishTrack(microphone)
        setMicrophoneOn(true)
        setConnectionState('Connected')
        if ([...room.remoteParticipants.values()].some((participant) => isAgent(participant.identity))) markAgentConnected()
      } catch (reason) {
        if (!disposed) {
          setConnectionState('Connecting')
          setError(reason instanceof Error ? reason.message : 'Could not connect to the voice call.')
        }
      }
    }

    void connect()
    const durationTimer = window.setInterval(() => setElapsedSeconds((seconds) => seconds + 1), 1000)
    return () => {
      disposed = true
      window.clearInterval(durationTimer)
      if (processingTimeoutRef.current) clearTimeout(processingTimeoutRef.current)
      audioElementsRef.current.forEach((element) => element.remove())
      audioElementsRef.current.clear()
      micTrackRef.current?.stop()
      micTrackRef.current = null
      void room.disconnect()
      room.removeAllListeners()
    }
  }, [voice.livekit_url, voice.token])

  async function toggleMicrophone() {
    const track = micTrackRef.current
    if (!track) return
    try {
      if (microphoneOn) await track.mute()
      else await track.unmute()
      setMicrophoneOn(!microphoneOn)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not change microphone state.')
    }
  }

  async function enableAudio() {
    try {
      await roomRef.current?.startAudio()
      await Promise.all([...audioElementsRef.current.values()].map((element) => element.play()))
      setAudioBlocked(false)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Browser audio playback is blocked.')
    }
  }

  async function handleEndCall() {
    if (ending || endedResult) return
    setEnding(true)
    setError('')
    try {
      await micTrackRef.current?.mute()
      const result = await endCall(callId)
      setEndedResult(result)
      setConnectionState('Completed')
      await roomRef.current?.disconnect()
      await onCallEnded()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not end the call.')
    } finally {
      setEnding(false)
    }
  }

  const storedCall = context.previous_calls.find((call) => call.id === callId)
  const persistedMetric = storedCall?.metric
  const outcome = endedResult?.outcome
  const outcomeName = outcome?.outcome ?? outcome?.outcome_type ?? storedCall?.outcome?.outcome_type ?? 'Not available'
  const summary = outcome?.summary ?? outcome?.notes ?? storedCall?.outcome?.notes ?? 'No summary was returned.'
  const duration = endedResult?.metrics.duration_seconds ?? storedCall?.duration_seconds ?? elapsedSeconds

  return <div className="voice-call" aria-label="Customer voice call">
    {!endedResult ? <>
      <header className="voice-call-header">
        <div>
          <p className="eyebrow">{connected ? 'Active call' : 'Incoming call'}</p>
          <h2>{customer.bank_name} AI Recovery Agent is calling you</h2>
          <p className="muted">{customer.full_name} · Call #{callId}</p>
        </div>
        <span className={`status-pill ${connected ? 'active' : ''}`}>{connectionState}</span>
      </header>
      <div className="voice-agent-card">
        <div className={`voice-orb ${connectionState === 'Agent speaking' ? 'speaking' : ''}`} aria-hidden="true"><span /></div>
        <div><strong>{customer.bank_name} AI Recovery Agent</strong><p>{agentConnected ? connectionState : 'Connecting to your call…'}</p></div>
      </div>
      <div className="voice-customer-facts">
        <div><span>Customer</span><strong>{customer.full_name}</strong></div>
        <div><span>Bank</span><strong>{customer.bank_name}</strong></div>
        <div><span>Account</span><strong>{focusLoan ? `${focusLoan.loan_type} · ${focusLoan.loan_number}` : 'No loan returned'}</strong></div>
        <div><span>Outstanding</span><strong>{formatMoney(focusLoan?.outstanding_amount)}</strong></div>
        <div><span>Duration</span><strong>{Math.floor(elapsedSeconds / 60)}:{String(elapsedSeconds % 60).padStart(2, '0')}</strong></div>
      </div>
      {!agentConnected && <p className="voice-note" role="status">Waiting for the AI agent to join the room…</p>}
      {audioBlocked && <button className="btn outline" onClick={enableAudio}>Enable call audio</button>}
      <div className="voice-controls">
        <button className={`btn ${microphoneOn ? 'outline' : 'danger'}`} type="button" onClick={toggleMicrophone} disabled={!connected || !micTrackRef.current}>
          {microphoneOn ? 'Microphone on' : 'Microphone off'}
        </button>
        <button className="btn danger" type="button" onClick={handleEndCall} disabled={ending || !connected}>
          {ending ? 'Ending call…' : 'End Call'}
        </button>
      </div>
      {error && <p className="error" role="alert">Voice call error: {error}</p>}
      {transcript.length > 0 && <section className="voice-transcript"><h3>Live transcript</h3>{transcript.map((item) => <p key={item.id}><strong>{item.speaker === 'CUSTOMER' ? customer.full_name : 'AI Recovery Agent'}:</strong> {item.text}</p>)}</section>}
    </> : <>
      <header className="voice-call-header"><div><p className="eyebrow">After Call</p><h2>Call with {customer.full_name} ended</h2></div><span className="status-pill complete">Completed</span></header>
      <div className="after-call-grid">
        <div><span>Outcome</span><strong>{outcomeName}</strong></div>
        <div><span>Duration</span><strong>{duration ?? 'Not available'} sec</strong></div>
        <div><span>Total turns</span><strong>{persistedMetric?.total_turns ?? endedResult.metrics.total_turns ?? 'Not available'}</strong></div>
        <div><span>Customer turns</span><strong>{persistedMetric?.user_turns ?? endedResult.metrics.user_turns ?? 'Not available'}</strong></div>
        <div><span>Agent turns</span><strong>{persistedMetric?.agent_turns ?? endedResult.metrics.agent_turns ?? 'Not available'}</strong></div>
        <div><span>Tool calls / failures</span><strong>{persistedMetric ? `${persistedMetric.tool_calls} / ${persistedMetric.tool_failures}` : `${endedResult.metrics.tool_calls ?? 0} / ${endedResult.metrics.tool_failures ?? 'Not available'}`}</strong></div>
      </div>
      <section className="after-call-section"><h3>Call summary</h3><p>{summary}</p>
        {outcome?.key_events?.length ? <><h4>Key events</h4><ul>{outcome.key_events.map((event, index) => <li key={index}>{event}</li>)}</ul></> : null}
        <p><strong>Follow-up requested:</strong> {outcome?.follow_up_required === undefined ? 'Not available' : outcome.follow_up_required ? 'Yes' : 'No'}</p>
        <p><strong>Payment commitment:</strong> {outcome?.promise_to_pay === undefined ? 'Not available' : outcome.promise_to_pay ? `${formatMoney(outcome.commitment_amount)}${outcome.commitment_date ? ` on ${outcome.commitment_date}` : ''}` : 'No commitment recorded'}</p>
        {outcome?.reason_for_nonpayment && <p><strong>Reason for nonpayment:</strong> {outcome.reason_for_nonpayment}</p>}
      </section>
      <section className="after-call-section"><h3>Account context</h3>
        {focusLoan ? <p>{focusLoan.loan_type} loan {focusLoan.loan_number} · {focusLoan.status} · Outstanding {formatMoney(focusLoan.outstanding_amount)} · Due {focusLoan.due_date}</p> : <p>No loan details available.</p>}
      </section>
      <section className="voice-transcript"><h3>Transcript</h3>{transcript.length ? transcript.map((item) => <p key={item.id}><strong>{item.speaker === 'CUSTOMER' ? customer.full_name : 'AI Recovery Agent'}:</strong> {item.text}</p>) : <p className="muted">No transcript was delivered to the browser during this call.</p>}</section>
    </>}
  </div>
}
