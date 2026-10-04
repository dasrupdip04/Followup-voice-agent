import React from 'react'
import Dashboard from './pages/Dashboard'

export default function App(){
  return (
    <div className="app">
      <header className="header">
        <div className="logo">FA</div>
        <div>
          <h1 style={{margin:0}}>Follow-up Customer Call</h1>
          <div className="muted">A bank recovery agent will speak with the selected customer</div>
        </div>
      </header>
      <Dashboard />
    </div>
  )
}
