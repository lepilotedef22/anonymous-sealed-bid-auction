# !/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------- IMPORTS ----------------------------------------------------- #

from __future__ import annotations
import logging
from abc import ABC
from Crypto.PublicKey import RSA
from typing import List

from src.utils.crypto import sign, verify


__author__ = 'Denis Verstraeten'
__date__ = '2020.3.5'


class Participant(ABC):
    """
    This super class handles everything related to participants of the auction.
    It should be extended in Auctioneer and in Bidder.
    """

    # ------------------------------------------------- CONSTRUCTOR ------------------------------------------------- #

    def __init__(self,
                 address: str,
                 generate_new_keys: bool
                 ) -> None:
        """
        :param address: Address of the Participant.
        :param generate_new_keys: Flag indicating whether new RSA keys need to be generated.
        """

        logging.info('Creating Participant.')
        self.address = address
        if generate_new_keys:

            self._RSA_key = RSA.generate(2048)
            self.public_key = self._RSA_key.publickey()

        else:

            self._RSA_key = None
            self.public_key = None

        self._ring = None  # List of public keys used for the ring signature scheme.
        self._s = None  # Index of the Participant in the ring. self._ring[s] = self.public_key.

    # --------------------------------------------------- METHODS --------------------------------------------------- #

    def set_ring(self,
                 keys: List[RSA.RsaKey]
                 ) -> None:
        """
        Stores the ring of public keys used for ring signature and the index of the Participant.
        :param keys: List of public keys.
        """

        self._ring = keys
        self._s = self._ring.index(self.public_key)
        self._ring[self._s] = self._RSA_key
        logging.debug(f'Ring set. s = {self._s}.')

    def sign(self,
             msg: bytes
             ) -> bytes:
        """
        Signs a message msg using a ring signature scheme.
        :param msg: Message to be signed.
        :return: Signature: List[int].
        """

        return sign(self._ring, self._s, msg)

    def verify(self,
               msg: bytes,
               sig: bytes
               ) -> bool:
        """
        Verifies that a message msg has valid signature sig.
        :param msg: Signed message.
        :param sig: Ring signature.
        :return: Validity of signature.
        """

        return verify(sig, msg, self._ring)
