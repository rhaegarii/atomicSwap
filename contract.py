#code from: https://web3py.readthedocs.io/en/stable/contracts.html#contracts

#Step1: A creates her public and secret keys for each coin, sends public
#Step2: B accepts proposal, does the same thing
#Step3: A creates multisig wallet with each public key being in control and sends address to B
#Step4: A creates tx1 = Refund(A, pkAa) tx2 = Swap(A, pkAb)
#Step5: B verifies and finds (sig1, tx1) where sig1 = Sign(skAb(tx1)) and sends that plus makes the contract
#Step6: A verifies and sends funds to M
#Step7: B signs the multisig transaction giving him control of the funds in M
#Step8: A signs the transaction giving B control of the funds in M, must verify to correct signature
#Step9: B extracts funds from M (before or after time = T)
#Step10: A uses

import json

from web3 import Web3

from solc import compile_standard

# Solidity source code
compiled_sol = compile_standard({
     "language": "Solidity",
     "sources": {
         "swapEthToLtc.sol": {
             "content": '''
                 pragma solidity ^0.6.6;

                 contract swapEthToLtc{

                 string public greeting;

                 address ltcSender;
                 address ltcReceiver;

                 struct Exchange {

                   uint256 value;
                   uint256 ltcValue;

                   address ethSender;
                   address ethReceiver;



                   address ltcMultiSigAddr;



                   }

                   enum States {
                        INVALID,
                        OPEN,
                        CLOSED,
                        EXPIRED
                    }

                 mapping (bytes32 => Exchange) private exchanges;
                 mapping (bytes32 => States) private exchangeStates;

                 event ContractOpen(bytes32 _swapID, address _otherTrader);
                 event BSignSent(bytes32 _swapID);
                 event ContractExpire(bytes32 _swapID);
                 event ContractClose(bytes32 _swapID);

                 constructor() public {
                       greeting = 'Hello';

                   }

                 modifier onlyInvalidExchanges(bytes32 _swapID) {
                    require (exchangeStates[_swapID] == States.INVALID);
                    _;
                 }

                 modifier onlyOpenExchanges(bytes32 _swapID) {
                    require (exchangeStates[_swapID] == States.OPEN);
                    _;
                 }

                 function open(bytes32 _swapID, uint256 _ltcValue, address _ethReceiver, address _ltcMultiSigAddr) public onlyInvalidExchanges(_swapID) payable {
                    // Store the details of the swap.
                    Exchange memory exchange = Exchange({
                      value: msg.value,
                      ltcValue: _ltcValue,

                      ethSender: msg.sender,
                      ethReceiver: _ethReceiver,



                      ltcMultiSigAddr: _ltcMultiSigAddr
                    });
                    exchanges[_swapID] = exchange;
                    exchangeStates[_swapID] = States.OPEN;

                    emit ContractOpen(_swapID, _ethReceiver);
                  }


                  function verify(address p, bytes32 hash, uint8 v, bytes32 r, bytes32 s, string memory message) public view returns(bool)  {

                        bytes32 check = keccak256(abi.encodePacked(message));
                        return ((ecrecover(hash, v, r, s) == p) && (check == hash)) ;
                    }

                  function refundEth(address ethSender)

                 }
               '''
         }
     },
     "settings":
         {
             "outputSelection": {
                 "*": {
                     "*": [
                         "metadata", "evm.bytecode"
                         , "evm.bytecode.sourceMap"
                     ]
                 }
             }
         }
 })

# web3.py instance
w3 = Web3(Web3.EthereumTesterProvider())

# set pre-funded account as sender
w3.eth.defaultAccount = w3.eth.accounts[0]

# get bytecode
bytecode = compiled_sol['contracts']['swapEthToLtc.sol']['swapEthToLtc']['evm']['bytecode']['object']

# get abi
abi = json.loads(compiled_sol['contracts']['swapEthToLtc.sol']['swapEthToLtc']['metadata'])['output']['abi']

XChainSwap = w3.eth.contract(abi=abi, bytecode=bytecode)

# Submit the transaction that deploys the contract
tx_hash = XChainSwap.constructor().transact()

# Wait for the transaction to be mined, and get the transaction receipt
tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
print(tx_receipt)
#finds transaction on blockchain
swapper = w3.eth.contract(
     address=tx_receipt.contractAddress,
     abi=abi
 )
print(swapper)

#swapper.functions.greet().call()
#output: 'Hello'

#tx_hash = swapper.functions.setGreeting('Nihao').transact()
#tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
#swapper.functions.greet().call()
#output: 'Nihao'
