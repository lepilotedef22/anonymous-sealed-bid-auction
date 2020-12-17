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
from typing import Optional, Any, Union, List
from hexbytes import HexBytes
from cryptocompare import get_price
from Crypto.PublicKey import RSA
from csv import writer

from src.auctioneer import Auctioneer
from src.utils.file_helper import get_bidders
from src.utils.crypto import parse
from src.participant import Participant


__author__ = 'Denis Verstraeten'
__date__ = '2020.3.4'


class Auction:
    """
    This class handles everything which is related to the auction.
    """

    # --- Constants --- #
    DEPOSIT = 1000000000000000000  # 1 ETH deposit expressed in Wei.

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
        self.__exchange_ratio = None
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
                                                 abi=self.__abi,
                                                 bytecode=bytecode)
        logging.info('Connected to smart contract.')
        self.__is_deployed = True
        print('Auction smart contract successfully deployed.')
        self.__exchange_ratio = self.__get_gas_price_usd()

    def estimate_gas(self,
                     output_file: Union[str, None],
                     functions: Union[List[str], None]
                     ) -> None:
        """
        This method estimates the gas consumption of the functions of the contract.
        :param output_file: Name of the CSV output file.
        :param functions: List of the name of the functions that need to be stored in the output_file.
        """
        if not self.__is_deployed:
            logging.info('Deploying smart contract.')
            self.deploy()

        if output_file is None:
            output_file = 'gas.csv'

        output = Path.cwd() / output_file
        if output.exists():
            output.unlink()

        rand_gen = {
            'uint256': lambda: randint(0, 2**256 - 1),
            'bytes': lambda: getrandbits(8 * 32).to_bytes(32, byteorder),
            'address': lambda: getrandbits(8 * 20).to_bytes(20, byteorder),
            'bool': lambda: bool(getrandbits(1))
        }
        logging.info('Estimating gas consumption of smart contract functions.')
        print('\t--------------------------------------------')
        print('\t| Gas consumption of individual functions: |')
        print('\t--------------------------------------------')
        csv_rows = [['Function', 'Gas', 'USD']]
        # --- Contract deployment --- #
        constructor_abi_dic = self.__abi[0]
        abi_inputs = constructor_abi_dic['inputs']
        input_types = list(map(lambda arg: arg['type'], abi_inputs))
        inputs = list(map(lambda arg_type: rand_gen[arg_type](), input_types))
        logging.info(f'Inputs: '
                     f'{", ".join([f"{input_types[i]}={inputs[i]}" for i in range(len(inputs))])}')
        gas = self.__contract.constructor(*inputs).estimateGas()
        if self.__exchange_ratio is None:
            print(f'Deployment: {gas} gas.')
            csv_rows.append(['Deployment', gas, ''])

        else:
            print(f'Deployment: {gas} gas = {gas * self.__exchange_ratio:.2f} USD.')
            csv_rows.append(['Deployment', gas, round(gas * self.__exchange_ratio, 2)])

        # --- Individual functions --- #
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

                            if self.__exchange_ratio is None:
                                print(f'{func_name}({", ".join(input_types)}): {gas} gas.')
                                if functions is None or func_name in functions:
                                    csv_rows.append([func_name, gas, ''])

                            else:
                                print(f'{func_name}({", ".join(input_types)}): {gas} gas = '
                                      f'{gas * self.__exchange_ratio:.2f} USD.')
                                if functions is None or func_name in functions:
                                    csv_rows.append([func_name, gas, round(gas * self.__exchange_ratio, 2)])

                        except ValueError as e:
                            logging.info(f'Passed inputs are not accepted by the function. Error: {e}.')

                        break

                except KeyError:
                    pass

        logging.info('Gas consumption estimated.')
        with output.open(mode='w') as csv_file:
            csv_writer = writer(csv_file, delimiter=',')
            csv_writer.writerows(csv_rows)
            logging.info('Data stored in csv file.')

    def proof_of_concept(self,
                         show_total_price: bool
                         ) -> None:
        """
        This method implements the proof of concept.
        :param show_total_price: Flag indicating total price of auction for each participant should be displayed.
        """
        # --- Deploying Smart Contract --- #
        if not self.__is_deployed:
            logging.info('Deploying smart contract.')
            self.deploy()

        # --- Getting bidders indices --- #
        bidders_dic = None
        for entry in self.__abi:
            try:
                if entry['name'] == 'bidders':
                    bidders_dic = entry
                    break

            except KeyError:
                pass

        outputs = bidders_dic['outputs']
        indices = {}
        for index, output in enumerate(outputs):
            indices[output['name']] = index

        c_index = indices['c']
        csig_index = indices['csig']
        cring_index = indices['cring']
        ctau_1_index = indices['ctau_1']
        ctau_2_index = indices['ctau_2']

        # --- Setting up filters --- #
        new_bidder_filter = self.__contract.events.newBidder.createFilter(fromBlock='latest')

        print('Simulating anonymous sealed-bid auction protocol...')
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
                                self.__auctioneer,
                                'startAuction')

        # --- Placing bids --- #
        for bidder in self.__bidders:
            logging.info(f'Placing bid for bidder {bidder}.')
            bidder.bid()
            tx = {
                'from': bidder.address,
                'value': Auction.DEPOSIT
            }
            self.__send_transaction(tx,
                                    bidder,
                                    'placeBid',
                                    bidder.c, bidder.csig[0], bidder.cring[0], bidder.ctau_1[0], bidder.ctau_2[0])

        for event in new_bidder_filter.get_new_entries():
            new_bidder_address = event['args']['newBidderAddress']
            event_name = event['event']
            logging.info(f'Catching event {event_name} from bidder at {new_bidder_address}.')
            self.__auctioneer.bidders[new_bidder_address] = None

        for bidder in self.__bidders:
            address = bidder.address
            sig = bidder.sig
            dsig = bidder.csig[1]
            tau_1 = bidder.tau_1
            dtau_1 = bidder.ctau_1[1]
            ring = bidder.ring
            dring = bidder.cring[1]
            bidder_blockchain = self.__call('bidders', address)
            c = bidder_blockchain[c_index]
            csig = bidder_blockchain[csig_index]
            cring = bidder_blockchain[cring_index]
            ctau_1 = bidder_blockchain[ctau_1_index]
            logging.info(f'Opening bid for bidder at {address}.')
            if self.__auctioneer.bid_opening(bidder_address, ring, c, sig, tau_1):
                logging.info(f'Bid opening successful for bidder at {bidder_address}.')

            else:
                logging.info(f'Bid opening failed, punishing bidder at {bidder_address}.')
                self.__auctioneer.bidders.pop(bidder_address, None)
                tx = {
                    'from': self.__auctioneer.address
                }
                self.__send_transaction(tx,
                                        self.__auctioneer,
                                        'punishBidder',
                                        bidder_address)

        # --- Getting winning bid --- #
        logging.info('Getting winning commitment.')
        self.__auctioneer.get_winning_commitment()

        # --- Opening identity of winning bidder --- #
        winning_commitment = self.__auctioneer.winning_com
        tx = {
            'from': self.__auctioneer.address
        }
        logging.info('Publishing winning commitment.')
        self.__send_transaction(tx,
                                self.__auctioneer,
                                'announceWinningCommitment',
                                winning_commitment)

        for bidder in self.__bidders:
            winning_commitment = self.__call('winningCommitment')
            if bidder.c == winning_commitment:
                logging.info(f'Bidder {bidder} is winning bidder.')
                tx = {
                    'from': bidder.address
                }
                self.__send_transaction(tx,
                                        bidder,
                                        'openIdentity',
                                        bidder.tau_2)
                break

        logging.info('Getting sig and tau_2 for winning bidder.')
        winning_bidder = self.__call('bidders', self.__auctioneer.winning_address)
        sig = winning_bidder[sig_index]
        tau_2 = winning_bidder[tau_2_index]

        if self.__auctioneer.identity_opening(sig, tau_2):
            print('Identity of winning bidder successfully verified.')
            print(f"Winning bidder's address: {self.__auctioneer.winning_address}.")
            print(f"Winning bidder's public key: {self.__auctioneer.winning_bidder}.")
            print(f'Winning bid: {self.__auctioneer.bidders[self.__auctioneer.winning_address]["bid"]}.')

        else:
            logging.info(f'Identity opening failed. Punishing bidder at {self.__auctioneer.winning_address}.')
            self.__auctioneer.bidders.pop(self.__auctioneer.winning_address, None)
            tx = {
                'from': self.__auctioneer.address
            }
            self.__send_transaction(tx,
                                    self.__auctioneer,
                                    'punishBidder',
                                    self.__auctioneer.winning_address)

        # --- Withdrawing deposit --- #
        print('Withdrawing deposits...')
        for bidder in self.__bidders:
            logging.info(f'Withdrawing deposit for bidder at {bidder.address}.')
            tx = {
                'from': bidder.address
            }
            self.__send_transaction(tx,
                                    bidder,
                                    'withdrawDeposit')

        logging.info('Withdrawing deposit for auctioneer.')
        tx = {
            'from': self.__auctioneer.address
        }
        self.__send_transaction(tx,
                                self.__auctioneer,
                                'withdrawDeposit')
        print('Deposits withdrawn.')
        if show_total_price:
            print('------------')
            print('| Gas cost|')
            print('------------')

            if self.__exchange_ratio is None:
                print(f'Total cost auctioneer: {self.__auctioneer.gas} gas.')
                for bidder in self.__bidders:
                    print(f'Total cost for bidder {bidder.name}: {bidder.gas} gas.')

            else:
                print(f'Total cost auctioneer: {self.__auctioneer.gas} gas '
                      f'= {self.__auctioneer.gas * self.__exchange_ratio:.2f} USD.')
                for bidder in self.__bidders:
                    print(f'Total cost for bidder {bidder.name}: {bidder.gas} gas ='
                          f' {bidder.gas * self.__exchange_ratio:.2f} USD.')

    def __send_transaction(self,
                           transaction,
                           participant: Participant,
                           func_name: Optional[str] = None,
                           *args
                           ) -> None:
        """
        Executes a transaction. Can be the execution of a smart contract function.
        :param transaction: Transaction data.
        :param participant: Optional participant whose gas consumption should be updated.
        :param func_name: Optional name of the smart contract function to be executed.
        :param args: Argument to be passed to the function.
        """
        if func_name is not None:
            logging.info(f'Executing function {func_name}.')
            tx_hash = self.__contract.functions[func_name](*args).transact(transaction)

        else:
            logging.info('Executing transaction.')
            tx_hash = self.__w3.eth.sendTransaction(transaction)

        logging.info(f'Transaction hash: {tx_hash.hex()}.')
        self.__gas_cost(tx_hash,
                        participant)
        self.__number_of_tx += 1

    def __gas_cost(self,
                   tx_hash: HexBytes,
                   participant: Participant
                   ) -> None:
        """
        Adds the gas cost of the transaction to self.__total_gas_cost.
        :param tx_hash: Hash of the transaction whose gas cost should be added.
        :param participant: Optional participant whose gas consumption should be updated.
        """
        tx_receipt = self.__w3.eth.waitForTransactionReceipt(tx_hash)
        gas_used = tx_receipt.gasUsed
        if self.__exchange_ratio is None:
            logging.info(f'Gas used for transaction {tx_hash.hex()}: {gas_used} gas.')

        else:
            logging.info(f'Gas used for transaction {tx_hash.hex()}: {gas_used} gas = '
                         f'{gas_used * self.__exchange_ratio:.2f} USD.')

        self.__total_gas_cost += gas_used
        participant.gas += gas_used
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

    def __get_gas_price_usd(self) -> Union[float, None]:
        """
        :return: Exchange rate from gas to USD.
        """
        eth_to_usd_fetch = get_price('ETH', curr='USD')
        if eth_to_usd_fetch is None:
            return None

        eth_to_usd = eth_to_usd_fetch['ETH']['USD']
        gas_to_wei = self.__w3.eth.gasPrice
        wei_to_eth = 1e-18
        exchange_ratio = gas_to_wei * wei_to_eth * eth_to_usd
        logging.info(f'Exchange ratio from gas to USD is {exchange_ratio:.2f} USD/gas.')
        return exchange_ratio
