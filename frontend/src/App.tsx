import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from './lib/supabaseClient'
import { getProfile } from './lib/api'
import { AuthPage } from './components/AuthPage'
import { CompleteProfile } from './components/CompleteProfile'
import { ChatShell } from './components/ChatShell'

const queryClient = new QueryClient()

function Gate({ session }: { session: Session }) {
  const profileQuery = useQuery({
    queryKey: ['profile', session.user.id],
    queryFn: () => getProfile(session.access_token),
  })

  if (profileQuery.isLoading) return <p className="centered">Loading…</p>
  if (profileQuery.isError) return <p className="centered error">Could not load your profile.</p>

  const profile = profileQuery.data
  if (!profile?.department || !profile?.role) {
    return (
      <CompleteProfile
        token={session.access_token}
        onSaved={() => profileQuery.refetch()}
      />
    )
  }

  return <ChatShell />
}

function AppInner() {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setLoading(false)
    })
    const { data: listener } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession)
    })
    return () => listener.subscription.unsubscribe()
  }, [])

  if (loading) return <p className="centered">Loading…</p>
  if (!session) return <AuthPage />
  return <Gate session={session} />
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  )
}
