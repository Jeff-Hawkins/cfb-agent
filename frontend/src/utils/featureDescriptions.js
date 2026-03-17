/**
 * FEATURE_DESCRIPTIONS — labels and descriptions for all 23 model features.
 *
 * Kept in sync with FEATURE_DESCRIPTIONS in tools/explanation_generator.py.
 * Keys match the feature_cols list from models/saved/feature_cols.pkl exactly.
 */
export const FEATURE_DESCRIPTIONS = {
  home_rushingYards: {
    label: 'Home Rushing Yards',
    description: 'Season rushing yards per game for the home team.',
  },
  away_rushingYards: {
    label: 'Away Rushing Yards',
    description: 'Season rushing yards per game for the away team.',
  },
  diff_rushingYards: {
    label: 'Rushing Yards Diff',
    description: 'Home minus away rushing yards per game differential.',
  },
  home_turnovers: {
    label: 'Home Turnovers',
    description: 'Season turnover total for the home team.',
  },
  away_turnovers: {
    label: 'Away Turnovers',
    description: 'Season turnover total for the away team.',
  },
  diff_turnovers: {
    label: 'Turnovers Diff',
    description:
      'Home minus away turnover differential (positive = home turns it over more).',
  },
  home_fumblesLost: {
    label: 'Home Fumbles Lost',
    description: 'Season fumbles lost by the home team.',
  },
  away_fumblesLost: {
    label: 'Away Fumbles Lost',
    description: 'Season fumbles lost by the away team.',
  },
  diff_fumblesLost: {
    label: 'Fumbles Lost Diff',
    description: 'Home minus away fumbles-lost differential.',
  },
  sp_overall_diff: {
    label: 'SP+ Overall Diff',
    description:
      'Home minus away SP+ overall rating. Positive = home team is rated better overall.',
  },
  sp_off_vs_def: {
    label: 'SP+ Off vs Def',
    description:
      'Home offense SP+ rating minus away defense SP+ rating. Positive = home offense has an edge.',
  },
  sp_def_vs_off: {
    label: 'SP+ Def vs Off',
    description:
      'Away offense SP+ rating minus home defense SP+ rating. Lower = better for the home team.',
  },
  sp_special_diff: {
    label: 'SP+ Special Teams Diff',
    description: 'Home minus away special teams SP+ rating differential.',
  },
  rec_3yr_diff: {
    label: '3-Year Recruiting Avg Diff',
    description:
      'Difference in 3-year rolling average recruiting class points (home minus away).',
  },
  ret_ppa_diff: {
    label: 'Returning Production PPA Diff',
    description: 'Home minus away returning production total PPA differential.',
  },
  ret_pct_diff: {
    label: 'Returning Production % Diff',
    description: 'Home minus away returning production percentage differential.',
  },
  home_new_coach: {
    label: 'Home New Coach',
    description:
      '1 if the home team has a coach in their first year at this school, 0 otherwise.',
  },
  away_new_coach: {
    label: 'Away New Coach',
    description:
      '1 if the away team has a coach in their first year at this school, 0 otherwise.',
  },
  coach_win_pct_diff: {
    label: 'Coach Career Win % Diff',
    description:
      'Home coach career win percentage minus away coach career win percentage.',
  },
  elo_diff: {
    label: 'Elo Rating Diff',
    description:
      'Home minus away end-of-prior-season Elo rating differential.',
  },
  talent_diff: {
    label: 'Talent Composite Diff',
    description: 'Home minus away team talent composite score differential.',
  },
  neutral_site: {
    label: 'Neutral Site',
    description: '1 if the game is played at a neutral site, 0 otherwise.',
  },
  home_field: {
    label: 'Home Field Advantage',
    description:
      '1 if the home team has a true home-field advantage (not neutral site), 0 otherwise.',
  },
}
