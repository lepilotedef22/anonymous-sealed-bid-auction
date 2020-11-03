# !/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------- IMPORTS ----------------------------------------------------- #

import logging
from typing import Optional

from src.participant import Participant
from src.utils.crypto import decrypt


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

    def __repr__(self) -> str:
        """
        :return: str representation of Auctioneer.
        """

        return f'Auctioneer(address: {self.address})'
