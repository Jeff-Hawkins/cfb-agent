/**
 * GamesPage — public view of weekly FBS games with model vs Vegas comparison.
 * No authentication required. Accessible at /games.
 *
 * Each game card shows win probabilities and model-implied spreads for both
 * teams alongside the Vegas consensus line and model edge. Games with an
 * approved pick show a Value Pick badge that links to /picks.
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getWeeklyGames } from '../api/client'

const SEASON = 2025
const WEEKS  = Array.from({ length: 15 }, (_, i) => i + 1)

// Confidence badge thresholds based on the stronger team's win probability
const LABEL_COLORS = {
  Lean:     'bg-yellow-700 text-yellow-100',
  Moderate: 'bg-orange-700 text-orange-100',
  Strong:   'bg-red-700   text-red-100',
}

function confidenceLabel(maxWinProb) {
  if (maxWinProb >= 0.85) return 'Strong'
  if (maxWinProb >= 0.75) return 'Moderate'
  if (maxWinProb >= 0.60) return 'Lean'
  return null
}

function ConfidencePill({ prob }) {
  const label = confidenceLabel(prob)
  if (!label) return null
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${LABEL_COLORS[label]}`}>
      {label}
    </span>
  )
}

function formatSpread(val) {
  if (val === null || val === undefined) return '—'
  const rounded = Number(val).toFixed(1)
  return val > 0 ? `+${rounded}` : `${rounded}`
}

function GameCard({ game }) {
  const navigate    = useNavigate()
  const maxWinProb  = Math.max(game.home_win_prob, game.away_win_prob)
  const isFinal     = game.status === 'final'

  return (
    <div className="bg-[#111111] border border-[#222222] rounded-xl p-5">
      {/* Matchup header */}
      <div className="flex items-center justify-between mb-3">
        <p className="text-gray-400 text-xs">
          {game.away_team} @ {game.home_team} — Week {game.week}
        </p>
        <div className="flex items-center gap-2">
          <ConfidencePill prob={maxWinProb} />
          {game.has_approved_pick && (
            <button
              onClick={() => navigate('/picks')}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-[#C9A84C] text-black hover:bg-[#e0be6a] transition-colors"
            >
              🔥 Value Pick
            </button>
          )}
        </div>
      </div>

      {/* Final score (if available) */}
      {isFinal && (
        <div className="flex gap-4 mb-3 text-sm">
          <span className="text-gray-400 text-xs">Final:</span>
          <span className="text-white font-semibold text-xs">
            {game.away_team} {game.away_score} — {game.home_team} {game.home_score}
          </span>
        </div>
      )}

      {/* Two-column team breakdown */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        {/* Away team */}
        <div className="bg-[#0a0a0a] rounded-lg p-3">
          <p className="text-gray-300 text-sm font-medium mb-2 truncate">{game.away_team}</p>
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Win Prob</span>
              <span className="text-white font-medium">
                {(game.away_win_prob * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Model Line</span>
              <span className="text-white font-medium">
                {formatSpread(game.away_implied_spread)}
              </span>
            </div>
          </div>
        </div>

        {/* Home team */}
        <div className="bg-[#0a0a0a] rounded-lg p-3">
          <p className="text-gray-300 text-sm font-medium mb-2 truncate">{game.home_team}</p>
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Win Prob</span>
              <span className="text-white font-medium">
                {(game.home_win_prob * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Model Line</span>
              <span className="text-white font-medium">
                {formatSpread(game.home_implied_spread)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Vegas line and edge */}
      <div className="flex flex-wrap gap-4 text-xs text-gray-400 border-t border-[#1a1a1a] pt-3">
        <span>
          Vegas Line:{' '}
          <span className="text-white font-medium">
            {game.consensus_spread !== null
              ? `${formatSpread(game.consensus_spread)} (home)`
              : '—'}
          </span>
        </span>
        <span>
          Model Edge:{' '}
          <span className={`font-medium ${game.model_edge !== null && game.model_edge >= 5 ? 'text-[#C9A84C]' : 'text-white'}`}>
            {game.model_edge !== null ? `${Number(game.model_edge).toFixed(1)} pts` : '—'}
          </span>
        </span>
      </div>
    </div>
  )
}

export default function GamesPage() {
  const [games,   setGames]   = useState([])
  const [week,    setWeek]    = useState(1)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    getWeeklyGames(SEASON, week)
      .then(data => {
        if (!cancelled) setGames(Array.isArray(data) ? data : [])
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load games. Please try again.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [week])

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-xl font-bold text-white">This Week's Games</h1>
        <p className="text-gray-500 text-sm mt-1">
          Model predictions vs Vegas consensus — FBS games with a model lean
        </p>
      </div>

      {/* Week selector */}
      <div className="flex items-center gap-3 mb-6">
        <span className="text-gray-400 text-sm">Week:</span>
        <select
          value={week}
          onChange={e => setWeek(Number(e.target.value))}
          className="bg-[#1a1a1a] border border-[#333333] text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-[#C9A84C]"
        >
          {WEEKS.map(w => (
            <option key={w} value={w}>Week {w}</option>
          ))}
        </select>
      </div>

      {/* Error state */}
      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      {/* Content */}
      {loading ? (
        <div className="flex flex-col gap-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-52 bg-[#1a1a1a] rounded-xl animate-pulse" />
          ))}
        </div>
      ) : games.length === 0 ? (
        <p className="text-gray-500 text-sm">No games this week.</p>
      ) : (
        <div className="flex flex-col gap-4">
          {games.map(game => (
            <GameCard key={game.game_id} game={game} />
          ))}
        </div>
      )}
    </div>
  )
}
