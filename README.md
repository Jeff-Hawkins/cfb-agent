# CFB Betting Agent 🏈

An AI-powered college football analysis tool that predicts game win probabilities and surfaces betting line inefficiencies using historical stats, machine learning, and a conversational LLM interface.

-----

## What It Does

- **Win Probability Modeling** — Logistic regression model trained on 5 seasons (2021–2025) of FBS game data. Predicts win probability based on team offensive/defensive efficiency and home field advantage.
- **Betting Line Analysis** — Compares model-generated probabilities against historical betting lines to identify where the market may be mispriced.
- **Conversational Agent** — LangGraph-style orchestrator powered by an LLM (Groq / llama-3.3-70b) that lets you ask natural language questions like *“Who has the edge in a neutral-site game between Alabama and Georgia?”*
- **Streamlit UI** — Clean front-end for exploring predictions without touching the code.

-----

## Tech Stack

|Layer      |Tools                                                        |
|-----------|-------------------------------------------------------------|
|Language   |Python 3.11                                                  |
|Database   |SQLite (via SQLAlchemy)                                      |
|ML Model   |scikit-learn (Logistic Regression)                           |
|LLM / Agent|Groq API, LangGraph-style orchestrator                       |
|UI         |Streamlit                                                    |
|Data Source|[College Football Data API](https://collegefootballdata.com/)|

-----

## Project Structure

```
cfb-agent/
├── data/
│   └── cfb.db                  # SQLite database (auto-built on run)
├── db/
│   └── database.py             # DB init, schema, query helpers
├── tools/
│   └── stats_fetcher.py        # CFBD API calls and data loading
├── models/
│   ├── win_probability.py      # Logistic regression training + inference
│   └── saved/                  # Serialized model artifacts (joblib)
├── agent/
│   └── orchestrator.py         # LangGraph-style agent logic
├── app.py                      # Streamlit UI entry point
├── main.py                     # CLI entry point, rebuilds DB
├── requirements.txt
├── .env.example
└── .gitignore
```

-----

## Database

Built from the College Football Data API. Clears and rebuilds on each `main.py` run.

|Table          |Rows   |Description                                      |
|---------------|-------|-------------------------------------------------|
|`games`        |13,407+|Game results, scores, home/away teams (2021–2025)|
|`team_stats`   |33,261+|Per-game offensive and defensive stats           |
|`betting_lines`|5,339+ |Historical spread and over/under lines           |


> 2020 excluded due to COVID-disrupted schedule introducing noise. Row counts reflect pre-2025 data; 2025 season adds to these totals.

-----

## Model

**Algorithm:** Logistic Regression  
**Accuracy:** ~67% on held-out FBS games (n=2,968, 2021–2024 data)  
**Features used:**

- Points per game
- Passing yards
- Rushing yards
- Turnovers
- Fumbles lost
- Home field advantage

**Known limitations:**

- No AP Poll / rankings integration (top-10 matchups may be skewed)
- Season aggregates — doesn’t weight recent form
- No injury or depth chart data
- Example miss: Michigan given 67.8% home win probability vs. Ohio State (2025) — OSU won 27-9 as the #2 ranked team

> This is intentional transparency. The model is a baseline, not a black box. Next iteration will incorporate SP+ ratings and rolling recent-form weighting.

-----

## Getting Started

**1. Clone the repo**

```bash
git clone https://github.com/yourusername/cfb-agent.git
cd cfb-agent
```

**2. Set up your environment**

```bash
conda create -n cfb-agent python=3.11
conda activate cfb-agent
pip install -r requirements.txt
```

**3. Add your API keys**

```bash
cp .env.example .env
# Add your CFBD_API_KEY and GROQ_API_KEY
```

**4. Build the database**

```bash
python main.py
```

**5. Train the model**

```bash
python -m models.win_probability
```

**6. Launch the app**

```bash
streamlit run app.py
```

-----

## Roadmap

- [ ] Add SP+ ratings as model features
- [ ] Rolling 4-week form weighting
- [ ] Injury report integration
- [ ] Swap Groq for Anthropic Claude API
- [ ] Expand to NFL regular season

-----

## About

Built by Jeff Hawkins — former D1 football player (USF) turned data analyst. This project sits at the intersection of two things I care about: sports and predictive analytics. The goal isn’t just to predict wins — it’s to understand *why* the model gets it wrong and build something more honest over time.

Connect on [LinkedIn](https://www.linkedin.com/in/jeffrey-hawkins-a576a1128/) | [Live Demo](https://cfb-agent.streamlit.app/)
