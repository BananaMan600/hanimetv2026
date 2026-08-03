import unittest

from hanimetv2026.api_test import normalize_metadata


class NormalizeMetadataTests(unittest.TestCase):
    def test_normalize_metadata_extracts_expected_fields(self):
        payload = {
            "success": True,
            "video": {
                "id": 1226,
                "name": "Itadaki! Seieki",
                "slug": "itadaki-seieki",
                "description": "A short description",
                "brand": "Pashmina",
                "views": 100,
                "likes": 10,
                "dislikes": 1,
                "downloads": 20,
                "monthly_rank": 3,
                "released_at": "2014-03-27T15:00:00.000Z",
                "created_at": "2016-06-07T00:02:39.351Z",
                "poster_url": "https://example.com/poster.jpg",
                "cover_url": "https://example.com/cover.jpg",
                "tags": ["big boobs", "bondage"],
            },
            "franchise": {
                "title": "Pashmina",
                "slug": "pashmina",
                "videos": [{"slug": "amanee-1"}, {"slug": "pure-hearted-girl-et-cetera-1"}],
            },
        }

        metadata = normalize_metadata(payload)

        self.assertEqual(metadata["title"], "Itadaki! Seieki")
        self.assertEqual(metadata["slug"], "itadaki-seieki")
        self.assertEqual(metadata["brand"], "Pashmina")
        self.assertEqual(metadata["tags"], ["big boobs", "bondage"])
        self.assertEqual(metadata["franchise_title"], "Pashmina")
        self.assertEqual(metadata["franchise_videos"], ["amanee-1", "pure-hearted-girl-et-cetera-1"])


if __name__ == "__main__":
    unittest.main()
