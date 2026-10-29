"""Adversarial tests for G0 source admissibility and G1 claim binding."""
import unittest

from openfx.source_provenance import (
    ProvenanceError, build_atomic_claim, build_hypothesis_card,
    build_source_record, validate_source_record,
)


CONTENT = b"Synthetic local fixture: price moved above the marked level."
LOCATOR = "fixture://local/synthetic-source#bytes=0-59"


def source():
    return build_source_record(
        source_id="fixture-source-1",
        identity="local synthetic fixture; not third-party material",
        rights_basis="owner_created",
        permission_evidence="created solely as a repository test fixture",
        retrieved_at_utc="2026-10-30T10:00:00Z",
        exact_locator=LOCATOR,
        capture_method="inline synthetic bytes",
        content=CONTENT,
        provenance_state="test_confirmed",
    )


class SourceAdmissibilityTests(unittest.TestCase):
    def test_synthetic_local_source_is_admissible(self):
        record = source()
        result = validate_source_record(record, CONTENT)
        self.assertTrue(result["valid"])
        self.assertEqual(result["provenance_state"], "test_confirmed")

    def test_missing_rights_basis_is_rejected(self):
        record = source()
        record["rights_basis"] = ""
        with self.assertRaisesRegex(ProvenanceError, "rights_basis"):
            validate_source_record(record, CONTENT)

    def test_ambiguous_rights_require_human_review(self):
        record = source()
        record["rights_basis"] = "ambiguous"
        with self.assertRaisesRegex(ProvenanceError, "ambiguous"):
            validate_source_record(record, CONTENT)

    def test_explicit_permission_requires_auditable_approval_fields(self):
        record = source()
        record["rights_basis"] = "explicit_permission"
        with self.assertRaisesRegex(ProvenanceError, "human approval"):
            validate_source_record(record, CONTENT)

    def test_missing_exact_locator_is_rejected(self):
        record = source()
        record["exact_locator"] = " "
        with self.assertRaisesRegex(ProvenanceError, "exact_locator"):
            validate_source_record(record, CONTENT)

    def test_missing_or_malformed_hash_is_rejected(self):
        for digest in ("", "not-a-hash", "A" * 64):
            record = source()
            record["content_sha256"] = digest
            with self.subTest(digest=digest), self.assertRaisesRegex(ProvenanceError, "SHA-256"):
                validate_source_record(record, CONTENT)

    def test_content_hash_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ProvenanceError, "hash mismatch"):
            validate_source_record(source(), CONTENT + b" altered")

    def test_invalid_timestamp_and_provenance_are_rejected(self):
        record = source()
        record["retrieved_at_utc"] = "yesterday"
        with self.assertRaisesRegex(ProvenanceError, "timestamp"):
            validate_source_record(record, CONTENT)
        record = source()
        record["provenance_state"] = "verified_by_ai"
        with self.assertRaisesRegex(ProvenanceError, "provenance_state"):
            validate_source_record(record, CONTENT)


class ClaimAndHypothesisBindingTests(unittest.TestCase):
    def test_atomic_claim_binds_source_id_locator_and_hash(self):
        record = source()
        claim = build_atomic_claim(
            claim_id="claim-1", source_record=record, source_content=CONTENT,
            exact_locator=LOCATOR, statement="The synthetic fixture states a price move.",
            provenance_state="test_confirmed",
        )
        self.assertEqual(claim["source_ref"]["source_id"], record["source_id"])
        self.assertEqual(claim["source_ref"]["content_sha256"], record["content_sha256"])

    def test_claim_with_non_exact_locator_is_rejected(self):
        with self.assertRaisesRegex(ProvenanceError, "does not exactly match"):
            build_atomic_claim(
                claim_id="claim-2", source_record=source(), source_content=CONTENT,
                exact_locator="fixture://different", statement="Claim",
            )

    def test_hypothesis_remains_hypothesis_not_verified_rule(self):
        claim = build_atomic_claim(
            claim_id="claim-3", source_record=source(), source_content=CONTENT,
            exact_locator=LOCATOR, statement="A synthetic observation.",
        )
        card = build_hypothesis_card(
            hypothesis_id="hyp-1", title="Synthetic test hypothesis",
            falsifiable_statement="If condition X holds, outcome Y should occur.",
            linked_claims=[claim], predicted_mechanism="Mechanism to test",
            invalidation_criteria="Reject if Y does not occur under frozen test conditions",
        )
        self.assertEqual(card["epistemic_status"], "hypothesis")
        self.assertFalse(card["is_verified_rule"])
        self.assertEqual(card["linked_claims"][0]["source_ref"], claim["source_ref"])

    def test_hypothesis_rejects_unlinked_or_non_source_claim(self):
        with self.assertRaisesRegex(ProvenanceError, "at least one"):
            build_hypothesis_card(
                hypothesis_id="hyp-2", title="T", falsifiable_statement="F",
                linked_claims=[], predicted_mechanism="M", invalidation_criteria="I",
            )
        with self.assertRaisesRegex(ProvenanceError, "source-backed"):
            build_hypothesis_card(
                hypothesis_id="hyp-3", title="T", falsifiable_statement="F",
                linked_claims=[{"claim_kind": "hypothesis"}],
                predicted_mechanism="M", invalidation_criteria="I",
            )


if __ __name__ == "__main__":
    unittest.main()
