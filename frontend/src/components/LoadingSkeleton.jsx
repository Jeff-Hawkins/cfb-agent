/**
 * LoadingSkeleton component — animated placeholder cards shown while data is loading.
 */

/**
 * Renders a grid of skeleton placeholder cards.
 * @param {Object} props
 * @param {number} [props.count=6] - Number of skeleton cards to render.
 * @returns {JSX.Element} Grid of skeleton cards.
 */
export default function LoadingSkeleton({ count = 6 }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="bg-[#111111] border border-[#222222] rounded-xl h-40 animate-pulse"
        />
      ))}
    </>
  )
}
