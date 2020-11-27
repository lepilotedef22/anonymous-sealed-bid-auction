// SPDX-License-Identifier: GPL-3.0
// Author: Denis Verstraeten
pragma solidity ^0.7.0;

contract Auction {
    /* Struct */
    struct Bidder {
        bytes c;
        bytes sig;
        bytes ring;
        bytes tau_1;
        bytes tau_2;
    }

    /* State variables */
    uint public T0;
    uint public T1;
    uint public T2;
    uint public T3;
    bool public test;
    address public auctioneer;
    mapping (address => Bidder) public bidders;
    address[] public bidderAddresses;
    mapping(address => uint) public deposit;
    uint public depositValue;
    uint public totalDeposit = 0;
    bytes public winningCommitment;

    /* Modifiers */
    modifier enoughDeposit {
        require(msg.value >= depositValue, 'Deposit value is not enough.');
        _;
    }

    modifier canStartAuction {
        require(totalDeposit == 0, 'Cannot start new auction, deposits are not empty.');
        _;
    }

    modifier beforeT1 {
        require(block.number <= T0 + T1 || test, 'After T1 already.');
        _;
    }

    modifier beforeT2 {
        require(block.number <= T0 + T1 + T2 || test, 'After T2 already.');
        _;
    }

    modifier beforeT3 {
        require(block.number <= T0 + T1 + T2 + T3 || test, 'After T3 already.');
        _;
    }

    modifier afterT3 {
        require(block.number > T0 + T1 + T2 + T3 || test, 'Not after T3 yet.');
        _;
    }
    /* Events */
    event newBidder(address newBidderAddress);

    /* Constructor */
    constructor(uint _T1, uint _T2, uint _T3, bool _test, uint deposit){
        T1 = _T1;
        T2 = _T2;
        T3 = _T3;
        test = _test;
        depositValue = deposit;
    }

    /* Functions */
    function startAuction() public payable enoughDeposit canStartAuction {
        T0 = block.number;
        auctioneer = msg.sender;
        deposit[msg.sender] = msg.value;
        totalDeposit += msg.value;
    }

    function placeBid(bytes memory _c, bytes memory _sig, bytes memory _ring) public payable enoughDeposit beforeT1 {
        deposit[msg.sender] = msg.value;
        totalDeposit += msg.value;
        bidders[msg.sender].c = _c;
        bidders[msg.sender].sig = _sig;
        bidders[msg.sender].ring = _ring;
        emit newBidder(msg.sender);
    }

    function openBid(bytes memory _tau_1) public beforeT2 {
        bidders[msg.sender].tau_1 = _tau_1;
    }

    function announceWinningCommitment(bytes memory _winningCommitment) public beforeT2 {
        winningCommitment = _winningCommitment;
    }

    function openIdentity(bytes memory _tau_2) public beforeT3 {
        bidders[msg.sender].tau_2 = _tau_2;
    }

    function withdrawDeposit() public afterT3 {
        msg.sender.transfer(deposit[msg.sender]);
        totalDeposit -= deposit[msg.sender];
        deposit[msg.sender] = 0;
    }

    function punishBidder(address bidderAddress) public {
        deposit[bidderAddress] = 0;
        totalDeposit -= deposit[bidderAddress];
    }

    function getC(address bidderAddress) public beforeT2 returns (bytes memory) {
        return bidders[bidderAddress].c;
    }

    function getSig(address bidderAddress) public beforeT2 returns (bytes memory) {
        return bidders[bidderAddress].sig;
    }

    function getTau1(address bidderAddress) public beforeT2 returns (bytes memory) {
        return bidders[bidderAddress].tau_1;
    }

    function getRing(address bidderAddress) public beforeT2 returns (bytes memory) {
        return bidders[bidderAddress].ring;
    }
}