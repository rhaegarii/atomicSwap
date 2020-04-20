from bitcoinlib.wallets import HDWallet, wallets_list, wallet_create_or_open
hdW = wallet_create_or_open('LitecoinMS-onReal')
print(hdW.as_dict())
