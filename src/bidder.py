# !/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------- IMPORTS ----------------------------------------------------- #

import logging
from typing import Optional
from random import randint
from sys import byteorder

from src.participant import Participant
from src.utils.crypto import commit, encrypt


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
        self.r_i = None
        self.c_i = None
        self.sigma_i = None
        self.Sigma_i = None
        self.C_i1 = None
        self.r_i1 = None
        self.com_i1 = None
        self.delta_i = None
        self.C_i2 = None
        self.r_i2 = None
        self.com_i2 = None
        logging.info('Bidder created.')

    # --------------------------------------------------- METHODS --------------------------------------------------- #

    def generate_commitments(self) -> None:
        """
        Generates the different commitments that needs to be sent to the blockchain.
        It is advised to read this along the paper to get a better understanding of the variable names.
        """

        self.r_i = randint(0, 2*256 - 1).to_bytes(int(256 / 8), byteorder)
        logging.debug(f'r_i = {int.from_bytes(self.r_i, byteorder)}.')
        self.c_i = commit(self.bid.to_bytes(int(256 / 8), byteorder), self.r_i)
        logging.debug(f'c_i = {self.c_i.hex()}.')
        self.sigma_i = self.sign(self.c_i)
        logging.debug(f'sigma_i = {self.sigma_i.hex()}.')
        self.Sigma_i = self.sign(self.c_i + self.sigma_i)
        logging.debug(f'Sigma_i = {self.Sigma_i.hex()}.')
        self.C_i1 = encrypt(
            self.c_i + self.sigma_i + self.Sigma_i + self.bid.to_bytes(int(256 / 8), byteorder) + self.r_i,
            self.auctioneer_pub_key
        )
        logging.debug(f'C_i1 = {self.C_i1.hex()}.')
        self.r_i1 = randint(0, 2*256 - 1).to_bytes(int(256 / 8), byteorder)
        logging.debug(f'r_i1 = {int.from_bytes(self.r_i1, byteorder)}.')
        self.com_i1 = commit(self.C_i1, self.r_i1)
        logging.debug(f'com_i1 = {self.com_i1.hex()}.')
        self.delta_i = self.sign(self.c_i + self.sigma_i + self.Sigma_i)
        logging.debug(f'delta_i = {self.delta_i.hex()}.')
        self.C_i2 = encrypt(
            self.c_i + self.public_key.export_key() + self.auctioneer_pub_key.export_key() + self.Sigma_i +
            self.delta_i,
            self.auctioneer_pub_key
        )
        logging.debug(f'C_i2 = {self.C_i2.hex()}.')
        self.r_i2 = randint(0, 2*256 - 1).to_bytes(int(256 / 8), byteorder)
        logging.debug(f'r_i2 = {int.from_bytes(self.r_i2, byteorder)}')
        self.com_i2 = commit(self.C_i2, self.r_i2)
        logging.debug(f'com_i2 = {self.com_i2.hex()}.')

    def __repr__(self) -> str:
        """
        :return: str representation of Bidder.
        """

        return f'Bidder(name: {self.name}, bid: {self.bid})' if self.address is None else \
            f'Bidder(name: {self.name}, bid: {self.bid}, address: {self.address})'
