/**
 * PickHistoryPage — admin view of all approved picks with outcomes and ATS tracking.
 * Shows a summary bar (ATS record, ROI, avg CLV) above a sortable history table.
 */
import { useEffect, useState } from 'react'
import { getApprovedPicks } from '../../api/client'

const API_URL = import.meta.env.VITE_API_URL ?? ''

const ATS_COLOR = {
  WIN:  'text-green-400',
  LOSS: 'text-red-400',
  PUSH: 'text-gray-400',
}

function SummaryBar({ picks }) {
  const finished = picks.filter(p => p.ats_result && p.ats_result !== '')
  const wins     = finished.filter(p => p.ats_result === 'WIN').length
  const losses   = finished.filter(p => p.ats_result === 'LOSS').length
  const pushes   = finished.filter(p => p.ats_result === 'PUSH').length

  // Simple ROI: +1 unit per win, -1.1 per loss (standard -110 vig)
  const roi = finished.length > 0
    ? (((wins * 1) - (losses * 1.1)) / finished.length * 100).toFixed(1)
    : null

  const clvPicks = picks.filter(p => p.clv !== '' && p.clv !== null)
  const avgClv   = clvPicks.length > 0
    ? (clvPicks.reduce((s, p) => s + Number(p.clv), 0) / clvPicks.length).toFixed(2)
    : null

  return (
    <div className="flex gap-8 bg-[#111111] border border-[#222222] rounded-xl px-6 py-4 mb-6 text-sm">
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
      <div>
        <p className="text-gray-400 text-xs mb-1">Avg CLV</p>
        <p className="text-white font-semibold">
          {avgClv !== null ? `${avgClv} pts` : '—'}
        </p>
      </div>
    </div>
  )
}

export default function PickHistoryPage() {
  const [picks,        setPicks]        = useState([])
  const [loading,      setLoading]      = useState(true)
  const [explanations, setExplanations] = useState({})   // pick_id → explanation_short

  useEffect(() => {
    getApprovedPicks()
      .then(data => {
        setPicks(data)
        // Fetch explanations in parallel after picks load — fail silently
        data.forEach(pick => {
          fetch(`${API_URL}/explanations/${pick.id}`)
            .then(res => {
              if (!res.ok) return
              return res.json()
            })
            .then(json => {
              if (json?.explanation_short) {
                setExplanations(prev => ({ ...prev, [pick.id]: json.explanation_short }))
              }
            })
            .catch(() => {})
        })
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-10">
        <div className="h-20 bg-[#1a1a1a] rounded-xl animate-pulse mb-6" />
        <div className="h-64 bg-[#1a1a1a] rounded-xl animate-pulse" />
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-10">
      <h1 className="text-xl font-bold text-white mb-6">Pick History</h1>

      {picks.length === 0 ? (
        <p className="text-gray-500 text-sm">No approved picks yet.</p>
      ) : (
        <>
          <SummaryBar picks={picks} />

          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="text-gray-400 text-xs border-b border-[#222222]">
                  <th className="text-left py-2 pr-4">Week</th>
                  <th className="text-left py-2 pr-4">Matchup</th>
                  <th className="text-left py-2 pr-4">Pick</th>
                  <th className="text-left py-2 pr-4">Win Prob</th>
                  <th className="text-left py-2 pr-4">Confidence</th>
                  <th className="text-left py-2 pr-4">Pick Spread</th>
                  <th className="text-left py-2 pr-4">Model Line</th>
                  <th className="text-left py-2 pr-4">Outcome</th>
                  <th className="text-left py-2 pr-4">ATS</th>
                  <th className="text-left py-2">CLV</th>
                </tr>
              </thead>
              <tbody>
                {picks.map(pick => {
                  const atsColor     = ATS_COLOR[pick.ats_result] ?? 'text-gray-500'
                  const aiText       = explanations[pick.id] ?? null
                  const isHome       = pick.pick_team === pick.home_team
                  const pickSpread   = isHome ? pick.spread : -1 * pick.spread
                  const modelImplied = isHome
                    ? -1 * (pick.win_probability - 0.5) * 28
                    : (pick.win_probability - 0.5) * 28
                  const formatSpread = (val) => {
                    const rounded = Number(val).toFixed(1)
                    return val > 0 ? `+${rounded}` : `${rounded}`
                  }
                  return (
                    <>
                      <tr key={pick.id} className="border-b border-[#1a1a1a] hover:bg-[#111111] transition-colors">
                        <td className="py-3 pr-4 text-gray-300">{pick.week}</td>
                        <td className="py-3 pr-4 text-gray-300 whitespace-nowrap">
                          {pick.away_team} @ {pick.home_team}
                        </td>
                        <td className="py-3 pr-4 text-[#CFB526] font-medium">{pick.pick_team}</td>
                        <td className="py-3 pr-4 text-white">
                          {pick.win_probability !== ''
                            ? `${(pick.win_probability * 100).toFixed(1)}%`
                            : '—'}
                        </td>
                        <td className="py-3 pr-4">
                          <span className="text-xs text-gray-300">{pick.confidence_label || '—'}</span>
                        </td>
                        <td className="py-3 pr-4 text-gray-300">
                          {pick.spread !== '' ? formatSpread(pickSpread) : '—'}
                        </td>
                        <td className="py-3 pr-4 text-gray-300">
                          {pick.spread !== '' ? formatSpread(modelImplied) : '—'}
                        </td>
                        <td className="py-3 pr-4">
                          <span className={pick.outcome === 'WIN' ? 'text-green-400' : pick.outcome === 'LOSS' ? 'text-red-400' : 'text-gray-500'}>
                            {pick.outcome || '—'}
                          </span>
                        </td>
                        <td className={`py-3 pr-4 font-medium ${atsColor}`}>
                          {pick.ats_result || '—'}
                        </td>
                        <td className="py-3 text-gray-300">
                          {pick.clv !== '' && pick.clv !== null ? `${Number(pick.clv).toFixed(2)}` : '—'}
                        </td>
                      </tr>
                      {aiText && (
                        <tr key={`${pick.id}-ai`} className="border-b border-[#1a1a1a]">
                          <td colSpan={10} className="pb-3 pt-0 px-0">
                            <p className="text-xs text-gray-500 mb-0.5">AI Analysis</p>
                            <p className="text-xs text-gray-400 leading-relaxed">{aiText}</p>
                          </td>
                        </tr>
                      )}
                    </>
                  )
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
