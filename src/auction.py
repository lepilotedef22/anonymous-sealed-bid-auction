# !/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------- IMPORTS ----------------------------------------------------- #

import logging
from pathlib import Path
from web3 import Web3
from json import loads, dump
from solc import compile_standard
from random import randint, getrandbits, sample, shuffle
from sys import byteorder
from typing import Optional
from hexbytes import HexBytes

from src.auctioneer import Auctioneer
from src.utils.file_helper import get_bidders
from src.bidder import Bidder
from src.utils.crypto import commit


__author__ = 'Denis Verstraeten'
__date__ = '2020.3.4'


class Auction:
    """
    This class handles everything which is related to the auction. TODO: improve docs.
    """

    # ------------------------------------------------- CONSTRUCTOR ------------------------------------------------- #

    def __init__(self) -> None:

        logging.info('Creating Auction object.')
        self.__w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:7545'))
        self.__contract = None
        self.__abi = None
        self.__is_deployed = False
        self.__auctioneer = None
        self.__bidders = []
        self.__thread_is_running = True
        self.__total_gas_cost = 0
        logging.info('Auction object created.')

    # --------------------------------------------------- METHODS --------------------------------------------------- #

    def deploy(self) -> None:
        """
        This method deploys the Auction smart contract on the Ganache Ethereum local chain.
        See: https://www.trufflesuite.com/ganache
        Credit: https://web3py.readthedocs.io/en/stable/contracts.html
        Credit: https://github.com/ethereum/py-solc
        """

        logging.info('Deploying Auction smart contract on chain.')
        logging.info('Compiling smart contract source code into bytecode using solc.')
        contract_path = Path.cwd() / 'contracts' / 'auction.sol'
        logging.info(f'Contract path: {contract_path}.')
        compiled = compile_standard(
            {
                'language': 'Solidity',
                'sources': {
                    'auction.sol': {
                        'urls': [str(contract_path)]
                    }
                },
                'settings': {
                    'outputSelection': {
                        '*': {
                            '*': [
                                'metadata',
                                'evm.bytecode',
                                'evm.bytecode.sourceMap'
                            ]
                        }
                    }
                }
            },
            allow_paths=str(contract_path)
        )
        self.__w3.eth.defaultAccount = self.__w3.eth.accounts[0]  # First account is default account.
        bytecode = compiled['contracts']['auction.sol']['Auction']['evm']['bytecode']['object']
        self.__abi = loads(compiled['contracts']['auction.sol']['Auction']['metadata'])['output']['abi']
        logging.info('Creating temporary contract object.')
        temp_contract = self.__w3.eth.contract(abi=self.__abi,
                                               bytecode=bytecode)
        logging.info('Transacting contract on the chain.')
        tx_hash = temp_contract.constructor().transact()
        logging.info(f'Transaction hash: {tx_hash.hex()}.')
        tx_receipt = self.__w3.eth.waitForTransactionReceipt(tx_hash)
        contract_address = tx_receipt.contractAddress
        gas_used = tx_receipt.gasUsed
        logging.info(f'Gas used for transaction {tx_hash.hex()}: {gas_used} gas.')
        self.__total_gas_cost += gas_used
        logging.info(f'Contract address: {contract_address}.')
        data = {
            'abi': self.__abi,
            'bytecode': bytecode,
            'contractAddress': contract_address
        }
        compile_path = Path.cwd() / 'compile'
        if not compile_path.exists():
            compile_path.mkdir(parents=True, exist_ok=True)
        with open(Path.cwd() / 'compile' / 'out.json', 'w') as output_file:
            logging.info('Storing abi, bytecode and contract address in compile/out.json.')
            dump(data, output_file, indent=4)
            logging.info('Abi, bytecode and address stored.')
        logging.info('Connecting to actual smart contract.')

        self.__contract = self.__w3.eth.contract(address=contract_address,
                                                 abi=self.__abi)
        logging.info('Connected to smart contract.')
        self.__is_deployed = True
        print('Auction smart contract successfully deployed.')

    def estimate_gas(self) -> None:
        """
        This method estimates the gas consumption of the functions of the contract.
        """

        if not self.__is_deployed:

            logging.info('Deploying smart contract.')
            self.deploy()

        rand_gen = {
            'uint256': lambda: randint(0, 2**256 - 1),
            'bytes': lambda: getrandbits(8 * 32).to_bytes(32, byteorder),
            'address': lambda: getrandbits(8 * 20).to_bytes(20, byteorder)
        }

        logging.info('Estimating gas consumption of smart contract functions.')
        print('\t--------------------------------------------')
        print('\t| Gas consumption of individual functions: |')
        print('\t--------------------------------------------')
        for smart_contract_function in self.__contract.all_functions():

            func_name = getattr(smart_contract_function, 'fn_name')
            logging.info(f'Function name: {func_name}.')
            for func_abi_dic in self.__abi:

                try:

                    if func_abi_dic['name'] == func_name:

                        logging.info(f'Match found for function {func_name}.')
                        abi_inputs = func_abi_dic['inputs']
                        input_types = list(map(lambda arg: arg['type'], abi_inputs))
                        inputs = list(map(lambda arg_type: rand_gen[arg_type](), input_types))
                        logging.info(f'Inputs: '
                                     f'{", ".join([f"{input_types[i]}={inputs[i]}" for i in range(len(inputs))])}')
                        func = self.__contract.functions[func_name]
                        try:

                            gas = func(*inputs).estimateGas()
                            print(f'{func_name}({", ".join(input_types)}): {gas} gas.')

                        except ValueError:

                            logging.info('Passed inputs are not accepted by the function.')

                except KeyError:

                    pass

        logging.info('Gas consumption estimated.')

    def proof_of_concept(self) -> None:
        """
        This method implements the proof of concept.
        """

        if not self.__is_deployed:

            logging.info('Deploying smart contract.')
            self.deploy()

        # Registering filters
        z_i_filter = self.__contract.events.submittedZ_i.createFilter(fromBlock='latest')
        c_i1_filter = self.__contract.events.submittedC_i1.createFilter(fromBlock='latest')

        # Generating auctioneer and bidders
        self.__auctioneer = Auctioneer(address=self.__w3.eth.defaultAccount)
        logging.info(f'Auctioneer created: {self.__auctioneer}.')
        self.__bidders = get_bidders(Path('bidders.json'))  # If new file is created,
        # max number of bidders must be < number of accounts on the blockchain.

        bidder_addresses = sample(self.__w3.eth.accounts[1:], len(self.__bidders))
        # Randomly picks n = len(self.__bidders) addresses out of the accounts list.
        # Element zero is excluded because it is auctioneer address.

        for (index, bidder) in enumerate(self.__bidders):

            bidder.address = bidder_addresses[index]
            bidder.auctioneer_pub_key = self.__auctioneer.public_key

        logging.debug(f'Bidders created: {self.__bidders}.')

        # Generating ring of public keys
        keys = [self.__auctioneer.public_key]
        for bidder in self.__bidders:

            keys.append(bidder.public_key)

        shuffle(keys)
        self.__auctioneer.set_ring(keys)
        for bidder in self.__bidders:

            bidder.set_ring(keys)

        # Generating and sending bidder's commitments
        data_lengths = {}  # Will be used later to help parsing concatenated messages. Not very elegant.
        for bidder in self.__bidders:

            logging.info(f'Generating and sending messages for bidder {bidder.name} at {bidder.address}.')
            bidder.generate_commitments()
            data_lengths[bidder.address] = {
                'r_i': len(bidder.r_i),
                'c_i': len(bidder.c_i),
                'sigma_i': len(bidder.sigma_i),
                'Sigma_i': len(bidder.Sigma_i),
                'bid': int(256 / 8),
                'delta_i': len(bidder.delta_i),
                'PK_bidder': len(bidder.public_key.export_key()),
                'PK_auctioneer': len(bidder.auctioneer_pub_key.export_key())
            }
            tx = {
                'from': bidder.address,
                'to': self.__contract.address
            }
            self.__send_transaction(tx,
                                    'submitZ_i',
                                    bidder.c_i.hex(),
                                    bidder.sigma_i.hex(),
                                    bidder.com_i1.hex(),
                                    bidder.com_i2.hex())

        # Auctioneer storing commitments
        for event in z_i_filter.get_new_entries():

            bidder_address = event['args']['bidderAddress']
            event_name = event['event']
            logging.info(f'Catching event {event_name} from bidder at {bidder_address}.')
            c_i = event['args']['c_i']
            sigma_i = event['args']['sigma_i']
            if self.__auctioneer.verify(c_i, sigma_i):

                logging.info('Valid signature.')
                bidder = Bidder(address=bidder_address,
                                generate_new_keys=False)
                bidder.c_i = c_i
                bidder.sigma_i = sigma_i
                bidder.com_i1 = event['args']['com_i1']
                bidder.com_i2 = event['args']['com_i2']
                self.__auctioneer.bidders[bidder_address] = bidder

                logging.info(f'Storing Z_i for bidder at {bidder_address}.')
                tx = {
                    'from': self.__auctioneer.address,
                    'to': self.__contract.address
                }
                self.__send_transaction(tx,
                                        'storeZ_i',
                                        bidder_address,
                                        bidder.c_i.hex(),
                                        bidder.sigma_i.hex(),
                                        bidder.com_i1.hex(),
                                        bidder.com_i2.hex())

            else:

                logging.info(f'Invalid signature for bidder at {bidder_address}.')
                self.__black_list_bidder(bidder_address)

        # Sending C_i1
        for bidder in self.__bidders:

            logging.info(f'Sending C_i1 for bidder {bidder.name} at {bidder.address}.')
            tx = {
                'from': bidder.address,
                'to': self.__contract.address
            }
            self.__send_transaction(tx,
                                    'submitC_i1',
                                    bidder.C_i1.hex(),
                                    int.from_bytes(bidder.r_i1, byteorder))

        # Getting C_i1 and finding out winning bidder
        winning_bid = 0
        winning_bidder_address = None
        for event in c_i1_filter.get_new_entries():

            bidder_address = event['args']['bidderAddress']
            event_name = event['event']
            logging.info(f'Catching event {event_name} from bidder at {bidder_address}.')
            if bidder_address in self.__auctioneer.bidders.keys():

                c_i1 = event['args']['C_i1']
                r_i1 = event['args']['r_i1'].to_bytes(int(256 / 8), byteorder)
                if commit(c_i1, r_i1) == self.__auctioneer.bidders[bidder_address].com_i1:

                    logging.info('C_i1 and r_i1 match commitment com_i1.')
                    m_i1 = self.__auctioneer.decrypt(c_i1)

                    # Parsing data in m_i1
                    length = data_lengths[bidder_address]
                    c_i = m_i1[:length['c_i']]
                    sigma_i = m_i1[length['c_i']: length['c_i'] + length['sigma_i']]
                    Sigma_i = m_i1[length['c_i'] + length['sigma_i']:
                                   length['c_i'] + length['sigma_i'] + length['Sigma_i']]
                    x_i = m_i1[length['c_i'] + length['sigma_i'] + length['Sigma_i']:
                               length['c_i'] + length['sigma_i'] + length['Sigma_i'] + length['bid']]
                    r_i = m_i1[length['c_i'] + length['sigma_i'] + length['Sigma_i'] + length['bid']:
                               length['c_i'] + length['sigma_i'] + length['Sigma_i'] + length['bid'] + length['r_i']]

                    if c_i == self.__auctioneer.bidders[bidder_address].c_i and commit(x_i, r_i) == c_i:

                        logging.info('bid and r_i match commitment c_i.')
                        if sigma_i == self.__auctioneer.bidders[bidder_address].sigma_i and \
                                self.__auctioneer.verify(c_i, sigma_i):

                            logging.info('Valid signature sigma_i on c_i.')
                            if self.__auctioneer.verify(c_i + sigma_i, Sigma_i):

                                logging.info('Valid signature Sigma_i on c_i||sigma_i.')
                                if x_i > winning_bid:

                                    logging.info('New winning bid.')
                                    winning_bid = x_i
                                    winning_bidder_address = bidder_address

                                logging.info(f'Storing C_i1 and r_i1 for bidder at {bidder_address}.')
                                tx = {
                                    'from': self.__auctioneer.address,
                                    'to': self.__contract.address
                                }
                                self.__send_transaction(tx,
                                                        'storeC_i1',
                                                        c_i1.hex(),
                                                        int.from_bytes(r_i1, byteorder))

                            else:

                                logging.info('Invalid signature Sigma_i on c_i||sigma_i.')
                                self.__black_list_bidder(bidder_address)

                        else:

                            logging.info('Invalid signature sigma_i on c_i.')
                            self.__black_list_bidder(bidder_address)

                    else:

                        logging.info('bid and r_i do not match commitment c_i.')
                        self.__black_list_bidder(bidder_address)

                else:

                    logging.info('C_i1 and r_i1 do not match com_i1.')
                    self.__black_list_bidder(bidder_address)

            else:

                logging.info(f'Bidder at {bidder_address} not among registered bidders.')
                self.__black_list_bidder(bidder_address)

    def __send_transaction(self,
                           transaction,
                           func_name: Optional[str] = None,
                           *args
                           ) -> None:
        """
        Executes a transaction. Can be the execution of a smart contract function.
        :param func_name: Optional name of the smart contract function to be executed.
        :param args: Argument to be passed to the function.
        :param transaction: Transaction data.
        """

        if func_name is not None:

            logging.info(f'Executing function {func_name}.')
            tx_hash = self.__contract.functions[func_name](*args).transact(transaction)

        else:

            logging.info('Executing transaction.')
            tx_hash = self.__w3.eth.sendTransaction(transaction)

        logging.info(f'Transaction hash: {tx_hash.hex()}.')
        self.__gas_cost(tx_hash)

    def __gas_cost(self,
                   tx_hash: HexBytes
                   ) -> None:
        """
        Adds the gas cost of the transaction to self.__total_gas_cost.
        :param tx_hash: Hash of the transaction whose gas cost should be added.
        """

        tx_receipt = self.__w3.eth.waitForTransactionReceipt(tx_hash)
        gas_used = tx_receipt.gasUsed
        logging.info(f'Gas used for transaction {tx_hash.hex()}: {gas_used} gas.')
        self.__total_gas_cost += gas_used
        logging.info(f'Total gas cost: {self.__total_gas_cost} gas.')

    def __black_list_bidder(self,
                            bidder_address: str
                            ) -> None:
        """
        Black list bidder by calling the smart contract function.
        :param bidder_address: Address of the bidder to be black listed.
        """

        logging.info(f'Black listing bidder at {bidder_address}.')
        tx = {
            'from': self.__auctioneer.address,
            'to': self.__contract.address
        }
        self.__send_transaction(tx,
                                'blackListBidder',
                                bidder_address)
        logging.info(f'Bidder at {bidder_address} black listed.')
