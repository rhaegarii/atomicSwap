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


#Assumption needed for contract of communication that happened before:
#A and B agree on an exchange amount (A is sending X bitcoin to User B, B is sending Y ethereum to A)
#A created a multisig wallet M in Bitcoin, with pk1, pk2, and sent this to B, along with two transactions:
#     tx1. a refund transaction: from M to A
#     tx2. a send transaction: from M to B
#both of these with amount X
#B verified and signed both transactions on the Bitcoin chain, created the following contract
#B sent both signatures along with the contract address to A
#A funds M with X coins, B verifies this and funds the contract with Y coins, sends swapId to A, A verifies this
#A now has T time to decide what to do, A can either: (T is assumed to be a known, agreed on time)
#     1. wait for T to expire, invalidating the contract, A can then refund herself using B's signed transaction whenever,
#     at this point, B also gets refunded from the contract
#     2. Refund herself, sending the contract tx1 signed by her, same thing happens as #1
#     3. Send the contract her signature on tx2, the contract verifies this and unlocks the contract
#          -> after 2T then, the contract funds are sent to A's account, and B can broadcast his and her signature on tx2 to get his bitcoins


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

                 

                 struct Exchange {

                   uint256 value;
                   uint256 ltcValue;

                   address ethSender;
                   address ethReceiver;

                   address ltcSender;
                   address ltcReceiver;

                   address ltcMultiSigAddr;



                   uint T
                   uint T2
                   string swapTransaction;
                   string refundTransaction;

                   bool unlock;


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
                 //called by B to initiate contract
                 function open(bytes32 _swapID, uint256 _ltcValue, address _ethReceiver, address _ltcMultiSigAddr) public onlyInvalidExchanges(_swapID) payable {
                    //if (exchangeStates[_swapID] == States.Open || exchangeStates[_swapID] == States.Invalid) {
                     //   return; //shouldnt open new id if this is the case right?
                    //}

                    // Store the details of the swap.
                    Exchange memory exchange = Exchange({
                      value: msg.value,
                      ltcValue: _ltcValue,

                      ethSender: msg.sender,
                      ethReceiver: _ethReceiver,

                      unlock: false,
                      T: now + (3600*10),//contract has designated time of 10 hours for initial swap and 10 more for confirmation -> due to bitcoins slow block output
                      T2: now + (3600*20),
                      ltcMultiSigAddr: _ltcMultiSigAddr
                    });
                    exchanges[_swapID] = exchange;
                    exchangeStates[_swapID] = States.OPEN;

                    emit ContractOpen(_swapID, _ethReceiver);
                  }

                  //returns value stored in contract for given swapid, so it can be verified
                  function getExchangeValue(bytes32 sId) public view returns(uint) {
                      return exchanges[sId].value;
                  }



                  //SC1
                  function nullify(bytes32 sId) {
                      if (exchanges[sId].T < now && exchanges[sId].unlock == false) { //FIND OUT HOW TO GET CURRTIME
                          sendEth(thisExchange.ethSender);
                          exchangesStates[sId] = States.Closed;
                      }

                  }


                  //SC2
                  //called by A  or B to refund B
                  //takes in signature for tx1
                  function cancel(bytes32 sId, string tx1sig) public view returns(bool) {
                      thisExchange = exchanges[sId];

                      if verify(thisExchange.refundTransaction, tx1sig, thisExchange.ltcSender) {//we need to verify the transaction signature matches the refund transaction
                         sendEth(thisExchange.ethSender); //we refund B
                         return true;
                      }
                      return false;
                  }


                  //SC3
                  //called by A to enable swap
                  //takes in signature for tx2
                  function swap(bytes32 sId, string tx2sig) public view returns(bool) {
                      thisExchange = exchanges[sId];

                      if verify(thisExchange.refundTransaction, tx2sig, thisExchange.ltcSender) {//we need to verify the transaction signature matches the send transaction
                         //should we also broadcast the transaction ann
                         thisExchange.unlock = true;
                         return true;
                      }
                      return false;
                  }
                 

                  //SC4
                  function fundReceiver(bytes32 sId) {
                      if (exchanges[sId].T2 < now && exchanges[sId].unlock == true) {
                          sendEth(exchanges[sId].ethReceiver);
                      }

                  }






                  //helpers (verify and sendeth)
                  function verify(address p, bytes32 hash, uint8 v, bytes32 r, bytes32 s, string memory message) public view returns(bool)  {

                        bytes32 check = keccak256(abi.encodePacked(message));
                        return ((ecrecover(hash, v, r, s) == p) && (check == hash)) ;
                    }

                  function sendEth(address recipient) {
                  
                  }

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
