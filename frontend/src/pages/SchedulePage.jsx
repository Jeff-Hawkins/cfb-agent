/**
 * SchedulePage — displays 2025 CFB games by week with prediction capabilities.
 * Allows selecting a week (1–15) and renders a grid of GameCard components.
 */
import { useState, useEffect } from 'react'
import { getGames } from '../api/client'
import GameCard from '../components/GameCard'
import LoadingSkeleton from '../components/LoadingSkeleton'

/**
 * Page showing the weekly CFB schedule with clickable game cards.
 * @returns {JSX.Element} The schedule page.
 */
export default function SchedulePage() {
  const [week, setWeek] = useState(1)
  const [games, setGames] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    getGames(week)
      .then((data) => {
        if (!cancelled) {
          setGames(Array.isArray(data) ? data : [])
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError('Failed to load games. Please try again.')
          setLoading(false)
        }
      })

    return () => { cancelled = true }
  }, [week])

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Banner */}
      <div className="mb-6 p-4 bg-[#111111] border border-[#222222] rounded-xl text-center">
        <p className="text-gray-300 text-sm">
          <span className="text-[#C9A84C] font-semibold">2025 Season</span>
          {' '}— Predictions powered by LightGBM model{' '}
          <span className="text-white font-semibold">(78.2% holdout accuracy)</span>
        </p>
      </div>

      {/* Week selector */}
      <div className="flex items-center gap-4 mb-6">
        <label htmlFor="week-select" className="text-gray-300 text-sm font-medium">
          Week
        </label>
        <select
          id="week-select"
          value={week}
          onChange={(e) => setWeek(Number(e.target.value))}
          className="bg-[#111111] border border-[#222222] text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#C9A84C]"
        >
          {Array.from({ length: 15 }, (_, i) => i + 1).map((w) => (
            <option key={w} value={w}>
              Week {w}
            </option>
          ))}
        </select>
      </div>

      {/* Error state */}
      {error && (
        <p className="text-red-400 text-sm mb-4">{error}</p>
      )}

      {/* Games grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          <LoadingSkeleton count={6} />
        ) : games.length === 0 ? (
          <p className="text-gray-500 col-span-3 text-center py-12">
            No games found for Week {week}.
          </p>
        ) : (
          games.map((game, idx) => (
            <GameCard key={game.id ?? idx} game={game} />
          ))
        )}
      </div>
    </div>
  )
}
