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
from bitcoinlib.keys import HDKey
from bitcoinlib.wallets import HDWallet, wallet_create_or_open


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

                   address payable ethSender;
                   address payable ethReceiver;

                   string ltcSender;
                   //address ltcReceiver;

                   string ltcMultiSigAddr;



                   uint T;
                   uint T2;
                   bytes32 swapTHash;
                   bytes32 refundTHash;

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
                 function open(bytes32 _swapID, uint256 _ltcValue, address payable _ethReceiver, string memory _ltcMultiSigAddr, string memory oSender, bytes32 sHash, bytes32 rHash) public onlyInvalidExchanges(_swapID) payable {
                    //if (exchangeStates[_swapID] == States.Open || exchangeStates[_swapID] == States.Invalid) {
                     //   return; //shouldnt open new id if this is the case
                    //}

                    // Store the details of the swap.
                    Exchange memory exchange = Exchange({
                      value: msg.value,
                      ltcValue: _ltcValue,

                      ethSender: msg.sender,
                      ethReceiver: _ethReceiver,

                      unlock: false,
                      T: now + (600),//contract has designated time of 10 hours for initial swap and 10 more for confirmation -> due to bitcoins slow block output
                      T2: now + (2*600),
                      ltcMultiSigAddr: _ltcMultiSigAddr,
                      swapTHash: sHash,
                      refundTHash: rHash,
                      ltcSender: oSender
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
                  function nullify(bytes32 sId) public  {
                      if (exchanges[sId].T < now && exchanges[sId].unlock == false) {
                          sendEth(sId, exchanges[sId].ethSender);
                      }
                  }


                  //SC2
                  //called by A  or B to refund B
                  //takes in signature for tx1
                 function cancel(bytes32 sId, address p, bytes32 hash, uint8 v, bytes32 r, bytes32 s, string memory message) public payable returns(bool) {
                      Exchange memory thisExchange = exchanges[sId];

                      if (hash == thisExchange.refundTHash && verify(p, hash, v, r, s, message)) {//we need to verify the transaction signature matches the refund transaction
                         sendEth(sId, thisExchange.ethSender); //we refund B
                         return true;
                      }
                      return false;
                  }


                  //SC3
                  //called by A to enable swap
                  //takes in signature for tx2
                  function swap(bytes32 sId, address p, bytes32 hash, uint8 v, bytes32 r, bytes32 s, string memory message) public view returns(bool) {
                      Exchange memory thisExchange = exchanges[sId];

                      if (hash == thisExchange.swapTHash && verify(p, hash, v, r, s, message)) {//we need to verify the transaction signature matches the send transaction
                         //should we also broadcast the transaction ann
                         thisExchange.unlock = true;
                         return true;
                      }
                      return false;
                  }


                  //SC4
                  function fundReceiver(bytes32 sId) public {
                      if (exchanges[sId].T2 < now && exchanges[sId].unlock == true) {
                          sendEth(sId, exchanges[sId].ethReceiver);
                      }
                  }






                  //helpers (verify and sendeth)
                  function verify(address p, bytes32 hash, uint8 v, bytes32 r, bytes32 s, string memory message) public view returns(bool)  {

                        bytes32 check = sha256(abi.encodePacked(p));
                        return ((ecrecover(hash, v, r, s) == p) && (check == hash)) ;
                    }

                  function sendEth(bytes32 sId, address payable recipient) public {
                      recipient.transfer(exchanges[sId].value);
                      exchangeStates[sId] = States.CLOSED;
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

#Code used to initialize wallets, which are now used in each running of the script
NETWORK = 'testnet'
#k1 = HDKey('tprv8ZgxMBicQKsPd1Q44tfDiZC98iYouKRC2CzjT3HGt1yYw2zuX2awTotzGAZQEAU9bi2M5MCj8iedP9MREPjUgpDEBwBgGi2C8eK'
#           '5zNYeiX8', network=NETWORK)
#k2 = HDKey('tprv8ZgxMBicQKsPeUbMS6kswJc11zgVEXUnUZuGo3bF6bBrAg1ieFfUdPc9UHqbD5HcXizThrcKike1c4z6xHrz6MWGwy8L6YKVbgJ'
#           'MeQHdWDp', network=NETWORK)


#w1 = HDWallet.create('multisig_2of2_cosigner1', sigs_required=2, keys=[k1, k2.public_master(multisig=True)], network=NETWORK)
#w2 = HDWallet.create('multisig_2of2_cosigner2',  sigs_required=2, keys=[k1.public_master(multisig=True), k2], network=NETWORK)

#open multisig wallet M
w1 = wallet_create_or_open('multisig_2of2_cosigner1')
w2 = wallet_create_or_open('multisig_2of2_cosigner2')
wal3 = wallet_create_or_open('rcvr', network=NETWORK)
wal4 = wallet_create_or_open('sndr', network=NETWORK)
print((wal3.addresslist()))
#print(w2.address)

#initialize trasaction on wallet 1
w1.utxos_update()
tswap = w1.send_to(wal3.addresslist()[0], 2, network=NETWORK)
treturn = w1.send_to(wal4.addresslist()[0], 2, network=NETWORK)

tswap.info()
treturn.info()

#sign and sent transaction on wallet 2
w2.get_key()
t2 = w2.transaction_import(tswap)
#t2.sign()
#print(t2.sign())
#t2.send()
t2.info()

print(dir(t2))

# web3.py instance
w3 = Web3(Web3.EthereumTesterProvider())

# set pre-funded account as sender
w3.eth.defaultAccount = w3.eth.accounts[0]
ethReceiver = w3.eth.account.create();


# get bytecode
bytecode = compiled_sol['contracts']['swapEthToLtc.sol']['swapEthToLtc']['evm']['bytecode']['object']

# get abi
abi = json.loads(compiled_sol['contracts']['swapEthToLtc.sol']['swapEthToLtc']['metadata'])['output']['abi']

XChainSwap = w3.eth.contract(abi=abi, bytecode=bytecode)





# Submit the transaction that deploys the contract
tx_hash = XChainSwap.constructor().transact()
print(t2)
XChainSwap.functions.open((0).to_bytes(32, 'big'), 10, (ethReceiver.address), "0x"+(wal3.addresslist()[0]), "0x"+(w1.addresslist()[0]), (tswap.hash).encode('utf-8'), (treturn.hash).encode('utf-8')).send()

# Wait for the transaction to be mined, and get the transaction receipt
tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
#print(tx_receipt)
#finds transaction on blockchain
swapper = w3.eth.contract(
     address=tx_receipt.contractAddress,
     abi=abi
 )

 #Event 1: Owner of chain currency signs swap transaction and sends to other party
tswapinit = w2.send_to(wal3.addresslist()[0], 2, network=NETWORK)

#multisig party creates signature for transaction but doesn't sign it yet
w1.get_key()
tswap = w1.transaction_import(tswapinit)
#t2.sign()
#print(t2.sign())
#t2.send()


 #Event 2: Owner of multisig chain sends signature to the smart contracts as well as other party. Signature is verified by the contract, setting status to "unlock"
XChainSwap.functions.swap((0).to_bytes(32, 'big'), tswap.rawtx, tswap.hash, tswap.signature_segwit,  tswap.signature()[0:round(len(tswap.signature())/2)], tswap.signature()[round(len(tswap.signature())/2):], tswap.rawtx).send()


#Event 3: Owner of contract chain uses the recently acquired signature to sign the transaction and retrieve the multisig funds
tswap.sign()
tswap.send()
tswap.info()
#They now have control of the currency they chose to swap for

#Owner of multisg chain now queries the SC and retrieves their currency, completing the swap
XChainSwap.functions.fundReceiver(0).send()

#print(swapper)

#swapper.functions.greet().call()
#output: 'Hello'

#tx_hash = swapper.functions.setGreeting('Nihao').transact()
#tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
#swapper.functions.greet().call()
#output: 'Nihao'
