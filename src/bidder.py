# !/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------- IMPORTS ----------------------------------------------------- #

import logging
from typing import Optional, List
from random import randint, sample, shuffle
from sys import byteorder
from Crypto.PublicKey import RSA

from src.participant import Participant
from src.utils.crypto import commit, encrypt, sign


__author__ = 'Denis Verstraeten'
__date__ = '2020.3.6'


class Bidder(Participant):
    """
    This class handles a bidder.
    """

    # ------------------------------------------------- CONSTRUCTOR ------------------------------------------------- #

    def __init__(self,
                 name: Optional[str] = None,
                 bid: Optional[int] = None,
                 address: Optional[str] = None,
                 generate_new_keys: Optional[bool] = True
                 ) -> None:
        """
        :param name: Name of the bidder.
        :param bid: Amount of the bid.
        :param address: Address of the bidder.
        :param generate_new_keys: Flag indicating whether new RSA keys need to be generated.
        """

        logging.info('Creating Bidder.')
        super().__init__(address, generate_new_keys)
        self.name = name
        self.bid = bid
        self.auctioneer_pub_key = None
        self.ring = None
        self.s = None
        logging.info('Bidder created.')

    # --------------------------------------------------- METHODS --------------------------------------------------- #

    def make_ring(self,
                  keys: List[RSA.RsaKey]
                  ) -> None:
        """
        Builds a ring of possible signers.
        :param keys: Keys from which the ring is constructed.
        """
        logging.info('Making ring for bidder.')
        self.ring = [self.public_key, self.auctioneer_pub_key]
        self.ring.extend(sample(list(filter(
            lambda key: key != self.public_key and key != self.auctioneer_pub_key, keys)), randint(0, len(keys) - 2)))
        shuffle(self.ring)
        self.s = self.ring.index(self.public_key)
        logging.info(f'Ring of size {len(self.ring)} created. s = {self.s}.')

    def sign(self,
             msg: bytes
             ) -> bytes:
        """
        Signs a message msg using a ring signature scheme.
        :param msg: Message to be signed.
        :return: Signature: List[int].
        """

        return sign(self.ring, self.s, msg)

    def __repr__(self) -> str:
        """
        :return: str representation of Bidder.
        """

        return f'Bidder(name: {self.name}, bid: {self.bid})' if self.address is None else \
            f'Bidder(name: {self.name}, bid: {self.bid}, address: {self.address})'
