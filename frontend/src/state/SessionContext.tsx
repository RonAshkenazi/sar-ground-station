import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { getSessionState } from '../api/sessions'
import type { SessionState } from '../types'

type SessionCtx = {
  session: SessionState | null
  setSession: (session: SessionState) => void
  refreshSession: () => Promise<SessionState | null>
  clearSession: () => void
  lassoPolygon: [number, number][] | null
  setLassoPolygon: (polygon: [number, number][] | null) => void
}

const SessionContext = createContext<SessionCtx | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSessionState] = useState<SessionState | null>(null)
  const [lassoPolygon, setLassoPolygon] = useState<[number, number][] | null>(null)

  useEffect(() => {
    setLassoPolygon(null)
  }, [session?.session_id])

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
        clearSession: () => {
          setSessionState(null)
          setLassoPolygon(null)
        },
        lassoPolygon,
        setLassoPolygon,
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
