# !/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------- IMPORTS ----------------------------------------------------- #

from unittest import TestCase, main
from Crypto.PublicKey import RSA
from functools import reduce
from sys import byteorder

from src.utils.crypto import encrypt, decrypt, sign, verify


__author__ = 'Denis Verstraeten'
__date__ = '2020.3.30'


class CryptoTest(TestCase):
    """
    Unit tests for the crypto module.
    """

    key = RSA.generate(2048)
    ring_number = 5
    s = 2
    ring = []
    for index, key in enumerate([RSA.generate(2048) for _ in range(ring_number)]):

        ring.append(key.publickey() if index != s else key)

    # ---------------------------------------------------- TESTS ---------------------------------------------------- #

    def test_encryption_decryption_short(self):
        """
        Tests whether Dec(Enc(x)) = x for x shorter than 2048 bits.
        """

        msg = b'Hello world!'
        cipher = encrypt(msg, CryptoTest.key)
        plain = decrypt(cipher, CryptoTest.key)

        self.assertEqual(msg, plain)

    def test_encryption_decryption_long_multiple(self):
        """
        Tests whether Dec(Enc(x)) = x for len(x) > 2048 bits.
        """

        msg = reduce(bytes.__add__, [b'a' for _ in range(int(5000 / 8))])  # One character is one byte
        cipher = encrypt(msg, CryptoTest.key)
        plain = decrypt(cipher, CryptoTest.key)

        self.assertEqual(msg, plain)

    def test_valid_signature(self):
        """
        Tests whether a valid signature is successfully verified.
        """

        msg = b'Hello world!'
        signature = sign(CryptoTest.ring, CryptoTest.s, msg)

        self.assertTrue(verify(signature, msg, CryptoTest.ring))

    def test_invalid_signature_value(self):
        """
        Tests whether an invalid signature does not verify.
        """

        msg = b'Hello world!'
        signature = sign(CryptoTest.ring, CryptoTest.s, msg)
        signature = (int.from_bytes(signature, byteorder) + 1).to_bytes(len(signature) + 1, byteorder)

        self.assertFalse(verify(signature, msg, CryptoTest.ring))

    def test_invalid_signature_ring(self):
        """
        Tests whether the signature is invalid with another ring.
        """

        msg = b'Hello world!'
        signature = sign(CryptoTest.ring, CryptoTest.s, msg)
        CryptoTest.ring[CryptoTest.s] = CryptoTest.key

        self.assertFalse(verify(signature, msg, CryptoTest.ring))


# ------------------------------------------------------- MAIN ------------------------------------------------------- #

if __name__ == '__main__':
    main()
