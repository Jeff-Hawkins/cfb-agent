"""Utility for normalizing team names from external sources to CFBD canonical names.

This module provides a centralized mapping for team names used by various scrapers
to ensure consistency with the database.
"""

# Mapping from external names to CFBD canonical names
TEAM_NAME_MAPPING = {
    "ole miss": "Mississippi",
    "usc": "Southern California",
    "uconn": "Connecticut",
    "uab": "Alabama Birmingham",
    "utsa": "Texas San Antonio",
    "utep": "Texas El Paso",
    "usf": "South Florida",
    "tcu": "Texas Christian",
    "smu": "Southern Methodist",
    "lsu": "Louisiana State",
    "ucf": "Central Florida",
    "fiu": "Florida International",
    "fau": "Florida Atlantic",
    "unlv": "Nevada Las Vegas",
    "umass": "Massachusetts",
    "app state": "Appalachian State",
    "pitt": "Pittsburgh",
    "miami (oh)": "Miami Ohio",
    "miami (fl)": "Miami",
    "louisiana": "Louisiana Lafayette",
    "ul monroe": "Louisiana Monroe",
    "san josé state": "San Jose State",
}

def normalize_team_name(name: str) -> str:
    """Maps external source team names to CFBD canonical names.
    
    Args:
        name: The raw team name from an external source.
        
    Returns:
        The CFBD canonical team name if a mapping exists, otherwise the input unchanged.
    """
    if not name:
        return name
    
    # Check lowercase for case-insensitive matching
    lower_name = name.strip().lower()
    if lower_name in TEAM_NAME_MAPPING:
        return TEAM_NAME_MAPPING[lower_name]
    
    return name

def get_unmapped_teams(raw_names: list[str]) -> list[str]:
    """Returns names from a list that have no mapping and don't match any known CFBD team.
    
    Note: For now, this just returns names that are not in the mapping and not 
    already looking like a CFBD name (this part is hard to check without a DB query,
    so we just return names not in the mapping for now).
    
    Args:
        raw_names: List of raw team names.
        
    Returns:
        List of unmapped raw team names.
    """
    # In a more advanced version, we could check against a known list of CFBD teams
    unmapped = []
    for name in raw_names:
        if not name:
            continue
        lower_name = name.strip().lower()
        if lower_name not in TEAM_NAME_MAPPING:
            # We skip it if it's already a "canonical" name we know, 
            # but for now we just return anything not in our special mapping.
            unmapped.append(name)
    return unmapped
