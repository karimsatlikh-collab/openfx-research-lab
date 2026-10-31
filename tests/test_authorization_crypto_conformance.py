"""Conformance gate for the proposed AuthorizationRecord crypto primitives.

These tests do not implement an authorization verifier or authorize worker execution.
"""
import json
import unittest

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


class Ed25519Rfc8032VectorTests(unittest.TestCase):
    def test_rfc8032_test_vector_1_empty_message(self):
        # RFC 8032, section 7.1, test vector 1.
        seed = bytes.fromhex(
            "9d61b19deffd5a60ba844af492ec2cc4"
            "4449c5697b326919703bac031cae7f60"
        )
        expected_public_key = bytes.fromhex(
            "d75a980182b10ab7d54bfed3c964073a"
            "0ee172f3daa62325af021a68f707511a"
        )
        expected_signature = bytes.fromhex(
            "e5564300c360ac729086e2cc806e828a"
            "84877f1eb8e5d974d873e06522490155"
            "5fb8821590a33bacc61e39701cf9b46bd"
            "25bf5f0595bbe24655141438e7a100b"
        )

        private_key = Ed25519PrivateKey.from_private_bytes(seed)
        public_key = private_key.public_key()
        self.assertEqual(
            expected_public_key,
            public_key.public_bytes_raw(),
        )
        signature = private_key.sign(b"")
        self.assertEqual(expected_signature, signature)
        public_key.verify(expected_signature, b"")

    def test_ed25519_rejects_changed_message_and_signature(self):
        seed = bytes.fromhex(
            "9d61b19deffd5a60ba844af492ec2cc4"
            "4449c5697b326919703bac031cae7f60"
        )
        private_key = Ed25519PrivateKey.from_private_bytes(seed)
        public_key = private_key.public_key()
        signature = private_key.sign(b"authorization payload")

        with self.assertRaises(InvalidSignature):
            public_key.verify(signature, b"modified payload")
        with self.assertRaises(InvalidSignature):
            public_key.verify(signature[:-1] + bytes([signature[-1] ^ 1]),
                              b"authorization payload")


class JcsRfc8785ConformanceTests(unittest.TestCase):
    def test_rfc8785_section_3_sample_canonical_bytes(self):
        source = r'''{
          "numbers": [333333333.33333329, 1E30, 4.50,
                      2e-3, 0.000000000000000000000000001],
          "string": "\u20ac$\u000F\u000aA'\u0042\u0022\u005c\\\"\/",
          "literals": [null, true, false]
        }'''
        value = json.loads(source)
        expected = (
            '{"literals":[null,true,false],'
            '"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],'
            '"string":"€$\\u000f\\nA\'B\\\"\\\\\\\\\\\"/"}'
        ).encode("utf-8")
        self.assertEqual(expected, rfc8785.dumps(value))

    def test_rfc8785_appendix_b_number_boundaries(self):
        cases = [
            (1e-6, b"0.000001"),
            (1e-7, b"1e-7"),
            (1e20, b"100000000000000000000"),
            (1e21, b"1e+21"),
            (1e30, b"1e+30"),
            (1e-27, b"1e-27"),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(expected, rfc8785.dumps(value))

    def test_property_order_uses_utf16_code_units(self):
        # U+1F600 starts with UTF-16 high surrogate D83D, which sorts
        # before U+E000. Unicode code-point ordering would give the reverse.
        value = {"\ue000": 1, "\U0001f600": 2}
        self.assertEqual(
            '{"😀":2,"":1}'.encode("utf-8"),
            rfc8785.dumps(value),
        )

    def test_non_finite_numbers_and_lone_surrogates_fail_closed(self):
        for value in (float("nan"), float("inf"), float("-inf"), "\ud800"):
            with self.subTest(value=repr(value)):
                with self.assertRaises(Exception):
                    rfc8785.dumps(value)


if __name__ == "__main__":
    unittest.main()
