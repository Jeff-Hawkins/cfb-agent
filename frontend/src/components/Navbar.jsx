/**
 * Navbar component — fixed top bar with site title and navigation links.
 * Shows Admin/History links for authenticated users; Login link otherwise.
 */
import { useEffect, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'

const navLink = ({ isActive }) =>
  `text-sm font-medium transition-colors pb-1 ${
    isActive
      ? 'text-[#C9A84C] border-b-2 border-[#C9A84C]'
      : 'text-gray-300 hover:text-white'
  }`

export default function Navbar() {
  const [session, setSession] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => setSession(session))

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_e, s) => setSession(s))
    return () => subscription.unsubscribe()
  }, [])

  async function handleLogout() {
    await supabase.auth.signOut()
    navigate('/', { replace: true })
  }

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[#111111] border-b border-[#222222] h-16 flex items-center px-6">
      <div className="flex items-center justify-between w-full max-w-7xl mx-auto">
        <span className="text-[#C9A84C] font-bold text-xl tracking-tight">CFB Agent</span>

        <div className="flex items-center gap-6">
          <NavLink to="/games" className={navLink}>Games</NavLink>
          <NavLink to="/rankings" className={navLink}>Power Rankings</NavLink>
          <NavLink to="/picks" className={navLink}>Picks</NavLink>
          <NavLink to="/clv" className={navLink}>CLV</NavLink>

          {session ? (
            <>
              <NavLink to="/admin" end className={navLink}>Admin</NavLink>
              <NavLink to="/admin/history" className={navLink}>History</NavLink>
              <button
                onClick={handleLogout}
                className="text-sm font-medium text-gray-400 hover:text-white transition-colors"
              >
                Logout
              </button>
            </>
          ) : (
            <NavLink to="/login" className={navLink}>Login</NavLink>
          )}
        </div>
      </div>
    </nav>
  )
}
