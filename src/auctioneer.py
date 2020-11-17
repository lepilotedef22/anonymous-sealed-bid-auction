# !/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------- IMPORTS ----------------------------------------------------- #

import logging
from typing import Optional, List
from Crypto.PublicKey import RSA
from sys import byteorder

from src.participant import Participant
from src.utils.crypto import decrypt, verify, parse, commit_verify


__author__ = 'Denis Verstraeten'
__date__ = '2020.3.5'


class Auctioneer(Participant):
    """
    This class handles the auctioneer.
    """

    # ------------------------------------------------- CONSTRUCTOR ------------------------------------------------- #

    def __init__(self,
                 address: str,
                 generate_new_keys: Optional[bool] = True
                 ) -> None:
        """
        :param address: Address of the auctioneer.
        :param generate_new_keys: Flag indicating whether new RSA keys need to be generated.
        """
        logging.info('Creating auctioneer.')
        super().__init__(address, generate_new_keys)
        self.bidders = {}

    # --------------------------------------------------- METHODS --------------------------------------------------- #

    def decrypt(self,
                cipher: bytes
                ) -> bytes:
        """
        Uses RSA to decrypt cipher text.
        :return: Plain text.
        """
        logging.debug(f'Cipher text: {cipher.hex()}.')
        plain = decrypt(cipher, self._RSA_key)
        logging.debug(f'Plain text: {plain}.')
        return plain

    def verify(self,
               msg: bytes,
               sig: bytes,
               ring: List[RSA.RsaKey]
               ) -> bool:
        """
        Verifies that a message msg has valid signature sig.
        :param msg: Signed message.
        :param sig: Ring signature.
        :param ring: Ring of keys to be used to check the validity of the signature.
        :return: Validity of signature.
        """
        return verify(sig, msg, ring)

    def bid_opening(self,
                    address: str,
                    ring: List[RSA.RsaKey],
                    c: bytes,
                    sigma: bytes,
                    tau_1: bytes
                    ) -> bool:
        """
        Opens the bid value for bidder at address and stores it.
        :param address: Address of the bidder.
        :param ring: Ring of public keys used by the bidder for the Ring Signature.
        :param c: Commitment to the bid.
        :param sigma: Ring Signature to the bid.
        :param tau_1: Bid opening token.
        :return: Whether th bid opening was successful.
        """
        logging.info(f'Opening bid for bidder at {address}.')
        status = False
        logging.info('Parsing sigma.')
        sigma, c1, c2 = parse(sigma)
        if self.verify(c, sigma, ring):
            logging.info('Signature sigma successfully verified.')
            C1, d1 = parse(tau_1)
            if commit_verify(C1, d1, c1):
                logging.info('Commitment C1 successfully verified.')
                m1 = self.decrypt(C1)
                logging.info('Cipher text C1 decrypted.')
                logging.info('Parsing m1.')
                c_tilde, sigma_tilde, Sigma, bid, d = parse(m1)
                if c_tilde == c and sigma_tilde == sigma:
                    if self.verify(c + sigma, Sigma, ring):
                        logging.info('Signature Sigma verified.')
                        if commit_verify(bid, c, d):
                            logging.info('Commitment to bid successfully verified.')
                            logging.info('Storing bid and validating opening.')
                            self.bidders[address] = {
                                'bid': int.from_bytes(bid, byteorder),
                                'd': d
                            }
                            logging.info(f'Bid: {int.from_bytes(bid, byteorder)}.')
                            status = True

        return status

    def __repr__(self) -> str:
        """
        :return: str representation of Auctioneer.
        """
        return f'Auctioneer(address: {self.address})'
