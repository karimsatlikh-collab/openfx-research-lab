import json
import unittest
from pathlib import Path

from openfx.transcript_quality import compare_transcript_fidelity

CORPUS_PATH = Path(__file__).parent / "fixtures" / "transcript_adversarial_cases.json"


class TranscriptAdversarialCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        cls.cases = cls.corpus["cases"]

    def test_corpus_is_labeled_and_has_unique_case_ids(self):
        self.assertEqual(self.corpus["schema_version"], 1)
        self.assertIn("not a statistically representative sample", self.corpus["scope"])
        ids = [case["id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual({case["label"] for case in self.cases}, {"equivalent", "meaning_change"})

    def test_all_curated_cases_match_expected_triage(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                result = compare_transcript_fidelity(case["reference"], case["extracted"])
                self.assertEqual(result["status"], case["expected_status"], msg=str({
                    "id": case["id"],
                    "label": case["label"],
                    "flags": result["flags"],
                    "similarity": result["similarity"],
                }))


if __name__ == "__main__":
    unittest.main()
