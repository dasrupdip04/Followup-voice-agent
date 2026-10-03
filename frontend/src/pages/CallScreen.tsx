import React, {useEffect, useRef, useState} from 'react'
import { sendMessage, endCall } from '../services/callService'
import LiveKitConnector from '../components/LiveKitConnector'

/*
  CallScreen
  - Displays call status, elapsed time, transcript, speaker separation, and tool events.
  - Accepts a `strategy` prop produced by the StartCall endpoint and displays it as
    the pre-call objective and recommended opening.
  - Provides a lightweight LiveKit integration boundary (`LiveKitConnector`) for
    voice connection. The connector is a documented placeholder that should be
    wired to the project's LiveKit runner when ready.
*/

export default function CallScreen({callId, strategy}:{callId:number, strategy?:any}){
  const [messages,setMessages] = useState<{speaker:string,text:string,id?:string}[]>([])
  const [input,setInput] = useState('')
  const [loading,setLoading] = useState(false)
  const [connected,setConnected] = useState(false)
  const [startedAt,setStartedAt] = useState<number|undefined>()
  const [elapsed,setElapsed] = useState(0)
  const [toolEvents,setToolEvents] = useState<string[]>([])
  const [endedResult,setEndedResult] = useState<any|null>(null)
  const timerRef = useRef<number|undefined>()

  useEffect(()=>{
    if(startedAt){
      timerRef.current = window.setInterval(()=>{
        setElapsed(Math.floor((Date.now()-startedAt)/1000))
      },1000)
    }
    return ()=>{ if(timerRef.current) window.clearInterval(timerRef.current) }
  },[startedAt])

  function onLivekitConnected(){
    setConnected(true)
    setStartedAt(Date.now())
  }

  function onLivekitDisconnected(){
    setConnected(false)
  }

  async function handleSend(){
    if(!input) return
    const userText = input
    setMessages(m=>[...m,{speaker:'CUSTOMER',text:userText}])
    setInput('')
    setLoading(true)
    try{
      const res = await sendMessage(callId, userText)
      // append agent response and any tool events
      if(res.tool_calls && res.tool_calls.length) setToolEvents(t=>[...t, ...res.tool_calls.map((t:any)=>t.name || JSON.stringify(t))])
      setMessages(m=>[...m,{speaker:'AGENT',text:res.response}])
    }catch(e:any){
      setMessages(m=>[...m,{speaker:'AGENT',text:'Error: failed to get response'}])
    }finally{setLoading(false)}
  }

  async function handleEnd(){
    try{
      const res = await endCall(callId)
      setEndedResult(res)
      setConnected(false)
      if(timerRef.current) window.clearInterval(timerRef.current)
    }catch(e:any){
      alert('Failed to end call')
    }
  }

  return (
    <div>
      <div className="card">
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
          <div>
            <div style={{fontSize:14,fontWeight:700}}>Call #{callId}</div>
            <div className="muted">Status: {connected? 'Connected' : 'Not connected'}</div>
          </div>
          <div style={{textAlign:'right'}}>
            <div className="muted">Elapsed</div>
            <div style={{fontWeight:700,fontSize:14}}>{new Date(elapsed*1000).toISOString().substr(11,8)}</div>
          </div>
        </div>

        <hr />

        {strategy && (
          <div style={{marginBottom:12}} className="card muted">
            <strong>Objective:</strong> {strategy.objective ?? '—'}
            <div style={{marginTop:6}}><strong>Opening:</strong> <span className="muted">{strategy.opening ?? '—'}</span></div>
          </div>
        )}

        <LiveKitConnector callId={callId} onConnected={onLivekitConnected} onDisconnected={onLivekitDisconnected} />

        <div className="transcript" style={{minHeight:150}}>
          {messages.map((m,i)=>(
            <div key={i} style={{marginBottom:10, padding:8, borderRadius:6, background: m.speaker==='AGENT'? 'rgba(30,120,240,0.06)' : 'rgba(200,200,200,0.04)'}}>
              <div style={{fontSize:12,fontWeight:700}}>{m.speaker}</div>
              <div style={{whiteSpace:'pre-wrap'}}>{m.text}</div>
            </div>
          ))}
        </div>

        {toolEvents.length>0 && (
          <div style={{marginTop:8}}>
            {toolEvents.map((t,i)=>(<div className="tool-event" key={i}>[tool] {t}</div>))}
          </div>
        )}

        <div className="input-row">
          <input className="input" value={input} onChange={e=>setInput(e.target.value)} placeholder="Type customer utterance (text test mode)..." />
          <button className="btn" onClick={handleSend} disabled={loading}>{loading? '...' : 'Send'}</button>
          <button style={{marginLeft:8}} className="btn outline" onClick={handleEnd}>End Call</button>
        </div>

        {endedResult && (
          <div style={{marginTop:12}} className="card">
            <h4>Call Summary</h4>
            <div><strong>Outcome:</strong> {endedResult.outcome?.outcome_type ?? JSON.stringify(endedResult.outcome)}</div>
            <div><strong>Duration:</strong> {endedResult.metrics?.duration_seconds ?? '—'}</div>
            <div style={{marginTop:8}}><strong>Metrics:</strong> <div className="muted">{JSON.stringify(endedResult.metrics)}</div></div>
          </div>
        )}
      </div>
    </div>
  )
}
