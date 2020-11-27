# !/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------- IMPORTS ----------------------------------------------------- #

import logging
from typing import Optional, List, Tuple
from random import randint, sample, shuffle
from Crypto.PublicKey import RSA
from sys import byteorder

from src.participant import Participant
from src.utils.crypto import sign, commit, encrypt, concatenate

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
        self.__name = name
        self.__bid_value = bid
        self.auctioneer_pub_key = None
        self.ring = None
        self.__s = None
        self.c = None
        self.__d = None
        self.sigma = None
        self.__Sigma = None
        self.C1 = None
        self.c1 = None
        self.d1 = None
        self.__delta = None
        self.C2 = None
        self.c2 = None
        self.d2 = None
        self.sig = None
        self.tau_1 = None
        self.tau_2 = None
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
        self.__s = self.ring.index(self.public_key)
        self.ring[self.__s] = self._RSA_key
        logging.info(f'Ring of size {len(self.ring)} created. s = {self.__s}.')
        logging.debug(f'Ring: {self.ring}.')

    def bid(self) -> Tuple[bytes, bytes]:
        """
        :return: Commitments and signatures to the bid to be placed.
        """
        logging.info('Generating bid.')
        logging.info('Computing c and d.')
        self.c, self.__d = commit(self.__bid_value.to_bytes(int(256 / 8), byteorder))
        logging.info('Computing sigma.')
        self.sigma = self.__sign(self.c)
        logging.info('Computing Sigma.')
        self.__Sigma = self.__sign(self.c + self.sigma)
        logging.info('Computing C1.')
        self.C1 = self.__encrypt(concatenate(self.c, self.sigma, self.__Sigma,
                                             self.__bid_value.to_bytes(int(256 / 8), byteorder), self.__d))
        logging.info('Computing c1 and d1.')
        self.c1, self.d1 = commit(self.C1)
        logging.info('Computing delta.')
        self.__delta = self.__sign2(self.c + self.sigma + self.__Sigma)
        logging.info('Computing C2.')
        m2 = concatenate(self.c, self.public_key.exportKey(), self.auctioneer_pub_key.exportKey(), self.sigma,
                         self.__Sigma, self.__delta)
        self.C2 = self.__encrypt(m2)
        logging.info('Computing c2 and d2.')
        self.c2, self.d2 = commit(self.C2)
        logging.info('Bid generated.')
        self.sig = concatenate(self.sigma, self.c1, self.c2)
        self.tau_1 = concatenate(self.C1, self.d1)
        self.tau_2 = concatenate(self.C2, self.d2)
        return self.c, self.sig

    def export_ring(self) -> bytes:
        """
        :return: The concatenation of the keys of the ring.
        """
        return concatenate(*list(map(lambda key: key.publickey().exportKey(), self.ring)))

    def __sign(self,
               msg: bytes
               ) -> bytes:
        """
        Signs a message msg using a ring signature scheme.
        :param msg: Message to be signed.
        :return: Signature: List[int].
        """
        return sign(self.ring, self.__s, msg)

    def __sign2(self,
                msg: bytes
                ) -> bytes:
        """
        Signs a message msg using a ring signature scheme with the designated identity verifier small ring R2.
        :param msg: Message to be signed.
        :return: Signature: List[int].
        """
        return sign([self._RSA_key, self.auctioneer_pub_key], 0, msg)

    def __encrypt(self,
                  plain: bytes
                  ) -> bytes:
        """
        :param plain: Message to be encrypted.
        :return: Encryption of plain.
        """
        return encrypt(plain, self.auctioneer_pub_key)

    def __repr__(self) -> str:
        """
        :return: str representation of Bidder.
        """

        return f'Bidder(name: {self.__name}, bid: {self.__bid_value}, address: {self.address}, key: {self.public_key})'
