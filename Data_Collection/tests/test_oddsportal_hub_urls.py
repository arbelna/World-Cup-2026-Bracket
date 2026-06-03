import unittest

try:
    from src.data_collection.collectors.oddsportal_collector import OddsPortalCollector
except ModuleNotFoundError as exc:
    OddsPortalCollector = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


@unittest.skipIf(OddsPortalCollector is None, f"playwright dependency unavailable: {_IMPORT_ERROR}")
class OddsPortalHubUrlTests(unittest.TestCase):
    def test_canonical_h2h_odds_url_strips_fragment_variants(self) -> None:
        base = OddsPortalCollector.BASE_URL
        a = "/football/h2h/mexico-O6iHcNkd/south-africa-W2ijYvlr/#h4EoUB7T"
        b = "/football/h2h/mexico-O6iHcNkd/south-africa-W2ijYvlr/#8nrACRTs"
        expected = f"{base}/football/h2h/mexico-O6iHcNkd/south-africa-W2ijYvlr#1X2;2"
        self.assertEqual(OddsPortalCollector._canonical_h2h_odds_url(a), expected)
        self.assertEqual(OddsPortalCollector._canonical_h2h_odds_url(b), expected)

    def test_dedupe_h2h_odds_urls(self) -> None:
        collector = OddsPortalCollector(tournaments=())
        hrefs = [
            "/football/h2h/mexico-O6iHcNkd/south-africa-W2ijYvlr/#h4EoUB7T",
            "/football/h2h/mexico-O6iHcNkd/south-africa-W2ijYvlr/#8nrACRTs",
            "/football/h2h/czech-republic-6LHwBDGU/south-korea-K6Gs7P6G/#CGdvIm6K",
        ]
        self.assertEqual(len(collector._dedupe_h2h_odds_urls(hrefs)), 2)


if __name__ == "__main__":
    unittest.main()
