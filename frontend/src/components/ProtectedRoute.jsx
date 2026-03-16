/**
 * ProtectedRoute — renders children only when a Supabase session exists.
 * Redirects unauthenticated visitors to /login.
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'

/**
 * Gate component for admin-only routes.
 * @param {{ children: React.ReactNode }} props
 * @returns {JSX.Element|null}
 */
export default function ProtectedRoute({ children }) {
  const [checking, setChecking] = useState(true)
  const [authed, setAuthed]     = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setAuthed(true)
      } else {
        navigate('/login', { replace: true })
      }
      setChecking(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session) navigate('/login', { replace: true })
    })

    return () => subscription.unsubscribe()
  }, [navigate])

  if (checking) return null
  if (!authed)  return null
  return children
}
