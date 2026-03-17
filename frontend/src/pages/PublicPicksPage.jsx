/**
 * PublicPicksPage — public view of all approved CFB Agent picks for a season/week.
 * No authentication required. Accessible at /picks.
 */
import { useEffect, useState } from 'react'
import { getPublicPicks } from '../api/client'

const SEASON = 2025
const WEEKS  = Array.from({ length: 15 }, (_, i) => i + 1)

const LABEL_COLORS = {
  Lean:     'bg-yellow-700 text-yellow-100',
  Moderate: 'bg-orange-700 text-orange-100',
  Strong:   'bg-red-700   text-red-100',
}

const OUTCOME_COLOR = {
  WIN:  'text-green-400',
  LOSS: 'text-red-400',
  PUSH: 'text-gray-400',
}

function ConfidencePill({ label }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${LABEL_COLORS[label] ?? 'bg-gray-700 text-gray-200'}`}>
      {label}
    </span>
  )
}

function SummaryBar({ picks }) {
  const finished = picks.filter(p => p.ats_result && p.ats_result !== '')
  const wins     = finished.filter(p => p.ats_result === 'WIN').length
  const losses   = finished.filter(p => p.ats_result === 'LOSS').length
  const pushes   = finished.filter(p => p.ats_result === 'PUSH').length

  const roi = finished.length > 0
    ? (((wins * 1) - (losses * 1.1)) / finished.length * 100).toFixed(1)
    : null

  return (
    <div className="flex flex-wrap gap-6 bg-[#111111] border border-[#222222] rounded-xl px-6 py-4 mb-6 text-sm">
      <div>
        <p className="text-gray-400 text-xs mb-1">ATS Record</p>
        <p className="text-white font-semibold">
          {wins}-{losses}{pushes > 0 ? `-${pushes}` : ''}
        </p>
      </div>
      <div>
        <p className="text-gray-400 text-xs mb-1">ROI</p>
        <p className={`font-semibold ${roi !== null ? (Number(roi) >= 0 ? 'text-green-400' : 'text-red-400') : 'text-gray-500'}`}>
          {roi !== null ? `${roi}%` : '—'}
        </p>
      </div>
      <div className="flex items-end">
        <p className="text-gray-500 text-xs">Model picks based on win probability and line value analysis</p>
      </div>
    </div>
  )
}

function PickCard({ pick }) {
  const isHome    = pick.pick_team === pick.home_team
  const aiText    = pick.explanation_short && pick.explanation_short !== '' ? pick.explanation_short : null
  const atsColor  = OUTCOME_COLOR[pick.ats_result] ?? 'text-gray-500'
  const outColor  = OUTCOME_COLOR[pick.outcome]    ?? 'text-gray-500'
  const hasResult = pick.outcome && pick.outcome !== ''

  return (
    <div className="bg-[#111111] border border-[#222222] rounded-xl p-5">
      {/* Matchup header */}
      <p className="text-gray-400 text-xs mb-1">
        {pick.away_team} @ {pick.home_team} — Week {pick.week}
      </p>

      {/* Pick team */}
      <div className="flex items-center gap-3 mb-3">
        <span className="text-[#CFB526] font-bold text-lg">{pick.pick_team}</span>
        <span className="text-gray-500 text-xs">{isHome ? 'HOME' : 'AWAY'}</span>
        <ConfidencePill label={pick.confidence_label} />
        {hasResult && (
          <>
            <span className={`text-xs font-semibold ${outColor}`}>{pick.outcome}</span>
            {pick.ats_result && pick.ats_result !== '' && (
              <span className={`text-xs font-semibold ${atsColor}`}>{pick.ats_result} ATS</span>
            )}
          </>
        )}
      </div>

      {/* Stats row */}
      <div className="flex flex-wrap gap-6 text-sm text-gray-300 mb-3">
        <span>
          Win Prob:{' '}
          <span className="text-white font-medium">
            {(pick.win_probability * 100).toFixed(1)}%
          </span>
        </span>
        <span>
          Spread:{' '}
          <span className="text-white font-medium">
            {pick.spread !== '' ? (pick.spread > 0 ? '+' : '') + Number(pick.spread).toFixed(1) : '—'}
          </span>
        </span>
        <span>
          Model Edge:{' '}
          <span className="text-white font-medium">
            +{Number(pick.model_spread_diff).toFixed(1)} pts
          </span>
        </span>
      </div>

      {/* AI Analysis */}
      {aiText && (
        <div>
          <p className="text-gray-500 text-xs mb-0.5">AI Analysis</p>
          <p className="text-gray-300 text-sm leading-relaxed">{aiText}</p>
        </div>
      )}
    </div>
  )
}

export default function PublicPicksPage() {
  const [picks,       setPicks]       = useState([])
  const [loading,     setLoading]     = useState(true)
  const [activeWeek,  setActiveWeek]  = useState(null)  // null = most recent
  const [weekOptions, setWeekOptions] = useState([])    // weeks that have picks

  // Initial load — fetch most recent week to discover which week is current
  useEffect(() => {
    setLoading(true)
    getPublicPicks(SEASON, null)
      .then(data => {
        setPicks(data)
        if (data.length > 0) {
          const w = data[0].week
          setActiveWeek(w)
          // Build week options from returned data (may span multiple weeks if same week)
          setWeekOptions(prev => {
            const known = new Set(prev)
            data.forEach(p => known.add(p.week))
            return Array.from(known).sort((a, b) => a - b)
          })
        }
      })
      .catch(() => setPicks([]))
      .finally(() => setLoading(false))
  }, [])

  function handleWeekChange(week) {
    if (week === activeWeek) return
    setActiveWeek(week)
    setLoading(true)
    getPublicPicks(SEASON, week)
      .then(data => {
        setPicks(data)
        setWeekOptions(prev => {
          const known = new Set(prev)
          data.forEach(p => known.add(p.week))
          return Array.from(known).sort((a, b) => a - b)
        })
      })
      .catch(() => setPicks([]))
      .finally(() => setLoading(false))
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-xl font-bold text-white">CFB Agent Picks</h1>
        <p className="text-gray-500 text-sm mt-1">{SEASON} Season</p>
      </div>

      {/* Summary bar — only when picks exist */}
      {!loading && picks.length > 0 && <SummaryBar picks={picks} />}

      {/* Week selector */}
      {weekOptions.length > 0 && (
        <div className="flex items-center gap-2 mb-6">
          <span className="text-gray-400 text-sm">Week:</span>
          <select
            value={activeWeek ?? ''}
            onChange={e => handleWeekChange(Number(e.target.value))}
            className="bg-[#1a1a1a] border border-[#333333] text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-[#C9A84C]"
          >
            {weekOptions.map(w => (
              <option key={w} value={w}>Week {w}</option>
            ))}
          </select>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="flex flex-col gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-36 bg-[#1a1a1a] rounded-xl animate-pulse" />
          ))}
        </div>
      ) : picks.length === 0 ? (
        <p className="text-gray-500 text-sm">No picks this week.</p>
      ) : (
        <div className="flex flex-col gap-4">
          {picks.map(pick => (
            <PickCard key={pick.id} pick={pick} />
          ))}
        </div>
      )}
    </div>
  )
}
