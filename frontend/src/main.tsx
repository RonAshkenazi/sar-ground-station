import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import { SessionProvider } from './state/SessionContext'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <SessionProvider>
      <App />
    </SessionProvider>
  </React.StrictMode>,
)
