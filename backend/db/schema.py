"""SQLAlchemy table definitions for the CFB agent PostgreSQL database.

All tables mirror the column names and types used by the CFBD API fetchers.
Call create_all_tables() once at startup to ensure every table exists before
any data is written.
"""

from sqlalchemy import (
    BigInteger, Boolean, Column, Float, MetaData, Table, Text
)
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
    Column("team",               Text),
    Column("season",             BigInteger),
    Column("offense_lineYards",  Float),
    Column("defense_stuffRate",  Float),
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


def create_all_tables():
    """Create all CFB agent tables in the database if they do not already exist.

    Uses SQLAlchemy's checkfirst=True so this is safe to call on every startup —
    existing tables and their data are never dropped or modified.

    Tables created (in dependency order):
        games, team_stats, betting_lines, sp_ratings, recruiting_rankings,
        returning_production, coaches, portal_players, portal_net_ratings,
        preseason_2026, elo_ratings, advanced_stats, drives, pregame_wp
    """
    metadata.create_all(engine, checkfirst=True)
    print("All tables verified / created.")


if __name__ == "__main__":
    create_all_tables()
