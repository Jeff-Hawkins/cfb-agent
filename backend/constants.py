"""
Shared threshold constants for CFB Agent.
Update here to propagate changes across all endpoints.
"""

# Spread filters
MAX_ABS_SPREAD = 17          # Exclude blowout games above this threshold
MIN_SPREAD_DIFF = 5.0        # Minimum model vs market disagreement to flag a pick

# Model confidence
MIN_WIN_PROB_FLAG = 0.65     # Minimum win probability to flag a pick
MIN_WIN_PROB_GAMES = 0.55    # Minimum win probability to show on Games page

# Model calibration
MODEL_IMPLIED_SCALE = 28     # Multiplier to convert win prob to implied spread points
