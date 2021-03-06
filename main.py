# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This file is the main script for the anonymous hidden auction proof of concept.
"""

# ----------------------------------------------------- IMPORTS ----------------------------------------------------- #

from argparse import ArgumentParser
import logging
from requests.exceptions import ConnectionError

from src.auction import Auction


__author__ = 'Denis Verstraeten'
__date__ = '2020.3.4'


if __name__ == '__main__':
    # Args parsing (credit: https://docs.python.org/fr/3/howto/argparse.html)
    parser = ArgumentParser(
        description='Anonymous Sealed-Bid Auction Proof of Concept launcher'
    )
    parser.add_argument(
        '-l',
        '--log',
        action='store',
        help='Logger level',
        default='critical',
        choices=[
            'debug',
            'info',
            'warning',
            'error',
            'critical'
        ])
    parser.add_argument(
        '-m',
        '--mode',
        action='store',
        help='Feature to be executed',
        default='deploy',
        choices=[
            'deploy',
            'poc',
            'gas'
        ]
    )
    parser.add_argument(
        '-o',
        '--output',
        action='store',
        help='File name for the gas csv file'
    )
    parser.add_argument(
        '-f',
        '--functions',
        help='Functions to store in the output file',
        nargs='+'
    )
    parser.add_argument(
        '-p',
        '--price',
        action='store_true',
        help='Displays the total price of the auction for each participant at the end of the simulation.'
    )
    args = vars(parser.parse_args())
    # Logging (credit: https://docs.python.org/3/howto/logging.html)
    numeric_level = getattr(logging, args['log'].upper(), None)
    logging.basicConfig(format='%(levelname)s: %(filename)s: %(funcName)s(): %(message)s',
                        level=numeric_level)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('web3').setLevel(logging.WARNING)
    # Args parsing
    mode = args['mode']
    output_file = args['output']
    functions = args['functions']
    show_price = args['price']
    auction = Auction()
    try:
        if mode == 'deploy':
            auction.deploy()

        elif mode == 'gas':
            auction.estimate_gas(output_file, functions)

        elif mode == 'poc':
            auction.proof_of_concept(show_price)

    except ConnectionError as e:
        print('Cannot connect to Ganache.')
        print('Make sure that Ganache is running and try again...')
