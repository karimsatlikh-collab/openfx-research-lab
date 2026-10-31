"""Adversarial tests for G0 source admissibility and G1 claim binding."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from openfx.source_provenance import (
    ProvenanceError, build_atomic_claim, build_hypothesis_card,
    build_source_record, register_claim_record, resolve_claim_record, validate_source_record,
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

    def test_non_utc_offset_is_rejected_for_utc_timestamp_field(self):
        record = source()
        record["retrieved_at_utc"] = "2026-10-30T13:00:00+03:00"
        with self.assertRaisesRegex(ProvenanceError, "timestamp"):
            validate_source_record(record, CONTENT)

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

    def test_hypothesis_rejects_missing_claim_id_and_unverified_claim_state(self):
        valid = {
            "claim_kind": "source_backed",
            "claim_id": "claim-valid",
            "provenance_state": "test_confirmed",
            "source_ref": {
                "source_id": "source-valid",
                "exact_locator": LOCATOR,
                "content_sha256": "a" * 64,
            },
        }
        missing_id = dict(valid)
        missing_id.pop("claim_id")
        with self.assertRaisesRegex(ProvenanceError, "claim_id"):
            build_hypothesis_card(
                hypothesis_id="hyp-4", title="T", falsifiable_statement="F",
                linked_claims=[missing_id], predicted_mechanism="M", invalidation_criteria="I",
            )
        unverified = dict(valid, provenance_state="hypothesis")
        with self.assertRaisesRegex(ProvenanceError, "source-backed"):
            build_hypothesis_card(
                hypothesis_id="hyp-5", title="T", falsifiable_statement="F",
                linked_claims=[unverified], predicted_mechanism="M", invalidation_criteria="I",
            )

    def test_caller_supplied_claim_is_explicitly_not_provenance_verified(self):
        # A plausible fabricated dictionary is not proof that a registry record exists.
        fabricated = {
            "claim_kind": "source_backed",
            "claim_id": "claim-fabricated",
            "provenance_state": "test_confirmed",
            "source_ref": {
                "source_id": "source-fabricated",
                "exact_locator": LOCATOR,
                "content_sha256": "b" * 64,
            },
        }
        card = build_hypothesis_card(
            hypothesis_id="hyp-fabricated",
            title="Caller-supplied claim",
            falsifiable_statement="A fabricated claim dictionary must not be treated as verified.",
            linked_claims=[fabricated],
            predicted_mechanism="Test-only mechanism",
            invalidation_criteria="Reject if provenance is reported verified without registry resolution",
        )
        self.assertTrue(card["claim_link_validation"]["shape_valid"])
        self.assertFalse(card["claim_link_validation"]["provenance_verified"])
        self.assertEqual(
            card["claim_link_validation"]["status"],
            "metadata_only_unverified",
        )
        self.assertIn("no authoritative claim registry", card["claim_link_validation"]["reason"])

    def test_content_addressed_registry_resolves_claim_and_source_chain(self):
        claim = build_atomic_claim(
            claim_id="claim-registry-1", source_record=source(), source_content=CONTENT,
            exact_locator=LOCATOR, statement="A registered synthetic observation.",
            provenance_state="test_confirmed",
        )
        with tempfile.TemporaryDirectory() as tmp:
            digest = register_claim_record(tmp, claim, source(), CONTENT)
            resolved = resolve_claim_record(tmp, "claim-registry-1")
            self.assertEqual(resolved["claim"], claim)
            self.assertEqual(resolved["claim_record_sha256"], digest)
            self.assertTrue(resolved["record_integrity_verified"])
            self.assertFalse(resolved["provenance_authenticated"])
            card = build_hypothesis_card(
                hypothesis_id="hyp-registry-1", title="Registered claim",
                falsifiable_statement="The registry-backed link resolves exactly.",
                linked_claims=[claim], predicted_mechanism="Mechanism",
                invalidation_criteria="Fail if the registry link does not resolve.",
                claim_registry_root=tmp,
            )
            result = card["claim_link_validation"]
            self.assertEqual(result["registry_records_resolved"], 1)
            self.assertTrue(result["record_integrity_verified"])
            self.assertFalse(result["provenance_verified"])
            self.assertEqual(
                result["status"],
                "content_addressed_local_registry_integrity_only_not_authenticated",
            )

    def test_registry_rejects_unknown_claim_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ProvenanceError, "resolution failed"):
                resolve_claim_record(tmp, "claim-does-not-exist")

    def test_registry_rejects_invalid_claim_state_before_writing_any_objects(self):
        valid_claim = build_atomic_claim(
            claim_id="claim-invalid-state", source_record=source(), source_content=CONTENT,
            exact_locator=LOCATOR, statement="State must be validated before registration.",
        )
        invalid_claims = []
        for state in ("hypothesis", "unknown", "not-a-state", None):
            invalid_claims.append(dict(valid_claim, provenance_state=state))
        missing_state = dict(valid_claim)
        missing_state.pop("provenance_state")
        invalid_claims.append(missing_state)

        for index, invalid_claim in enumerate(invalid_claims):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(ProvenanceError, "evidential provenance state"):
                    register_claim_record(tmp, invalid_claim, source(), CONTENT)
                root = Path(tmp)
                self.assertFalse((root / "claim-index" / "claim-invalid-state.json").exists())
                self.assertFalse((root / "claim-records").exists())
                self.assertFalse((root / "source-records").exists())
                self.assertFalse((root / "source-content").exists())

    def test_registry_rejects_duplicate_and_noncanonical_index_json(self):
        claim = build_atomic_claim(
            claim_id="claim-index-strict-json", source_record=source(), source_content=CONTENT,
            exact_locator=LOCATOR, statement="The index must have one canonical encoding.",
        )
        with tempfile.TemporaryDirectory() as tmp:
            digest = register_claim_record(tmp, claim, source(), CONTENT)
            index_path = Path(tmp) / "claim-index" / "claim-index-strict-json.json"
            duplicate = (
                '{"schema_version":1,"claim_id":"claim-index-strict-json",'
                f'"claim_record_sha256":"{digest}",'
                f'"claim_record_sha256":"{digest}"}}'
            ).encode("utf-8")
            index_path.write_bytes(duplicate)
            with self.assertRaisesRegex(ProvenanceError, "duplicate JSON object key"):
                resolve_claim_record(tmp, "claim-index-strict-json")

            noncanonical = json.dumps({
                "schema_version": 1,
                "claim_id": "claim-index-strict-json",
                "claim_record_sha256": digest,
            }, indent=2).encode("utf-8")
            index_path.write_bytes(noncanonical)
            with self.assertRaisesRegex(ProvenanceError, "not canonically encoded"):
                resolve_claim_record(tmp, "claim-index-strict-json")

    def test_registry_rejects_modified_claim_record_bytes(self):
        claim = build_atomic_claim(
            claim_id="claim-tamper-1", source_record=source(), source_content=CONTENT,
            exact_locator=LOCATOR, statement="Original statement.",
        )
        with tempfile.TemporaryDirectory() as tmp:
            digest = register_claim_record(tmp, claim, source(), CONTENT)
            path = Path(tmp) / "claim-records" / f"{digest}.json"
            path.write_bytes(path.read_bytes() + b" ")
            with self.assertRaisesRegex(ProvenanceError, "content hash mismatch"):
                resolve_claim_record(tmp, "claim-tamper-1")

    def test_registry_rejects_modified_source_bytes(self):
        claim = build_atomic_claim(
            claim_id="claim-source-tamper", source_record=source(), source_content=CONTENT,
            exact_locator=LOCATOR, statement="Source-bound statement.",
        )
        with tempfile.TemporaryDirectory() as tmp:
            register_claim_record(tmp, claim, source(), CONTENT)
            content_digest = source()["content_sha256"]
            path = Path(tmp) / "source-content" / f"{content_digest}.bin"
            path.write_bytes(CONTENT + b"tampered")
            with self.assertRaisesRegex(ProvenanceError, "source content hash mismatch"):
                resolve_claim_record(tmp, "claim-source-tamper")

    def test_registry_rejects_forged_caller_claim_and_changed_locator(self):
        claim = build_atomic_claim(
            claim_id="claim-forged-link", source_record=source(), source_content=CONTENT,
            exact_locator=LOCATOR, statement="Registered statement.",
        )
        with tempfile.TemporaryDirectory() as tmp:
            register_claim_record(tmp, claim, source(), CONTENT)
            forged = dict(claim, statement="A different caller-supplied statement.")
            with self.assertRaisesRegex(ProvenanceError, "does not match"):
                build_hypothesis_card(
                    hypothesis_id="hyp-forged-link", title="Forged link",
                    falsifiable_statement="Must reject altered claim.",
                    linked_claims=[forged], predicted_mechanism="Mechanism",
                    invalidation_criteria="Reject any altered claim.",
                    claim_registry_root=tmp,
                )
            altered_ref = dict(claim)
            altered_ref["source_ref"] = dict(claim["source_ref"], exact_locator="fixture://altered")
            with self.assertRaisesRegex(ProvenanceError, "does not match"):
                build_hypothesis_card(
                    hypothesis_id="hyp-altered-locator", title="Altered locator",
                    falsifiable_statement="Must reject altered locator.",
                    linked_claims=[altered_ref], predicted_mechanism="Mechanism",
                    invalidation_criteria="Reject altered locator.",
                    claim_registry_root=tmp,
                )

    @unittest.skipUnless(os.name == "posix", "POSIX file-mode assertion")
    def test_registry_objects_are_created_with_private_permissions(self):
        claim = build_atomic_claim(
            claim_id="claim-private-mode", source_record=source(), source_content=CONTENT,
            exact_locator=LOCATOR, statement="Private local fixture.",
        )
        with tempfile.TemporaryDirectory() as tmp:
            digest = register_claim_record(tmp, claim, source(), CONTENT)
            resolved = resolve_claim_record(tmp, "claim-private-mode")
            paths = [
                Path(tmp) / "claim-records" / f"{digest}.json",
                Path(tmp) / "source-records" / f"{resolved['source_record_sha256']}.json",
                Path(tmp) / "source-content" / f"{source()['content_sha256']}.bin",
                Path(tmp) / "claim-index" / "claim-private-mode.json",
            ]
            for path in paths:
                self.assertEqual(path.stat().st_mode & 0o077, 0, str(path))

    def test_registry_rejects_claim_id_collision(self):
        claim = build_atomic_claim(
            claim_id="claim-id-collision", source_record=source(), source_content=CONTENT,
            exact_locator=LOCATOR, statement="First statement.",
        )
        second = dict(claim, statement="Second statement.")
        with tempfile.TemporaryDirectory() as tmp:
            register_claim_record(tmp, claim, source(), CONTENT)
            with self.assertRaisesRegex(ProvenanceError, "collision or tampering"):
                register_claim_record(tmp, second, source(), CONTENT)


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


if __name__ == "__main__":
    unittest.main()
