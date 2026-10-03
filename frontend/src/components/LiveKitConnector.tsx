import React from 'react'

/*
  LiveKitConnector
  - A documented integration boundary for LiveKit voice/video.
  - This component intentionally does not include LiveKit credentials or secrets.
  - Responsibilities:
    - Accept `callId` and lifecycle callbacks.
    - Expose connection state, microphone mute/unmute, and participant list via props or events.
    - Emit transcript/participant events into the parent via callbacks.

  Integration notes:
  - The backend's LiveKit runner (if present) should provide a server-side token endpoint.
  - The frontend should call that token endpoint (not included here) to obtain a Join token.
  - Replace this placeholder with actual `livekit-client` usage when ready and keep
    authentication server-side to avoid exposing API secrets.
*/

export default function LiveKitConnector({callId, onConnected, onDisconnected}:{callId:number, onConnected?:()=>void, onDisconnected?:()=>void}){
  // Placeholder UI only. When integrating, replace this UI with the LiveKit client
  // component that uses a server-signed token and handles audio input/output.

  function handleConnect(){
    if(onConnected) onConnected()
  }
  function handleDisconnect(){
    if(onDisconnected) onDisconnected()
  }

  return (
    <div style={{border:'1px dashed rgba(255,255,255,0.04)', padding:12, borderRadius:6, marginBottom:8}}>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <div>
          <strong>LiveKit</strong>
          <div className="muted">Integration placeholder — not connected</div>
        </div>
        <div>
          <button className="btn" onClick={handleConnect}>Connect (dev)</button>
          <button style={{marginLeft:8}} className="btn outline" onClick={handleDisconnect}>Disconnect</button>
        </div>
      </div>
    </div>
  )
}
