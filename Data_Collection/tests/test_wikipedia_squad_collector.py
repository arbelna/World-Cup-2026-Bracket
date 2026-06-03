from __future__ import annotations

import unittest

from src.data_collection.collectors.wikipedia_squad_collector import (
    DEFAULT_SQUAD_SOURCES,
    parse_squad_page_html,
)


SAMPLE_SQUAD_HTML = """
<html><body>
<h2 id="Group_A">Group A</h2>
<h3>Ecuador</h3>
<table class="wikitable">
<tr><th>No.</th><th>Pos.</th><th>Player</th><th>Date of birth (age)</th><th>Caps</th><th>Goals</th><th>Club</th></tr>
<tr>
  <td>1</td><td>GK</td>
  <td><a href="/wiki/Hern%C3%A1n_Gal%C3%ADndez">Hern\u00e1n Gal\u00edndez</a></td>
  <td>(1987-03-30)</td><td>12</td><td>0</td>
  <td><a href="/wiki/Club_Am%C3%A9rica">Am\u00e9rica</a></td>
</tr>
<tr>
  <td>2</td><td>DF</td>
  <td><a href="/wiki/Test_Player">Test Player</a></td>
  <td>(1990-01-01)</td><td>\u2014</td><td>0</td>
  <td><a href="/wiki/Test_FC">Test FC</a></td>
</tr>
</table>
</body></html>
"""


class WikipediaSquadSourcesTest(unittest.TestCase):
    def test_default_page_titles(self) -> None:
        expected = (
            ("world-cup-2026", "2026_FIFA_World_Cup_squads"),
            ("world-cup-2022", "2022_FIFA_World_Cup_squads"),
            ("world-cup-2018", "2018_FIFA_World_Cup_squads"),
            ("world-cup-2014", "2014_FIFA_World_Cup_squads"),
            ("world-cup-2010", "2010_FIFA_World_Cup_squads"),
            ("euro-2024", "UEFA_Euro_2024_squads"),
            ("euro-2020", "UEFA_Euro_2020_squads"),
            ("euro-2016", "UEFA_Euro_2016_squads"),
            ("euro-2012", "UEFA_Euro_2012_squads"),
            ("copa-america-2024", "2024_Copa_Am\u00e9rica_squads"),
            ("copa-america-2021", "2021_Copa_Am\u00e9rica_squads"),
            ("copa-america-2019", "2019_Copa_Am\u00e9rica_squads"),
            ("copa-america-2016", "Copa_Am\u00e9rica_Centenario_squads"),
        )
        actual = tuple((source.tournament_id, source.wikipedia_page) for source in DEFAULT_SQUAD_SOURCES)
        self.assertEqual(actual, expected)


class WikipediaSquadParseTest(unittest.TestCase):
    def test_parse_squad_page_html_extracts_utf8_names(self) -> None:
        teams = parse_squad_page_html(SAMPLE_SQUAD_HTML)
        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0].team_name, "Ecuador")
        self.assertEqual(teams[0].group, "Group A")
        self.assertEqual(len(teams[0].players), 2)

        keeper = teams[0].players[0]
        self.assertEqual(keeper.player_name, "Hern\u00e1n Gal\u00edndez")
        self.assertEqual(keeper.club_name, "Am\u00e9rica")
        self.assertEqual(keeper.club_wikipedia_title, "Club_Am\u00e9rica")
        self.assertEqual(keeper.date_of_birth, "1987-03-30")
        self.assertEqual(keeper.squad_number, 1)

        defender = teams[0].players[1]
        self.assertIsNone(defender.caps)


if __name__ == "__main__":
    unittest.main()
