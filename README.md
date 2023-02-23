# mintr_bulk_companion
Repo for scripts that enable bulk minting from mintr without a full node (looped minting)

```
1. run the pertinent install script (install.sh for mac and linux, install.ps1 for windows)
2. run the command provided by Mintr
```

Mint NFTs using Mintr Bulk Mint Companion

options:
  -h, --help            show this help message and exit
  -nn STRING, --network_name STRING
                        Name of the blockchain network (mainnet or testnet10) (default: testnet10)
  -i INTEGER, --wallet_id INTEGER
                        ID of the wallet to use (default: None)
  -ra STRING, --royalty_address STRING
                        Address to send royalty payments (default: None)
  -rp FLOAT, --royalty_percentage FLOAT
                        NFT royalty percentage fraction in basis points. Example: 175 would represent 1.75% (default: 0)
  -m FLOAT, --fee FLOAT
                        Transaction fee in network currency (default: None)
  -mf STRING, --metadata_file STRING
                        Path to metadata file (default: bulk_mint_metadata.csv)
  -t BOOLEAN, --nft_targets BOOLEAN
                        Whether to mint NFTs to targets (default: False)

