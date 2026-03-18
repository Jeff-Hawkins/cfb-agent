/**
 * GamesPage — public view of weekly FBS games with model vs Vegas comparison.
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getWeeklyGames } from '../api/client'

const SEASON = 2025
const WEEKS  = Array.from({ length: 15 }, (_, i) => i + 1)

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

function ConfGroupBadge({ group }) {
  if (!group) return null
  const colors = group === 'P4' 
    ? 'bg-blue-900/40 text-blue-200 border-blue-800/50' 
    : 'bg-amber-900/40 text-amber-200 border-amber-800/50'
  
  return (
    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase tracking-wider ${colors}`}>
      {group}
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
    <div className="bg-[#111111] border border-[#222222] rounded-xl p-5 relative overflow-hidden">
      {/* Matchup header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <ConfGroupBadge group={game.conference_group} />
          <p className="text-gray-400 text-xs">
            {game.away_team} @ {game.home_team} — Week {game.week}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <ConfidencePill prob={maxWinProb} />
          {game.has_approved_pick && (
            <button
              onClick={() => navigate('/picks')}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-[#C9A84C] text-black hover:bg-[#e0be6a] transition-colors shadow-lg shadow-black/20"
            >
              🔥 Value Pick
            </button>
          )}
        </div>
      </div>

      {/* Final score */}
      {isFinal && (
        <div className="flex gap-4 mb-3 text-sm">
          <span className="text-gray-400 text-xs uppercase font-semibold">Final:</span>
          <span className="text-white font-bold text-xs">
            {game.away_team} {game.away_score} — {game.home_team} {game.home_score}
          </span>
        </div>
      )}

      {/* Two-column team breakdown */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-white/[0.03] border border-white/5 rounded-lg p-3">
          <p className="text-gray-300 text-sm font-bold mb-2 truncate">{game.away_team}</p>
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Win Prob</span>
              <span className="text-white font-medium">{(game.away_win_prob * 100).toFixed(0)}%</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Model Line</span>
              <span className="text-white font-mono">{formatSpread(game.away_implied_spread)}</span>
            </div>
          </div>
        </div>

        <div className="bg-white/[0.03] border border-white/5 rounded-lg p-3">
          <p className="text-gray-300 text-sm font-bold mb-2 truncate">{game.home_team}</p>
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Win Prob</span>
              <span className="text-white font-medium">{(game.home_win_prob * 100).toFixed(0)}%</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Model Line</span>
              <span className="text-white font-mono">{formatSpread(game.home_implied_spread)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Vegas line and edge */}
      <div className="flex flex-wrap gap-4 text-xs text-gray-400 border-t border-white/5 pt-3">
        <span>
          Vegas Line:{' '}
          <span className="text-white font-medium">
            {game.consensus_spread !== null ? `${formatSpread(game.consensus_spread)} (home)` : '—'}
          </span>
        </span>
        <span>
          Model Edge:{' '}
          <span className={`font-bold ${game.model_edge !== null && game.model_edge >= 5 ? 'text-[#C9A84C]' : 'text-white'}`}>
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
  const [filter,  setFilter]  = useState('All')
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

  const filteredGames = filter === 'All' 
    ? games 
    : games.filter(g => g.conference_group === filter)

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Weekly Predictions</h1>
          <p className="text-gray-500 text-sm">
            Model win probabilities and value edges for FBS matchups.
          </p>
        </div>

        <div className="flex items-center gap-4">
          {/* Week Selector */}
          <div className="flex items-center gap-2">
            <span className="text-gray-500 text-xs font-bold uppercase tracking-wider">Week</span>
            <select
              value={week}
              onChange={e => setWeek(Number(e.target.value))}
              className="bg-[#1a1a1a] border border-[#333333] text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-[#C9A84C]"
            >
              {WEEKS.map(w => <option key={w} value={w}>{w}</option>)}
            </select>
          </div>

          {/* Group Filter */}
          <div className="flex bg-[#1a1a1a] p-1 rounded-lg border border-[#333333]">
            {['All', 'P4', 'G5'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all ${
                  filter === f ? 'bg-[#C9A84C] text-black shadow-lg shadow-black/20' : 'text-gray-500 hover:text-white'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-56 bg-white/5 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : filteredGames.length === 0 ? (
        <div className="py-24 text-center">
          <p className="text-gray-500 text-lg italic">No {filter !== 'All' ? filter : ''} games found for this week.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredGames.map(game => (
            <GameCard key={game.game_id} game={game} />
          ))}
        </div>
      )}
    </div>
  )
}
