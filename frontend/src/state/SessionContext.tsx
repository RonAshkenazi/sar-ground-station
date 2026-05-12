import { createContext, useContext, useState, type ReactNode } from 'react'
import { getSessionState } from '../api/sessions'
import type { SessionState } from '../types'

type SessionCtx = {
  session: SessionState | null
  setSession: (session: SessionState) => void
  refreshSession: () => Promise<SessionState | null>
  clearSession: () => void
}

const SessionContext = createContext<SessionCtx | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<SessionState | null>(null)

  async function refreshSession() {
    if (!session?.session_id) return null
    const next = await getSessionState(session.session_id)
    setSessionState(next)
    return next
  }

  return (
    <SessionContext.Provider
      value={{
        session,
        setSession: setSessionState,
        refreshSession,
        clearSession: () => setSessionState(null),
      }}
    >
      {children}
    </SessionContext.Provider>
  )
}

export function useSession(): SessionCtx {
  const ctx = useContext(SessionContext)
  if (!ctx) {
    throw new Error('useSession must be inside SessionProvider')
  }
  return ctx
}
