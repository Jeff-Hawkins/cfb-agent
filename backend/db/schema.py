"""SQLAlchemy table definitions for the CFB agent PostgreSQL database.

All tables mirror the column names and types used by the CFBD API fetchers.
Call create_all_tables() once at startup to ensure every table exists before
any data is written.
"""

from sqlalchemy import (
    BigInteger, Boolean, Column, Float, MetaData, Table, Text, Integer, Numeric, DateTime, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from db.database import engine

metadata = MetaData()

games = Table(
    "games", metadata,
    Column("id",                         BigInteger),
    Column("season",                     BigInteger),
    Column("week",                       BigInteger),
    Column("seasonType",                 Text),
    Column("startDate",                  Text),
    Column("startTimeTBD",               Boolean),
    Column("completed",                  Boolean),
    Column("neutralSite",                Boolean),
    Column("conferenceGame",             Boolean),
    Column("attendance",                 Float),
    Column("venueId",                    Float),
    Column("venue",                      Text),
    Column("homeId",                     BigInteger),
    Column("homeTeam",                   Text),
    Column("homeClassification",         Text),
    Column("homeConference",             Text),
    Column("homePoints",                 BigInteger),
    Column("homeLineScores",             Text),
    Column("homePostgameWinProbability", Float),
    Column("homePregameElo",             Float),
    Column("homePostgameElo",            Float),
    Column("awayId",                     BigInteger),
    Column("awayTeam",                   Text),
    Column("awayClassification",         Text),
    Column("awayConference",             Text),
    Column("awayPoints",                 BigInteger),
    Column("awayLineScores",             Text),
    Column("awayPostgameWinProbability", Float),
    Column("awayPregameElo",             Float),
    Column("awayPostgameElo",            Float),
    Column("excitementIndex",            Float),
    Column("highlights",                 Text),
    Column("notes",                      Text),
)

team_stats = Table(
    "team_stats", metadata,
    Column("season",     BigInteger),
    Column("team",       Text),
    Column("conference", Text),
    Column("statName",   Text),
    Column("statValue",  BigInteger),
)

betting_lines = Table(
    "betting_lines", metadata,
    Column("game_id",         BigInteger),
    Column("season",          BigInteger),
    Column("week",            BigInteger),
    Column("home_team",       Text),
    Column("away_team",       Text),
    Column("home_score",      Float),
    Column("away_score",      Float),
    Column("spread",          Float),
    Column("spread_open",     Float),
    Column("over_under",      Float),
    Column("over_under_open", Float),
    Column("home_moneyline",  Float),
    Column("away_moneyline",  Float),
)

sp_ratings = Table(
    "sp_ratings", metadata,
    Column("year",                    BigInteger),
    Column("team",                    Text),
    Column("conference",              Text),
    Column("rating",                  Float),
    Column("ranking",                 Float),
    Column("secondOrderWins",         Text),
    Column("sos",                     Text),
    Column("offense_ranking",         Float),
    Column("offense_rating",          Float),
    Column("offense_success",         Text),
    Column("offense_explosiveness",   Text),
    Column("offense_rushing",         Text),
    Column("offense_passing",         Text),
    Column("offense_standardDowns",   Text),
    Column("offense_passingDowns",    Text),
    Column("offense_runRate",         Text),
    Column("offense_pace",            Text),
    Column("defense_ranking",         Float),
    Column("defense_rating",          Float),
    Column("defense_success",         Text),
    Column("defense_explosiveness",   Text),
    Column("defense_rushing",         Text),
    Column("defense_passing",         Text),
    Column("defense_standardDowns",   Text),
    Column("defense_passingDowns",    Text),
    Column("defense_havoc_total",     Text),
    Column("defense_havoc_frontSeven",Text),
    Column("defense_havoc_db",        Text),
    Column("specialTeams_rating",     Text),
)

recruiting_rankings = Table(
    "recruiting_rankings", metadata,
    Column("year",   BigInteger),
    Column("team",   Text),
    Column("rank",   BigInteger),
    Column("points", Float),
)

returning_production = Table(
    "returning_production", metadata,
    Column("season",              BigInteger),
    Column("team",                Text),
    Column("conference",          Text),
    Column("totalPPA",            Float),
    Column("totalPassingPPA",     Float),
    Column("totalReceivingPPA",   Float),
    Column("totalRushingPPA",     Float),
    Column("percentPPA",          Float),
    Column("percentPassingPPA",   Float),
    Column("percentReceivingPPA", Float),
    Column("percentRushingPPA",   Float),
    Column("usage",               Float),
    Column("passingUsage",        Float),
    Column("receivingUsage",      Float),
    Column("rushingUsage",        Float),
)

coaches = Table(
    "coaches", metadata,
    Column("firstName",      Text),
    Column("lastName",       Text),
    Column("hireDate",       Text),
    Column("school",         Text),
    Column("year",           BigInteger),
    Column("games",          BigInteger),
    Column("wins",           BigInteger),
    Column("losses",         BigInteger),
    Column("ties",           BigInteger),
    Column("preseasonRank",  Float),
    Column("postseasonRank", Float),
)

portal_players = Table(
    "portal_players", metadata,
    Column("season",         BigInteger),
    Column("firstName",      Text),
    Column("lastName",       Text),
    Column("position",       Text),
    Column("origin",         Text),
    Column("destination",    Text),
    Column("transferDate",   Text),
    Column("rating",         Float),
    Column("stars",          Float),
    Column("eligibility",    Text),
    Column("elig_weight",    Float),
    Column("weighted_stars", Float),
)

portal_net_ratings = Table(
    "portal_net_ratings", metadata,
    Column("season",          BigInteger),
    Column("team",            Text),
    Column("stars_in",        Float),
    Column("stars_out",       Float),
    Column("net_portal_score",Float),
)

preseason_2026 = Table(
    "preseason_2026", metadata,
    Column("team",                    Text),
    Column("sp_rating",               Float),
    Column("rec_3yr_avg",             Float),
    Column("ret_ppa",                 Float),
    Column("portal_net",              Float),
    Column("coach",                   Text),
    Column("n_seasons",               Float),
    Column("results_alpha",           Float),
    Column("portal_roi",              Float),
    Column("yoy_improvement",         Float),
    Column("coach_effectiveness_score",Float),
    Column("sp_z",                    Float),
    Column("rec_z",                   Float),
    Column("ret_z",                   Float),
    Column("portal_z",                Float),
    Column("coaching_z",              Float),
    Column("composite",               Float),
    Column("composite_100",           Float),
)


elo_ratings = Table(
    "elo_ratings", metadata,
    Column("year",        BigInteger),
    Column("team",        Text),
    Column("conference",  Text),
    Column("elo",         BigInteger),
)


advanced_stats = Table(
    "advanced_stats", metadata,
    Column("team",                Text),
    Column("season",              BigInteger),
    Column("offense_lineYards",   Float),
    Column("defense_stuffRate",   Float),
    Column("success_rate",        Float),
    Column("defense_havoc_total", Float),
)

drives = Table(
    "drives", metadata,
    Column("id",                 Text),
    Column("gameId",             BigInteger),
    Column("offense",            Text),
    Column("offenseConference",  Text),
    Column("defense",            Text),
    Column("defenseConference",  Text),
    Column("driveNumber",        BigInteger),
    Column("scoring",            Boolean),
    Column("startPeriod",        BigInteger),
    Column("startYardline",      BigInteger),
    Column("startYardsToGoal",   BigInteger),
    Column("startTime",          Text),
    Column("endPeriod",          BigInteger),
    Column("endYardline",        BigInteger),
    Column("endYardsToGoal",     BigInteger),
    Column("endTime",            Text),
    Column("elapsed",            Text),
    Column("plays",              BigInteger),
    Column("yards",              BigInteger),
    Column("driveResult",        Text),
    Column("isHomeOffense",      Boolean),
    Column("startOffenseScore",  BigInteger),
    Column("startDefenseScore",  BigInteger),
    Column("endOffenseScore",    BigInteger),
    Column("endDefenseScore",    BigInteger),
)

pregame_wp = Table(
    "pregame_wp", metadata,
    Column("season",             BigInteger),
    Column("week",               BigInteger),
    Column("seasonType",         Text),
    Column("gameId",             BigInteger),
    Column("homeTeam",           Text),
    Column("awayTeam",           Text),
    Column("spread",             Float),
    Column("homeWinProbability", Float),
)

# Phase 7 & 8A tables

game_outcomes = Table(
    "game_outcomes", metadata,
    Column("game_id",      Text, primary_key=True),
    Column("home_team",    Text),
    Column("away_team",    Text),
    Column("home_score",   Integer),
    Column("away_score",   Integer),
    Column("game_result",  Text),
    Column("ats_result",   Text),
    Column("home_covered", Boolean),
    Column("away_covered", Boolean),
    Column("fetched_at",   TIMESTAMP(timezone=True)),
)

closing_lines = Table(
    "closing_lines", metadata,
    Column("game_id",        Text, primary_key=True),
    Column("season",         Integer),
    Column("week",           Integer),
    Column("home_team",      Text),
    Column("away_team",      Text),
    Column("closing_spread", Numeric),
    Column("closing_total",  Numeric),
    Column("source",         Text),
    Column("snapped_at",     TIMESTAMP(timezone=True)),
)

clv_records = Table(
    "clv_records", metadata,
    Column("id",             UUID(as_uuid=True), primary_key=True),
    Column("pick_id",        UUID(as_uuid=True)),
    Column("game_id",        Text),
    Column("pick_team",      Text),
    Column("pick_spread",    Numeric),
    Column("closing_spread", Numeric),
    Column("clv",            Numeric),
    Column("clv_positive",   Boolean),
    Column("outcome",        Text),
    Column("recorded_at",    TIMESTAMP(timezone=True)),
)

cron_log = Table(
    "cron_log", metadata,
    Column("id",              UUID(as_uuid=True), primary_key=True),
    Column("job_name",        Text),
    Column("run_at",          TIMESTAMP(timezone=True)),
    Column("records_updated", Integer),
    Column("errors",          Text),
    Column("status",          Text),
)

pick_explanations = Table(
    "pick_explanations", metadata,
    Column("id",                Integer, primary_key=True),
    Column("pick_id",           UUID(as_uuid=True)),
    Column("explanation_short", Text),
    Column("explanation_full",  Text),
    Column("feature_snapshot",  JSONB),
    Column("model_version",     Text),
    Column("generated_at",      TIMESTAMP(timezone=True)),
)

picks = Table(
    "picks", metadata,
    Column("id",                 UUID(as_uuid=True), primary_key=True),
    Column("game_id",            Text),
    Column("season",             Integer),
    Column("week",               Integer),
    Column("home_team",          Text),
    Column("away_team",          Text),
    Column("pick_team",          Text),
    Column("win_probability",    Float),
    Column("spread",             Float),
    Column("model_spread_diff",  Float),
    Column("confidence_label",   Text),
    Column("approved",           Boolean),
    Column("rejected",           Boolean),
    Column("approval_timestamp", TIMESTAMP(timezone=True)),
    Column("outcome",            Text),
    Column("ats_result",         Text),
    Column("clv",                Float),
    Column("created_at",         TIMESTAMP(timezone=True)),
    Column("pick_spread",        Numeric),
)

ppa_ratings = Table(
    "ppa_ratings", metadata,
    Column("id",                   Integer, primary_key=True),
    Column("team",                 Text),
    Column("season",               Integer),
    Column("offense_ppa",          Float),
    Column("defense_ppa",          Float),
    Column("success_rate_offense", Float),
    Column("success_rate_defense", Float),
    Column("created_at",           TIMESTAMP(timezone=True)),
)

power_ratings_comparison = Table(
    "power_ratings_comparison", metadata,
    Column("id",            Integer, primary_key=True),
    Column("team",          Text),
    Column("season",        Integer),
    Column("massey_rating", Float),
    Column("sp_overall",    Float),
    Column("z_massey",      Float),
    Column("z_sp",          Float),
    Column("composite_z",   Float),
    Column("created_at",    TIMESTAMP(timezone=True)),
)


def create_all_tables():
    """Create all CFB agent tables in the database if they do not already exist.

    Uses SQLAlchemy's checkfirst=True so this is safe to call on every startup —
    existing tables and their data are never dropped or modified.
    """
    metadata.create_all(engine, checkfirst=True)
    print("All tables verified / created.")


if __name__ == "__main__":
    create_all_tables()
