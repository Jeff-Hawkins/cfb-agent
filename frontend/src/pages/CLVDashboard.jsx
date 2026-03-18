import { useState, useEffect } from 'react'
import { api } from '../api/client'

export default function CLVDashboard() {
  const [summary, setSummary] = useState(null)
  const [picks, setPicks] = useState([])
  const [loading, setLoading] = useState(true)
  const season = 2025 // Production default

  useEffect(() => {
    async function fetchData() {
      try {
        const [summaryRes, picksRes] = await Promise.all([
          api.get(`/clv/summary?season=${season}`),
          api.get(`/clv/picks?season=${season}`)
        ])
        setSummary(summaryRes)
        setPicks(picksRes)
      } catch (err) {
        console.error('Failed to fetch CLV data:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-12">
        <div className="animate-pulse space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-32 bg-white/5 rounded-xl" />
            ))}
          </div>
          <div className="h-96 bg-white/5 rounded-xl" />
        </div>
      </div>
    )
  }

  if (!picks.length) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-24 text-center">
        <h1 className="text-3xl font-bold mb-4">CLV Dashboard</h1>
        <p className="text-white/60 text-lg">
          CLV tracking begins once picks have completed games.<br />
          Check back after Week 1.
        </p>
      </div>
    )
  }

  const winCount = picks.filter(p => p.outcome === 'WIN').length
  const lossCount = picks.filter(p => p.outcome === 'LOSS').length

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2 text-[#d4af37]">CLV Dashboard</h1>
        <p className="text-white/60">Closing Line Value Tracking — Season {season}</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white/5 border border-white/10 rounded-xl p-6 text-center">
          <div className="text-4xl font-bold mb-1 text-white">
            {summary?.clv_positive_pct}%
          </div>
          <div className="text-sm font-semibold uppercase tracking-wider text-white/40 mb-2">
            Beating the Market
          </div>
          <div className="text-xs text-white/60">of picks beat the closing line</div>
        </div>

        <div className="bg-white/5 border border-white/10 rounded-xl p-6 text-center">
          <div className="text-4xl font-bold mb-1 text-white">
            {summary?.avg_clv > 0 ? '+' : ''}{summary?.avg_clv}
          </div>
          <div className="text-sm font-semibold uppercase tracking-wider text-white/40 mb-2">
            Avg CLV
          </div>
          <div className="text-xs text-white/60">average edge secured per pick</div>
        </div>

        <div className="bg-white/5 border border-white/10 rounded-xl p-6 text-center">
          <div className="text-4xl font-bold mb-1 text-white">
            {winCount}-{lossCount}
          </div>
          <div className="text-sm font-semibold uppercase tracking-wider text-white/40 mb-2">
            Pick Record
          </div>
          <div className="text-xs text-white/60">straight-up record on flagged picks</div>
        </div>
      </div>

      {/* Explainer */}
      <div className="bg-[#d4af37]/10 border border-[#d4af37]/20 rounded-lg p-4 mb-12">
        <p className="text-sm text-[#d4af37]/90 leading-relaxed">
          <span className="font-bold uppercase mr-2">What is CLV?</span>
          Closing Line Value (CLV) measures whether our model secured a better number than where the market settled before kickoff. 
          Consistently beating the closing line is the strongest signal of long-term betting edge — more reliable than win rate alone.
        </p>
      </div>

      {/* Pick Table */}
      <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/10 bg-white/5">
              <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-white/40">Week</th>
              <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-white/40">Game</th>
              <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-white/40">Pick</th>
              <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-white/40">Pick Spread</th>
              <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-white/40">Closing Line</th>
              <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-white/40">CLV</th>
              <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-white/40">Outcome</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {picks.map((p) => (
              <tr key={p.game_id} className="hover:bg-white/[0.02] transition-colors">
                <td className="px-6 py-4 text-sm font-medium">{p.week}</td>
                <td className="px-6 py-4">
                  <div className="text-sm font-medium">{p.away_team} @ {p.home_team}</div>
                </td>
                <td className="px-6 py-4 text-sm font-medium text-white/80">{p.pick_team}</td>
                <td className="px-6 py-4 text-sm font-mono">{p.pick_spread > 0 ? '+' : ''}{p.pick_spread}</td>
                <td className="px-6 py-4 text-sm font-mono">{p.closing_spread > 0 ? '+' : ''}{p.closing_spread}</td>
                <td className={`px-6 py-4 text-sm font-bold ${p.clv > 0 ? 'text-green-400' : p.clv < 0 ? 'text-red-400' : 'text-white/40'}`}>
                  {p.clv > 0 ? '+' : ''}{p.clv}
                </td>
                <td className="px-6 py-4">
                  {p.outcome ? (
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      p.outcome === 'WIN' ? 'bg-green-500/10 text-green-400 border border-green-500/20' :
                      p.outcome === 'LOSS' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                      'bg-white/10 text-white/60 border border-white/20'
                    }`}>
                      {p.outcome}
                    </span>
                  ) : (
                    <span className="text-xs text-white/40">Pending</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
