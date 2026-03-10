import os
import json
from groq import Groq
from dotenv import load_dotenv
from db.database import query_db
from models.win_probability import predict_win_probability, build_team_profiles

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# --- Tools the agent can call ---

def get_team_stats(team: str, season: int = 2024) -> str:
    profiles = build_team_profiles()
    data = profiles[
        (profiles["team"] == team) &
        (profiles["season"] == season)
    ]
    if data.empty:
        return f"No stats found for {team} in {season}"
    return data.to_string(index=False)

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

def get_win_probability(home_team: str, away_team: str, season: int = 2024) -> str:
    prob = predict_win_probability(home_team, away_team, season)
    if isinstance(prob, str):
        return prob
    return json.dumps({
        "home_team": home_team,
        "away_team": away_team,
        "home_win_probability": prob,
        "away_win_probability": round(1 - prob, 4)
    })

# --- Tool definitions for the LLM ---

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_team_stats",
            "description": "Get season stats for a college football team",
            "parameters": {
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Team name e.g. 'Ohio State'"},
                    "season": {"type": "integer", "description": "Season year e.g. 2024"}
                },
                "required": ["team"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_betting_line",
            "description": "Get the betting line for a matchup",
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
            "name": "get_win_probability",
            "description": "Get the predicted win probability for a matchup",
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
    }
]

# --- Tool executor ---

def run_tool(tool_name: str, args: dict) -> str:
    if tool_name == "get_team_stats":
        return get_team_stats(**args)
    elif tool_name == "get_betting_line":
        return get_betting_line(**args)
    elif tool_name == "get_win_probability":
        return get_win_probability(**args)
    return "Unknown tool"

# --- Agent loop ---

def run_agent(user_query: str):
    print(f"\nQuery: {user_query}\n")
    
    messages = [
        {
            "role": "system",
            "content": """You are a college football betting analyst. 
            You have access to team stats, betting lines, and a win probability model.
            When asked about a matchup, use your tools to gather data and provide
            a structured analysis including win probability and betting value assessment.
            Always explain your reasoning clearly."""
        },
        {"role": "user", "content": user_query}
    ]
    
    # Agentic loop
    while True:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        
        # If no tool calls, we have the final answer
        if not message.tool_calls:
            print("ANALYSIS:\n")
            print(message.content)
            break
        
        # Convert to plain dict to avoid Groq SDK serialization bug
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
            print(f"Calling tool: {tool_name} with {args}")
            result = run_tool(tool_name, args)
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

if __name__ == "__main__":
    run_agent("Analyze the Ohio State vs Michigan matchup in 2024. What does the model say and is there betting value?")