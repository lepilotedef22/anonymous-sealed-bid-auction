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
        self.winning_com = None
        self.winning_bidder = None

    # --------------------------------------------------- METHODS --------------------------------------------------- #

    def bid_opening(self,
                    address: str,
                    ring: List[RSA.RsaKey],
                    c: bytes,
                    sig: bytes,
                    tau_1: bytes
                    ) -> bool:
        """
        Opens the bid value for bidder at address and stores it.
        :param address: Address of the bidder.
        :param ring: Ring of public keys used by the bidder for the Ring Signature.
        :param c: Commitment to the bid.
        :param sig: Ring Signature to the bid.
        :param tau_1: Bid opening token.
        :return: Whether the bid opening was successful.
        """
        logging.info(f'Opening bid for bidder at {address}.')
        status = False
        logging.info('Parsing sigma.')
        sigma, c1, c2 = parse(sig)
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
                        if commit_verify(bid, d, c):
                            logging.info('Commitment to bid successfully verified.')
                            logging.info('Storing bid and validating opening.')
                            self.bidders[address] = {
                                'bid': int.from_bytes(bid, byteorder),
                                'com': c,
                                'decom': d
                            }
                            logging.info(f'Bid: {int.from_bytes(bid, byteorder)}.')
                            status = True

        return status

    def identity_opening(self,
                         sig: bytes,
                         tau_2
                         ) -> bool:
        """
        Opens the identity of the winning bidder, checks its validity and stores it.
        :param sig: Ring signature.
        :param tau_2: Identity opening token.
        :return: Verification status of the opening.
        """
        logging.info('Opening identity if winning bidder.')
        status = False
        logging.info('Parsing sigma.')
        sigma, c1, c2 = parse(sig)
        logging.info('Parsing tau_2.')
        C2, d2 = parse(tau_2)
        if commit_verify(C2, d2, c2):
            logging.info('Commitment c2 successfully verified.')
            m2 = self.decrypt(C2)
            logging.info('C2 decrypted.')
            c, pub_key_winner, pub_key_auctioneer, sig, Sigma, delta = parse(m2)
            pub_key_winner = RSA.importKey(pub_key_winner)
            pub_key_auctioneer = RSA.importKey(pub_key_auctioneer)
            if c == self.winning_com:
                logging.info('Commitment c successfully verified.')
                if self.verify(c + sig + Sigma, delta, [pub_key_winner, pub_key_auctioneer]):
                    logging.info('Signature delta successfully verified.')
                    self.winning_bidder = pub_key_winner
                    logging.info(f'Winning bidder: {self.winning_bidder}.')
                    status = True

        return status

    def get_winning_commitment(self) -> None:
        """
        TEMPORARY METHOD !!! Will be deleted once ZKP is implemented.
        Gets the winning bid value and the winning commitment.
        """
        logging.info('Getting winning bid.')
        max_bid = 0
        for bidder in self.bidders.values():
            x = bidder['bid']
            c = bidder['com']
            d = bidder['decom']
            if not commit_verify(x.to_bytes(int(256 / 8), byteorder), d, c):
                logging.info('Commit verification failed.')
                continue

            if x > max_bid:
                max_bid = x
                self.winning_com = c

        logging.info(f'Winning bid is {max_bid}.')

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

    def __repr__(self) -> str:
        """
        :return: str representation of Auctioneer.
        """
        return f'Auctioneer(address: {self.address})'
