/** API client for CFB Agent backend. */
const BASE       = import.meta.env.VITE_API_URL
const ADMIN_KEY  = import.meta.env.VITE_ADMIN_API_KEY ?? ''

const authHeaders = () => ({
  'Content-Type':  'application/json',
  'Authorization': `Bearer ${ADMIN_KEY}`,
})

/**
 * Fetch games for a given week.
 * @param {number} week - The week number (1–15).
 * @returns {Promise<Object[]>} Array of game objects.
 */
export async function getGames(week) {
  const res = await fetch(`${BASE}/games?week=${week}`)
  return res.json()
}

/**
 * Fetch win probability matchup data.
 * @param {string} home - Home team name.
 * @param {string} away - Away team name.
 * @param {number} [season=2025] - Season year.
 * @returns {Promise<Object>} Matchup prediction object.
 */
export async function getMatchup(home, away, season = 2025) {
  const res = await fetch(
    `${BASE}/matchup?home=${encodeURIComponent(home)}&away=${encodeURIComponent(away)}&season=${season}`
  )
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

/**
 * Fetch power rankings for all FBS teams.
 * @returns {Promise<Object[]>} Array of team ranking objects.
 */
export async function getRankings() {
  const res = await fetch(`${BASE}/rankings`)
  return res.json()
}

// ---------------------------------------------------------------------------
// Picks — admin endpoints
// ---------------------------------------------------------------------------

/**
 * Fetch picks that are not yet approved or rejected.
 * @returns {Promise<Object[]>}
 */
export async function getPendingPicks() {
  const res = await fetch(`${BASE}/picks/pending`)
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

/**
 * Approve a pick by UUID.
 * @param {string} pickId
 * @returns {Promise<Object>}
 */
export async function approvePick(pickId) {
  const res = await fetch(`${BASE}/picks/${pickId}/approve`, {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

/**
 * Reject a pick by UUID.
 * @param {string} pickId
 * @returns {Promise<Object>}
 */
export async function rejectPick(pickId) {
  const res = await fetch(`${BASE}/picks/${pickId}/reject`, {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

/**
 * Fetch all approved picks.
 * @returns {Promise<Object[]>}
 */
export async function getApprovedPicks() {
  const res = await fetch(`${BASE}/picks/approved`)
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

/**
 * Fetch weekly game predictions with model vs Vegas comparison (no auth required).
 * @param {number} season - Season year.
 * @param {number} week - Week number (1–15).
 * @returns {Promise<Object[]>} Array of game prediction objects sorted by model_edge desc.
 */
export async function getWeeklyGames(season, week) {
  const res = await fetch(`${BASE}/games/weekly?season=${season}&week=${week}`)
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

/**
 * Fetch public approved picks for a season/week (no auth required).
 * @param {number} season - Season year.
 * @param {number|null} [week] - Week number. Omit to get most recent week with picks.
 * @returns {Promise<Object[]>}
 */
export async function getPublicPicks(season, week = null) {
  const url = week != null
    ? `${BASE}/picks/public?season=${season}&week=${week}`
    : `${BASE}/picks/public?season=${season}`
/**
 * Generic API helper for simple GET/POST requests.
 */
const api = {
  async get(path) {
    const res = await fetch(`${BASE}${path}`)
    if (!res.ok) throw new Error(`${res.status}`)
    return res.json()
  },
  async post(path, body) {
    const res = await fetch(`${BASE}${path}`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(body)
    })
    if (!res.ok) throw new Error(`${res.status}`)
    return res.json()
  }
}

export default api
