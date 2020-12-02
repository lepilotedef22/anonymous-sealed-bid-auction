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

Ethereum has been chosen as the blockchain platform and the auction Smart Contract has been written in Solidity.
The simulation of the main auction protocol is handled by a Python script.

## How to run the code ?
This proof of concept requires two main components: a source code in Python and the Ganache software, 
which allows to locally simulate an Ethereum network. 

The code has been tested on MacOS 11.0.1, with Python 3.8.0.

### Ganache

This is a software that allows to simulate an arbitrary Ethereum network. It can be installed from 
[here](https://www.trufflesuite.com/ganache).

Once it is installed, you can start a session using the *Quick start* button.
