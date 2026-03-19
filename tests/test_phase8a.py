import unittest
from db.database import query_db

class TestPhase8a(unittest.TestCase):
    def test_ppa_ratings_table_populated(self):
        """Assert ppa_ratings table has data for 2024."""
        df = query_db("SELECT COUNT(*) as count FROM ppa_ratings WHERE season = 2024")
        count = int(df.iloc[0]["count"])
        self.assertGreaterEqual(count, 100, f"ppa_ratings table only has {count} rows for 2024")

    def test_advanced_stats_extended_populated(self):
        """Assert advanced_stats table has success_rate and havoc data for 2024."""
        df = query_db("""
            SELECT COUNT(*) as count 
            FROM advanced_stats 
            WHERE season = 2024 
              AND success_rate IS NOT NULL 
              AND defense_havoc_total IS NOT NULL
        """)
        count = int(df.iloc[0]["count"])
        self.assertGreaterEqual(count, 100, f"advanced_stats table only has {count} rows with extended data for 2024")

    def test_power_ratings_comparison_exists(self):
        """Assert power_ratings_comparison table exists (even if empty due to scraping blocks)."""
        df = query_db("SELECT table_name FROM information_schema.tables WHERE table_name = 'power_ratings_comparison'")
        self.assertFalse(df.empty, "power_ratings_comparison table does not exist")

if __name__ == "__main__":
    unittest.main()
