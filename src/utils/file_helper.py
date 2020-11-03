# !/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------- IMPORTS ----------------------------------------------------- #

import logging
from typing import List, Optional
from pathlib import Path
from json import load, dump
from random import randint

from src.bidder import Bidder


__author__ = 'Denis Verstraeten'
__date__ = '2020.3.29'


def get_bidders(bidder_file: Path,
                bidders_number: Optional[int] = 6,
                min_bid: Optional[int] = 0,
                max_bid: Optional[int] = 20
                ) -> List[Bidder]:
    """
    Parses the file in which the bidder data is stored.
    Data structure in bidder_file: {'bidders': [{'name': bidder_name, 'value': bid_value}]}
    :param bidder_file: File in which bidder data is stored. If file path does not exist,
    a new file is created at this path with randomly generated data.
    :param bidders_number: number of bidders to be generated.
    :param min_bid: min value  of the bids.
    :param max_bid: max value of the bids.
    :return: List of Bidder.
    """

    if bidder_file.exists():

        logging.info(f'Parsing data file: {bidder_file}.')
        with open(bidder_file, 'r') as file:

            data = load(file)
            bidders = list(map(lambda bidder: Bidder(bidder['name'], bidder['bid']), data['bidders']))
            logging.debug(f'Bidders: {bidders}.')
            return bidders

    else:

        logging.info(f'Creating/updating {bidder_file}.')
        bids = []
        bidders = []
        for i in range(bidders_number):

            name = f'bidder{i}'
            bid = randint(min_bid, max_bid)
            while bid in bids:

                bid = randint(min_bid, max_bid)

            bids.append(bid)
            bidders.append(Bidder(name, bid))

        with open(bidder_file, 'w') as file:

            data = {
                'bidders': list(map(lambda bidder: {
                    'name': bidder.name,
                    'bid': bidder.bid
                }, bidders))
            }
            logging.debug(f'Data to be stored: {data}.')
            dump(data, file)

        logging.debug(f'Bidders: {bidders}.')
        return bidders
