# Anonymous Sealed-Bid Auction
This repository includes a Proof of Concept of the protocol presented in the paper 
*Anonymous Fair Trading on Blockchain*.

## Introduction
This new protocol allows to hold an auction, while maintaining the anonymity of the bidders, 
as well as the confidentiality of the bids. It takes advantage of the auditability feature inherent to 
blockchain technologies.

It relies on the assumption of the existence of an underlying privacy preserving blockchain platform. 
The design of the protocol follows a generic approach and extensively uses well-known cryptographic primitives such as
*commitment scheme*, *public key encryption* and *ring signature*. The anonymity of the bidders is achieved using a 
*Designated Identity Verifier Ring Signature* technique introduced by Saraswat and 
Pandey and which can be found [here](https://link.springer.com/chapter/10.1007%2F978-3-319-16295-9_19). 
For more information about the protocol, a link to the paper will be available soon. Stay tuned !

Ethereum has been chosen as the blockchain platform, and the auction Smart Contract has been written in Solidity.
The simulation of the main auction protocol is handled by a Python script.

## Installation

The proof of concept requires three main parts to run properly.
* [Ganache](#Ganache)
* [Solc](#Solc)
* [Python](#Python)

The code has been tested on MacOS 11.0.1, with Python 3.8.0, Solc 0.7.4 and Ganache 2.5.4.

### Ganache

This is a software that allows to simulate an arbitrary Ethereum network. It can be installed from 
[here](https://www.trufflesuite.com/ganache).

### Solc

Solc is a compiler that allows to turn Solidity Smart Contracts into bytecode suitable to be uploaded to an Ethereum
network. It can be installed from [here](https://www.npmjs.com/package/solc). 
More information about it can be found in the 
[official documentation](https://docs.soliditylang.org/en/v0.7.5/installing-solidity.html).


### Python

The installation instructions for Python can be found [here](https://www.python.org/).

The required Python packages can be installed using [pip](https://pypi.org/) using the following command:


```
pip install -r requirements.txt
```

## Run the code

### Create a local Ethereum network
Start Ganache and click on *Quickstart*. If you want to run the simulation with more bidders, 
increase the number of peers of the network in such way that `N_peers >= N_bidders + 1`.

### Launch Python script
Make sure that Ganache is running before launching the Python script.

The main Python script is main.py:

```
python main.py [-h --help] 
               [-l --log {debug, info, warning, error, critical}]
               [-m --mode {deploy, gas, poc}]
               [-o --output OUTPUT]
               [-f --functions FUNCTIONS...]
               [-p --price]
```

1. `help`: Displays help and exits.
1. `log`: Sets up logging level. Regular usage should not required to use this option.   
1. `mode`:
    1. `deploy`: Compiles and deploys the auction.sol Smart Contract to the blockchain.
    1. `gas`: **Estimates** the gas consumption of all the functions of the Smart contract.
        1. `output`: Name of the output csv file to which the gas estimates have to be stored.
        1. `functions`: Names of the functions that have to be stored in file `OUTPUT`. 
           They have to be written in the following way: `function1, function2, ..., functionN`.
    1. `poc`: Runs the proof of concept simulation of an auction. The bids are set up in the bidders.json file.
    This file is automatically created with random bid values if nonexistent.
        1. `price`: Flag indicating whether the total overhead cost of the auction for each participant 
           has to be displayed at the end of the simulation.