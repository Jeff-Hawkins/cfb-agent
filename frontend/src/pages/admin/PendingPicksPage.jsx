/**
 * PendingPicksPage — admin view for approving or rejecting flagged picks.
 * Picks are removed from the UI immediately on approve/reject.
 * Each card fetches its AI explanation from GET /explanations/{pick_id}.
 */
import { useEffect, useState } from 'react'
import { getPendingPicks, approvePick, rejectPick } from '../../api/client'
// FEATURE_DESCRIPTIONS is imported for use in future feature-table expansion
// eslint-disable-next-line no-unused-vars
import { FEATURE_DESCRIPTIONS } from '../../utils/featureDescriptions'

const API_URL = import.meta.env.VITE_API_URL ?? ''

const LABEL_COLORS = {
  Lean:     'bg-yellow-700 text-yellow-100',
  Moderate: 'bg-orange-700 text-orange-100',
  Strong:   'bg-red-700   text-red-100',
}

function ConfidencePill({ label }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${LABEL_COLORS[label] ?? 'bg-gray-700 text-gray-200'}`}>
      {label}
    </span>
  )
}

/**
 * PickCard — renders a single pending pick with stats and AI analysis.
 * Fetches its own explanation independently so cards load in parallel.
 */
function PickCard({ pick, onApprove, onReject, isBusy }) {
  const [analysis, setAnalysis]         = useState(null)   // string when loaded
  const [analysisState, setAnalysisState] = useState('loading') // 'loading' | 'ready' | 'pending' | 'error'

  const isHome       = pick.pick_team === pick.home_team
  const pickSpread   = isHome ? pick.spread : -1 * pick.spread
  const modelImplied = isHome
    ? -1 * (pick.win_probability - 0.5) * 28
    : (pick.win_probability - 0.5) * 28
  const edge         = Math.abs(pick.spread - modelImplied).toFixed(1)
  const formatSpread = (val) => {
    const rounded = Number(val).toFixed(1)
    return val > 0 ? `+${rounded}` : `${rounded}`
  }

  useEffect(() => {
    let cancelled = false
    async function fetchExplanation() {
      try {
        const res = await fetch(`${API_URL}/explanations/${pick.id}`)
        if (cancelled) return
        if (res.status === 404) {
          setAnalysisState('pending')
          return
        }
        if (!res.ok) {
          setAnalysisState('error')
          return
        }
        const data = await res.json()
        setAnalysis(data.explanation_short ?? null)
        setAnalysisState('ready')
      } catch {
        if (!cancelled) setAnalysisState('error')
      }
    }
    fetchExplanation()
    return () => { cancelled = true }
  }, [pick.id])

  return (
    <div className="bg-[#111111] border border-[#222222] rounded-xl p-5">
      {/* Matchup header */}
      <p className="text-gray-400 text-xs mb-1">
        {pick.away_team} @ {pick.home_team} — Week {pick.week}
      </p>

      {/* Pick team (gold) */}
      <div className="flex items-center gap-3 mb-3">
        <span className="text-[#CFB526] font-bold text-lg">
          {pick.pick_team}
        </span>
        <span className="text-gray-500 text-xs">{isHome ? 'HOME' : 'AWAY'}</span>
        <ConfidencePill label={pick.confidence_label} />
      </div>

      {/* Stats row — always above AI Analysis */}
      <div className="flex gap-6 text-sm text-gray-300 mb-4">
        <span>
          Win Prob:{' '}
          <span className="text-white font-medium">
            {(pick.win_probability * 100).toFixed(1)}%
          </span>
        </span>
        <span>
          Pick Spread:{' '}
          <span className="text-white font-medium">{formatSpread(pickSpread)}</span>
        </span>
        <span>
          Model Line:{' '}
          <span className="text-white font-medium">{formatSpread(modelImplied)}</span>
        </span>
        <span>
          Edge:{' '}
          <span className="text-white font-medium">+{edge} pts</span>
        </span>
      </div>

      {/* AI Analysis section */}
      <div className="mb-4">
        <p className="text-gray-500 text-xs mb-1">AI Analysis</p>
        {analysisState === 'loading' && (
          <p className="text-gray-500 text-sm">Loading analysis...</p>
        )}
        {analysisState === 'ready' && analysis && (
          <p className="text-gray-300 text-sm leading-relaxed">{analysis}</p>
        )}
        {analysisState === 'pending' && (
          <p className="text-gray-500 text-sm italic">Analysis generating...</p>
        )}
        {/* error: fail silently — nothing rendered */}
      </div>

      {/* Action buttons */}
      <div className="flex gap-3">
        <button
          onClick={() => onApprove(pick.id)}
          disabled={isBusy}
          className="bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white text-sm font-semibold px-4 py-1.5 rounded-lg transition-colors"
        >
          Approve
        </button>
        <button
          onClick={() => onReject(pick.id)}
          disabled={isBusy}
          className="bg-red-800 hover:bg-red-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-1.5 rounded-lg transition-colors"
        >
          Reject
        </button>
      </div>
    </div>
  )
}

export default function PendingPicksPage() {
  const [picks,   setPicks]   = useState([])
  const [loading, setLoading] = useState(true)
  const [busy,    setBusy]    = useState({})   // pick_id → true while request in-flight

  useEffect(() => {
    getPendingPicks()
      .then(setPicks)
      .finally(() => setLoading(false))
  }, [])

  async function handleApprove(id) {
    setBusy(b => ({ ...b, [id]: true }))
    try {
      await approvePick(id)
      setPicks(p => p.filter(x => x.id !== id))
    } finally {
      setBusy(b => ({ ...b, [id]: false }))
    }
  }

  async function handleReject(id) {
    setBusy(b => ({ ...b, [id]: true }))
    try {
      await rejectPick(id)
      setPicks(p => p.filter(x => x.id !== id))
    } finally {
      setBusy(b => ({ ...b, [id]: false }))
    }
  }

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-10">
        <div className="h-6 w-48 bg-[#1a1a1a] rounded animate-pulse mb-6" />
        {[1,2,3].map(i => (
          <div key={i} className="h-32 bg-[#1a1a1a] rounded-xl animate-pulse mb-4" />
        ))}
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <h1 className="text-xl font-bold text-white mb-6">Pending Picks</h1>

      {picks.length === 0 ? (
        <p className="text-gray-500 text-sm">No picks pending review.</p>
      ) : (
        <div className="flex flex-col gap-4">
          {picks.map(pick => (
            <PickCard
              key={pick.id}
              pick={pick}
              onApprove={handleApprove}
              onReject={handleReject}
              isBusy={!!busy[pick.id]}
            />
          ))}
        </div>
      )}
    </div>
  )
}
