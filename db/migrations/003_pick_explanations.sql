CREATE TABLE IF NOT EXISTS pick_explanations (
    id SERIAL PRIMARY KEY,
    pick_id UUID NOT NULL REFERENCES picks(id) ON DELETE CASCADE,
    explanation_short TEXT,
    explanation_full TEXT,
    feature_snapshot JSONB,
    model_version TEXT,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(pick_id)
);
