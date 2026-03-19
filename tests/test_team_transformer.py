import unittest
from tools.utils.team_transformer import normalize_team_name, get_unmapped_teams

class TestTeamTransformer(unittest.TestCase):
    def test_known_mappings(self):
        """Assert all specified mappings return correct CFBD name."""
        self.assertEqual(normalize_team_name("Ole Miss"), "Mississippi")
        self.assertEqual(normalize_team_name("USC"), "Southern California")
        self.assertEqual(normalize_team_name("UConn"), "Connecticut")
        self.assertEqual(normalize_team_name("LSU"), "Louisiana State")
        self.assertEqual(normalize_team_name("App State"), "Appalachian State")
        self.assertEqual(normalize_team_name("Miami (OH)"), "Miami Ohio")
        self.assertEqual(normalize_team_name("Miami (FL)"), "Miami")
        self.assertEqual(normalize_team_name("Louisiana"), "Louisiana Lafayette")
        self.assertEqual(normalize_team_name("UL Monroe"), "Louisiana Monroe")
        self.assertEqual(normalize_team_name("San José State"), "San Jose State")

    def test_case_insensitive(self):
        """Assert 'ole miss' and 'OLE MISS' both normalize."""
        self.assertEqual(normalize_team_name("ole miss"), "Mississippi")
        self.assertEqual(normalize_team_name("OLE MISS"), "Mississippi")
        self.assertEqual(normalize_team_name("  ole miss  "), "Mississippi")

    def test_unmapped_passthrough(self):
        """Assert unknown names return unchanged."""
        self.assertEqual(normalize_team_name("Alabama"), "Alabama")
        self.assertEqual(normalize_team_name("Unknown Team"), "Unknown Team")

    def test_get_unmapped_teams(self):
        """Assert returns correct list of unmapped teams."""
        raw_names = ["Ole Miss", "Alabama", "USC", "Unknown Team"]
        # Alabama and Unknown Team are not in TEAM_NAME_MAPPING
        unmapped = get_unmapped_teams(raw_names)
        self.assertIn("Alabama", unmapped)
        self.assertIn("Unknown Team", unmapped)
        self.assertNotIn("Ole Miss", unmapped)
        self.assertNotIn("USC", unmapped)

if __name__ == "__main__":
    unittest.main()
