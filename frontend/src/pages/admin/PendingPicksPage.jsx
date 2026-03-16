/**
 * PendingPicksPage — admin view for approving or rejecting flagged picks.
 * Picks are removed from the UI immediately on approve/reject.
 */
import { useEffect, useState } from 'react'
import { getPendingPicks, approvePick, rejectPick } from '../../api/client'

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
          {picks.map(pick => {
            const opponent = pick.pick_team === pick.home_team ? pick.away_team : pick.home_team
            const isHome   = pick.pick_team === pick.home_team
            return (
              <div key={pick.id} className="bg-[#111111] border border-[#222222] rounded-xl p-5">
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

                {/* Stats row */}
                <div className="flex gap-6 text-sm text-gray-300 mb-4">
                  <span>
                    Win Prob:{' '}
                    <span className="text-white font-medium">
                      {(pick.win_probability * 100).toFixed(1)}%
                    </span>
                  </span>
                  <span>
                    Spread:{' '}
                    <span className="text-white font-medium">
                      {pick.spread > 0 ? '+' : ''}{pick.spread}
                    </span>
                  </span>
                  <span>
                    Model Edge:{' '}
                    <span className="text-white font-medium">
                      +{pick.model_spread_diff} pts
                    </span>
                  </span>
                </div>

                {/* Action buttons */}
                <div className="flex gap-3">
                  <button
                    onClick={() => handleApprove(pick.id)}
                    disabled={busy[pick.id]}
                    className="bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white text-sm font-semibold px-4 py-1.5 rounded-lg transition-colors"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => handleReject(pick.id)}
                    disabled={busy[pick.id]}
                    className="bg-red-800 hover:bg-red-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-1.5 rounded-lg transition-colors"
                  >
                    Reject
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
