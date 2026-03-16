/**
 * GameCard component — clickable card displaying a single CFB game.
 * Shows teams, score (if completed), and allows fetching win probability predictions.
 */
import { useState } from 'react'
import { getMatchup } from '../api/client'
import WinProbGauge from './WinProbGauge'
import ConfidenceBadge from './ConfidenceBadge'

/**
 * Card for a single game with prediction-on-click functionality.
 * @param {Object} props
 * @param {Object} props.game - Game data object.
 * @param {string} props.game.homeTeam - Home team name.
 * @param {string} props.game.awayTeam - Away team name.
 * @param {number|null} props.game.homePoints - Home team score.
 * @param {number|null} props.game.awayPoints - Away team score.
 * @param {boolean} props.game.neutralSite - Whether game is at a neutral site.
 * @param {string} props.game.homeConference - Home team conference.
 * @param {string} props.game.awayConference - Away team conference.
 * @param {string} props.game.awayClassification - Away team classification (e.g. 'fcs').
 * @param {boolean} props.game.completed - Whether the game has been played.
 * @returns {JSX.Element} The game card.
 */
export default function GameCard({ game }) {
  const {
    homeTeam,
    awayTeam,
    homePoints,
    awayPoints,
    neutralSite,
    awayClassification,
    completed,
  } = game

  const [prediction, setPrediction] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  /** Determine if home team won (for gold score styling). */
  const homeWon = completed && homePoints != null && awayPoints != null && homePoints > awayPoints
  const awayWon = completed && homePoints != null && awayPoints != null && awayPoints > homePoints

  /**
   * Fetch win probability prediction from the API.
   */
  async function handleGetPrediction() {
    setLoading(true)
    setError(null)
    setPrediction(null)
    try {
      const data = await getMatchup(homeTeam, awayTeam, 2025)
      setPrediction(data)
    } catch (err) {
      setError('Prediction unavailable — team may not be in model.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-[#111111] border border-[#222222] rounded-xl p-4 flex flex-col gap-3">
      {/* Header badges */}
      <div className="flex items-center gap-2 flex-wrap">
        {awayClassification === 'fcs' && (
          <span className="bg-gray-700 text-gray-300 text-xs font-medium px-2 py-0.5 rounded">
            FCS
          </span>
        )}
        {neutralSite && (
          <span className="bg-gray-600 text-gray-200 text-xs font-medium px-2 py-0.5 rounded">
            Neutral Site
          </span>
        )}
      </div>

      {/* Teams row */}
      <div className="flex flex-col gap-1">
        {/* Away team */}
        <div className="flex items-center justify-between">
          <span className={`font-semibold text-sm ${awayWon ? 'text-[#C9A84C]' : 'text-white'}`}>
            {awayTeam}
          </span>
          {completed && awayPoints != null && (
            <span className={`font-bold text-lg ${awayWon ? 'text-[#C9A84C]' : 'text-gray-400'}`}>
              {awayPoints}
            </span>
          )}
        </div>

        {/* Home team */}
        <div className="flex items-center justify-between">
          <span className={`font-semibold text-sm ${homeWon ? 'text-[#C9A84C]' : 'text-white'}`}>
            {homeTeam} <span className="text-gray-500 text-xs font-normal">(Home)</span>
          </span>
          {completed && homePoints != null && (
            <span className={`font-bold text-lg ${homeWon ? 'text-[#C9A84C]' : 'text-gray-400'}`}>
              {homePoints}
            </span>
          )}
        </div>

        {completed && (
          <p className="text-gray-500 text-xs mt-1">Final</p>
        )}
      </div>

      {/* Get Prediction button */}
      <button
        onClick={handleGetPrediction}
        disabled={loading}
        className="bg-[#C9A84C] text-black font-semibold rounded px-4 py-2 text-sm hover:bg-[#b8963e] transition-colors disabled:opacity-60 disabled:cursor-not-allowed self-start"
      >
        {loading ? 'Loading...' : 'Get Prediction'}
      </button>

      {/* Loading spinner */}
      {loading && (
        <div className="flex justify-center py-4">
          <div className="w-6 h-6 border-2 border-[#C9A84C] border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Error message */}
      {error && (
        <p className="text-red-400 text-xs">{error}</p>
      )}

      {/* Prediction result */}
      {prediction && !loading && (
        <div className="flex flex-col items-center gap-2 pt-2 border-t border-[#222222]">
          <WinProbGauge
            homeProb={prediction.home_win_probability ?? 0.5}
            homeName={homeTeam}
            awayName={awayTeam}
          />
          <ConfidenceBadge
            homeProb={prediction.home_win_probability ?? 0.5}
          />
        </div>
      )}
    </div>
  )
}
