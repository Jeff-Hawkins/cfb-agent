/**
 * ConfidenceBadge component — displays a colored badge indicating prediction confidence.
 * Confidence tiers: Toss-Up, Lean, Moderate, Strong based on gap from 50%.
 */

/**
 * Badge showing prediction confidence level.
 * @param {Object} props
 * @param {number} props.homeProb - Home win probability as a float (0–1).
 * @returns {JSX.Element} The confidence badge.
 */
export default function ConfidenceBadge({ homeProb }) {
  const gap = Math.abs(homeProb - 0.5) * 2

  let label, className

  if (gap < 0.10) {
    label = 'Toss-Up'
    className = 'bg-gray-700 text-gray-200'
  } else if (gap < 0.30) {
    label = 'Lean'
    className = 'bg-blue-800 text-blue-100'
  } else if (gap < 0.50) {
    label = 'Moderate'
    className = 'bg-[#C9A84C] text-black'
  } else {
    label = 'Strong'
    className = 'bg-green-700 text-green-100'
  }

  return (
    <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${className}`}>
      {label}
    </span>
  )
}
