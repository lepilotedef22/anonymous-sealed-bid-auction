# !/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------------------------------------- IMPORTS ----------------------------------------------------- #

import logging
from pathlib import Path
from web3 import Web3
from json import loads, dump
from solc import compile_standard
from random import randint, getrandbits, sample
from sys import byteorder
from typing import Optional, Any
from hexbytes import HexBytes

from src.auctioneer import Auctioneer
from src.utils.file_helper import get_bidders


__author__ = 'Denis Verstraeten'
__date__ = '2020.3.4'


class Auction:
    """
    This class handles everything which is related to the auction. TODO: improve docs.
    """

    # --- Constants --- #
    DEPOSIT = 50

    # ------------------------------------------------- CONSTRUCTOR ------------------------------------------------- #
    def __init__(self) -> None:
        logging.info('Creating Auction object.')
        self.__w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:7545'))
        self.__contract = None
        self.__abi = None
        self.__is_deployed = False
        self.__auctioneer = None
        self.__bidders = []
        self.__total_gas_cost = 0
        self.__number_of_tx = 0
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
        tx_hash = temp_contract.constructor(10, 10, 10, True, Auction.DEPOSIT).transact()
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
                        abi_state_mutability = func_abi_dic['stateMutability']
                        input_types = list(map(lambda arg: arg['type'], abi_inputs))
                        inputs = list(map(lambda arg_type: rand_gen[arg_type](), input_types))
                        logging.info(f'Inputs: '
                                     f'{", ".join([f"{input_types[i]}={inputs[i]}" for i in range(len(inputs))])}')
                        logging.info(f'State mutability: {abi_state_mutability}.')
                        func = self.__contract.functions[func_name]
                        try:
                            if abi_state_mutability == 'payable':
                                tx = {
                                    'value': Auction.DEPOSIT
                                }
                                gas = func(*inputs).estimateGas(tx)

                            else:
                                gas = func(*inputs).estimateGas()

                            print(f'{func_name}({", ".join(input_types)}): {gas} gas.')

                        except ValueError as e:
                            logging.info(f'Passed inputs are not accepted by the function. Error: {e}.')

                except KeyError:
                    pass

        logging.info('Gas consumption estimated.')

    def proof_of_concept(self) -> None:
        """
        This method implements the proof of concept.
        """
        # --- Deploying Smart Contract --- #
        if not self.__is_deployed:
            logging.info('Deploying smart contract.')
            self.deploy()

        # --- Generating auctioneer and bidders --- #
        self.__auctioneer = Auctioneer(address=self.__w3.eth.defaultAccount)
        logging.info(f'Auctioneer created: {self.__auctioneer}.')
        self.__bidders = get_bidders(Path('bidders.json'))  # If new file is created,
        # max number of bidders must be < number of accounts on the blockchain.
        pub_keys = list(map(lambda b: b.public_key, self.__bidders))
        pub_keys.append(self.__auctioneer.public_key)
        bidder_addresses = sample(self.__w3.eth.accounts[1:], len(self.__bidders))
        # Randomly picks n = len(self.__bidders) addresses out of the accounts list.
        # Element zero is excluded because it is auctioneer address.
        for (index, bidder) in enumerate(self.__bidders):
            bidder.address = bidder_addresses[index]
            bidder.auctioneer_pub_key = self.__auctioneer.public_key
            bidder.make_ring(pub_keys)

        logging.debug(f'Bidders created: {self.__bidders}.')

        # --- Starting auction --- #
        logging.info('Starting auction.')
        tx = {
            'from': self.__auctioneer.address,
            'value': Auction.DEPOSIT
        }
        self.__send_transaction(tx,
                                'startAuction')

        # --- Placing bids --- #
        for bidder in self.__bidders:
            logging.info(f'Placing bid for bidder {bidder}.')
            c, sig = bidder.bid()
            tx = {
                'from': bidder.address,
                'value': Auction.DEPOSIT
            }
            self.__send_transaction(tx,
                                    'placeBid',
                                    c, sig)

        # --- Opening bids --- #
        for bidder in self.__bidders:
            logging.info(f'Opening bid for bidder {bidder}.')
            tau_1 = bidder.tau_1
            tx = {
                'from': bidder.address
            }
            self.__send_transaction(tx,
                                    'openBid',
                                    tau_1)

        # --- Getting winning bid --- #
        #logging.info('Getting winning commitment.')
        #self.__auctioneer.get_winning_commitment()

        # --- Opening identity of winning bidder --- #
        #winning_commitment = self.__auctioneer.winning_com
        #for bidder in self.__bidders:
        #    if bidder.c == winning_commitment:
        #        sig, tau_2 = bidder.sig, bidder.get_identity_opening_token()
        #        self.__auctioneer.identity_opening(sig, tau_2)
        #        logging.info(f'Winning bidder is {bidder}.')

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
        self.__number_of_tx += 1

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

    def __call(self,
               func_name: str,
               *args
               ) -> Any:
        """
        Executes a call to the smart contract. Does not consume gas. Does not alter smart contract state.
        :param func_name: Name of the function to be called.
        :param args: Argument to be passed to the function.
        :return: Output of the function.
        """
        logging.info(f'Calling function {func_name}.')
        rtn = self.__contract.functions[func_name](*args).call()
        logging.debug(f'Return value is {rtn}.')
        return rtn
