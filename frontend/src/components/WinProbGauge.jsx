/**
 * WinProbGauge component — displays home win probability as a radial bar chart.
 * Uses Recharts RadialBarChart with a gold fill and centered percentage label.
 */
import { RadialBarChart, RadialBar, ResponsiveContainer, PolarAngleAxis } from 'recharts'

/**
 * Radial gauge showing home win probability.
 * @param {Object} props
 * @param {number} props.homeProb - Home win probability as a float (0–1).
 * @param {string} props.homeName - Home team name.
 * @param {string} props.awayName - Away team name.
 * @returns {JSX.Element} The win probability gauge.
 */
export default function WinProbGauge({ homeProb, homeName, awayName }) {
  const homePercent = Math.round(homeProb * 100)
  const awayPercent = 100 - homePercent

  const data = [{ value: homePercent, fill: '#C9A84C' }]

  return (
    <div className="flex flex-col items-center">
      {/* Radial bar chart */}
      <div className="relative w-[200px] h-[200px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%"
            cy="50%"
            innerRadius="60%"
            outerRadius="90%"
            startAngle={90}
            endAngle={-270}
            barSize={16}
            data={data}
          >
            <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
            <RadialBar
              dataKey="value"
              cornerRadius={8}
              background={{ fill: '#222222' }}
            />
          </RadialBarChart>
        </ResponsiveContainer>

        {/* Center percentage label */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-bold text-white">{homePercent}%</span>
        </div>
      </div>

      {/* Team labels below gauge */}
      <div className="flex justify-between w-full mt-2 px-2">
        <div className="text-left">
          <span className="text-[#C9A84C] font-semibold text-sm">{homePercent}%</span>
          <p className="text-gray-400 text-xs truncate max-w-[80px]">{homeName}</p>
        </div>
        <div className="text-right">
          <span className="text-gray-300 font-semibold text-sm">{awayPercent}%</span>
          <p className="text-gray-400 text-xs truncate max-w-[80px]">{awayName}</p>
        </div>
      </div>
    </div>
  )
}
