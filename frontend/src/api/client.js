/** API client for CFB Agent backend. */
const BASE = import.meta.env.VITE_API_URL;

/**
 * Fetch games for a given week.
 * @param {number} week - The week number (1–15).
 * @returns {Promise<Object[]>} Array of game objects.
 */
export async function getGames(week) {
  const res = await fetch(`${BASE}/games?week=${week}`);
  return res.json();
}

/**
 * Fetch win probability matchup data.
 * @param {string} home - Home team name.
 * @param {string} away - Away team name.
 * @param {number} [season=2025] - Season year.
 * @returns {Promise<Object>} Matchup prediction object.
 */
export async function getMatchup(home, away, season = 2025) {
  const res = await fetch(`${BASE}/matchup?home=${encodeURIComponent(home)}&away=${encodeURIComponent(away)}&season=${season}`);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

/**
 * Fetch power rankings for all FBS teams.
 * @returns {Promise<Object[]>} Array of team ranking objects.
 */
export async function getRankings() {
  const res = await fetch(`${BASE}/rankings`);
  return res.json();
}
