import streamlit as st
import json
import os
from groq import Groq
from dotenv import load_dotenv
from db.database import query_db
from models.win_probability import predict_win_probability, build_team_profiles

# Build DB if it doesn't exist (first run on cloud)
if not os.path.exists("data/cfb.db"):
    os.makedirs("data", exist_ok=True)
    from tools.stats_fetcher import fetch_games, fetch_team_stats, fetch_betting_lines
    with st.spinner("Building database for first time... this takes about 60 seconds."):
        for year in [2021, 2022, 2023, 2024, 2025]:
            fetch_games(year)
            fetch_team_stats(year)
            fetch_betting_lines(year)

if not os.path.exists("models/saved/win_prob_model.pkl"):
    os.makedirs("models/saved", exist_ok=True)
    from models.win_probability import train_model
    with st.spinner("Training win probability model..."):
        train_model()

load_dotenv()

# Load secrets from Streamlit Cloud if available
if "CFB_API_KEY" in st.secrets:
    os.environ["CFB_API_KEY"] = st.secrets["CFB_API_KEY"]
if "GROQ_API_KEY" in st.secrets:
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

st.set_page_config(
    page_title="CFB Betting Analyst",
    page_icon="🏈",
    layout="wide"
)

st.title("🏈 CFB Betting Analyst")
st.caption("AI-powered college football betting analysis")

# --- Sidebar ---
with st.sidebar:
    st.header("Matchup Input")
    
    # Get available teams
    @st.cache_data
    def get_teams():
        df = query_db("SELECT DISTINCT homeTeam FROM games WHERE season = 2024 ORDER BY homeTeam")
        return df["homeTeam"].tolist()
    
    teams = get_teams()
    
    home_team = st.selectbox("Home Team", teams, index=teams.index("Ohio State") if "Ohio State" in teams else 0)
    away_team = st.selectbox("Away Team", teams, index=teams.index("Michigan") if "Michigan" in teams else 1)
    season = st.selectbox("Season", [2025, 2024, 2023, 2022, 2021], index=0)
    
    analyze_btn = st.button("Analyze Matchup", type="primary", use_container_width=True)

# --- Tool definitions ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_win_probability",
            "description": "Get predicted win probability for a matchup",
            "parameters": {
                "type": "object",
                "properties": {
                    "home_team": {"type": "string"},
                    "away_team": {"type": "string"},
                    "season": {"type": "integer"}
                },
                "required": ["home_team", "away_team"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_betting_line",
            "description": "Get betting line for a matchup",
            "parameters": {
                "type": "object",
                "properties": {
                    "home_team": {"type": "string"},
                    "away_team": {"type": "string"},
                    "season": {"type": "integer"}
                },
                "required": ["home_team", "away_team"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_team_stats",
            "description": "Get season stats for a team",
            "parameters": {
                "type": "object",
                "properties": {
                    "team": {"type": "string"},
                    "season": {"type": "integer"}
                },
                "required": ["team"]
            }
        }
    }
]

def get_win_probability(home_team, away_team, season=2024):
    prob = predict_win_probability(home_team, away_team, season)
    if isinstance(prob, str):
        return prob
    return json.dumps({
        "home_team": home_team,
        "away_team": away_team,
        "home_win_probability": prob,
        "away_win_probability": round(1 - prob, 4)
    })

def get_betting_line(home_team, away_team, season=2024):
    result = query_db(f"""
        SELECT homeTeam, awayTeam, lines
        FROM betting_lines
        WHERE season = {season}
        AND (
            (homeTeam = '{home_team}' AND awayTeam = '{away_team}')
            OR
            (homeTeam = '{away_team}' AND awayTeam = '{home_team}')
        )
        LIMIT 1
    """)
    if result.empty:
        return f"No betting line found for {home_team} vs {away_team}"
    return result.to_string(index=False)

def get_team_stats(team, season=2024):
    profiles = build_team_profiles()
    data = profiles[
        (profiles["team"] == team) &
        (profiles["season"] == season)
    ]
    if data.empty:
        return f"No stats found for {team} in {season}"
    return data.to_string(index=False)

def run_tool(tool_name, args):
    if tool_name == "get_win_probability":
        return get_win_probability(**args)
    elif tool_name == "get_betting_line":
        return get_betting_line(**args)
    elif tool_name == "get_team_stats":
        return get_team_stats(**args)
    return "Unknown tool"

def run_agent(home_team, away_team, season):
    messages = [
        {
    "role": "system",
    "content": """You are a college football betting analyst with access to three tools:
    1. get_team_stats - get stats for a team
    2. get_win_probability - get win probability for a matchup  
    3. get_betting_line - get the betting line for a matchup
    
    Always call get_win_probability and get_betting_line first, then get_team_stats for both teams.
    Then provide a concise analysis with: win probability, key stat advantages, line value assessment, and recommendation."""
        },
        {
            "role": "user",
            "content": f"Analyze {home_team} (home) vs {away_team} (away) in {season}. Is there betting value?"
        }
    ]

    while True:
        response = get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.1
    )

        message = response.choices[0].message

        if not message.tool_calls:
            return message.content

        tool_calls_dict = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            }
            for tc in message.tool_calls
        ]

        messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": tool_calls_dict
        })

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            result = run_tool(tool_name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

# --- Main UI ---
if analyze_btn:
    if home_team == away_team:
        st.error("Please select two different teams.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Home Team", home_team)
        with col2:
            st.metric("Away Team", away_team)

        # Win probability bar
        with st.spinner("Running model..."):
            prob = predict_win_probability(home_team, away_team, season)
        
        if isinstance(prob, float):
            st.subheader("Win Probability")
            col1, col2 = st.columns(2)
            with col1:
                st.metric(f"{home_team}", f"{prob*100:.1f}%")
            with col2:
                st.metric(f"{away_team}", f"{(1-prob)*100:.1f}%")
            st.progress(prob)

        # Check if matchup exists in DB
        line_check = query_db(f"""
     SELECT COUNT(*) as cnt FROM betting_lines
        WHERE season = {season}
        AND (
        (homeTeam = '{home_team}' AND awayTeam = '{away_team}')
        OR
        (homeTeam = '{away_team}' AND awayTeam = '{home_team}')
        )
        """)
        
        if line_check["cnt"].iloc[0] == 0:
            st.warning(f"⚠️ No historical betting line found for {home_team} vs {away_team} in {season}. These teams may not have played each other. Win probability model will still run but line analysis will be limited.")

       # Agent analysis
        st.subheader("AI Analysis")
        try:
            with st.spinner("Analyzing matchup..."):
                analysis = run_agent(home_team, away_team, season)
            st.markdown(analysis)
        except Exception as e:
            st.error(f"⚠️ Analysis failed — one or both teams may not have enough data in the {season} season. Try selecting FBS teams that played each other.")
            with st.expander("Error details"):
                st.code(str(e))

else:
    st.info("Select a matchup in the sidebar and click Analyze Matchup to get started.")