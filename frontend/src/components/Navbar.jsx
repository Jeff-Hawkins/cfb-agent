/**
 * Navbar component — fixed top bar with site title and navigation links.
 * Uses react-router-dom NavLink for active-state gold underline styling.
 */
import { NavLink } from 'react-router-dom'

/**
 * Top navigation bar for CFB Agent.
 * @returns {JSX.Element} The navbar element.
 */
export default function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[#111111] border-b border-[#222222] h-16 flex items-center px-6">
      <div className="flex items-center justify-between w-full max-w-7xl mx-auto">
        {/* Site title */}
        <span className="text-[#C9A84C] font-bold text-xl tracking-tight">
          CFB Agent
        </span>

        {/* Navigation links */}
        <div className="flex items-center gap-6">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `text-sm font-medium transition-colors pb-1 ${
                isActive
                  ? 'text-[#C9A84C] border-b-2 border-[#C9A84C]'
                  : 'text-gray-300 hover:text-white'
              }`
            }
          >
            Schedule
          </NavLink>
          <NavLink
            to="/rankings"
            className={({ isActive }) =>
              `text-sm font-medium transition-colors pb-1 ${
                isActive
                  ? 'text-[#C9A84C] border-b-2 border-[#C9A84C]'
                  : 'text-gray-300 hover:text-white'
              }`
            }
          >
            Power Rankings
          </NavLink>
        </div>
      </div>
    </nav>
  )
}
