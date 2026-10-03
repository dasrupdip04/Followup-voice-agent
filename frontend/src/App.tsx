import React from 'react'
import Dashboard from './pages/Dashboard'

export default function App(){
  return (
    <div className="app">
      <header className="header">
        <div className="logo">FA</div>
        <div>
          <h1 style={{margin:0}}>Followup Agent</h1>
          <div className="muted">Collections voice agent console</div>
        </div>
      </header>
      <Dashboard />
    </div>
  )
}
