/**
 * RankingsPage — displays power rankings for all FBS teams.
 * Features sortable columns, conference filter, and gold left border for top 25.
 */
import { useState, useEffect, useMemo } from 'react'
import { getRankings } from '../api/client'
import LoadingSkeleton from '../components/LoadingSkeleton'

/**
 * Page showing sortable FBS power rankings with conference filter.
 * @returns {JSX.Element} The rankings page.
 */
export default function RankingsPage() {
  const [teams, setTeams] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [conferenceFilter, setConferenceFilter] = useState('All')
  const [sortKey, setSortKey] = useState('rank')
  const [sortDir, setSortDir] = useState('asc')

  useEffect(() => {
    getRankings()
      .then((data) => {
        setTeams(Array.isArray(data) ? data : [])
        setLoading(false)
      })
      .catch(() => {
        setError('Failed to load rankings.')
        setLoading(false)
      })
  }, [])

  /** Extract unique conferences from team data. */
  const conferences = useMemo(() => {
    const set = new Set(teams.map((t) => t.conference).filter(Boolean))
    return ['All', ...Array.from(set).sort()]
  }, [teams])

  /** Filter and sort teams. */
  const displayedTeams = useMemo(() => {
    let filtered = conferenceFilter === 'All'
      ? teams
      : teams.filter((t) => t.conference === conferenceFilter)

    return [...filtered].sort((a, b) => {
      const aVal = a[sortKey] ?? 0
      const bVal = b[sortKey] ?? 0

      if (typeof aVal === 'string') {
        return sortDir === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal)
      }
      return sortDir === 'asc' ? aVal - bVal : bVal - aVal
    })
  }, [teams, conferenceFilter, sortKey, sortDir])

  /**
   * Handle column header click to sort.
   * @param {string} key - Column key to sort by.
   */
  function handleSort(key) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  /** Render a sort indicator arrow. */
  function SortArrow({ col }) {
    if (sortKey !== col) return <span className="text-gray-600 ml-1">↕</span>
    return <span className="text-[#C9A84C] ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-white mb-2">Power Rankings</h1>
      <p className="text-gray-400 text-sm mb-6">2025 Preseason Composite Rating — 136 FBS Teams</p>

      {/* Conference filter */}
      <div className="flex items-center gap-4 mb-6">
        <label htmlFor="conf-select" className="text-gray-300 text-sm font-medium">
          Conference
        </label>
        <select
          id="conf-select"
          value={conferenceFilter}
          onChange={(e) => setConferenceFilter(e.target.value)}
          className="bg-[#111111] border border-[#222222] text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#C9A84C]"
        >
          {conferences.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {/* Error state */}
      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      {/* Loading skeletons */}
      {loading && (
        <div className="grid grid-cols-1 gap-3">
          <LoadingSkeleton count={10} />
        </div>
      )}

      {/* Rankings table */}
      {!loading && !error && (
        <div className="overflow-x-auto rounded-xl border border-[#222222]">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[#111111] border-b border-[#222222]">
                {[
                  { key: 'rank', label: 'Rank' },
                  { key: 'team', label: 'Team' },
                  { key: 'conference', label: 'Conference' },
                  { key: 'rating', label: 'Rating' },
                ].map(({ key, label }) => (
                  <th
                    key={key}
                    onClick={() => handleSort(key)}
                    className="px-4 py-3 text-left text-gray-400 font-medium cursor-pointer hover:text-white select-none"
                  >
                    {label}
                    <SortArrow col={key} />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayedTeams.length === 0 ? (
                <tr>
                  <td colSpan={4} className="text-center py-12 text-gray-500">
                    No teams found.
                  </td>
                </tr>
              ) : (
                displayedTeams.map((team, idx) => {
                  const originalRank = team.rank ?? idx + 1
                  const isTopTwentyFive = originalRank <= 25

                  return (
                    <tr
                      key={team.team ?? idx}
                      className={`border-b border-[#1a1a1a] hover:bg-[#1a1a1a] transition-colors ${
                        isTopTwentyFive ? 'border-l-4 border-l-[#C9A84C]' : 'border-l-4 border-l-transparent'
                      }`}
                    >
                      <td className="px-4 py-3 text-white font-semibold">
                        {originalRank}
                      </td>
                      <td className="px-4 py-3 text-white font-medium">
                        {team.team}
                      </td>
                      <td className="px-4 py-3 text-gray-400">
                        {team.conference || '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-300">
                        {typeof team.rating === 'number'
                          ? team.rating.toFixed(3)
                          : team.rating ?? '—'}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
