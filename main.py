from time import sleep
from typing import Any, Dict, List, Optional
import csv
import requests
import urllib3
import argparse
import logging
from os import path

urllib3.disable_warnings()

# Set up logging
logger = logging.getLogger()
logging.basicConfig(filename='mintr_bulk_companion.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Create argument parser
parser = argparse.ArgumentParser(description='Mint NFTs using Mintr Bulk Mint Companion')

# Define arguments
parser.add_argument('-nn', '--network_name', dest='network_name', type=str, default='testnet10', metavar='STRING',
                    help='Name of the blockchain network (mainnet or testnet10) (default: %(default)s)')
parser.add_argument('-i', '--wallet_id', dest='wallet_id', type=int, required=True, metavar='INTEGER', help='ID of the wallet to use (default: %(default)s)')
parser.add_argument('-ra', '--royalty_address', dest='royalty_address', type=str, required=True, metavar='STRING', help='Address to send royalty payments (default: %(default)s)')
parser.add_argument('-rp', '--royalty_percentage', dest='royalty_percentage', type=float, default=0, metavar='FLOAT', help='NFT royalty percentage fraction in basis points. Example: 175 would represent 1.75%% (default: %(default)s)')
parser.add_argument('-m', '--fee', dest='fee', type=float, required=True, metavar='FLOAT', help='Transaction fee in network currency (default: %(default)s)')
parser.add_argument('-mf', '--metadata_file', dest='metadata_file', type=str, default='bulk_mint_metadata.csv', metavar='STRING', help='Path to metadata file (default: %(default)s)')
parser.add_argument('-t', '--nft_targets', dest='nft_targets', type=bool, default=False, metavar='BOOLEAN', help='Whether to mint NFTs to targets (default: %(default)s)')


# Parse arguments
args = parser.parse_args()


logger.info(f"\n\n#### STARTING Mintr Bulk Mint Companion\n")
print(f"\n\n#### STARTING Mintr Bulk Mint Companion\n")


# Validate types
try:
    assert isinstance(args.network_name, str)
    assert isinstance(args.wallet_id, int)
    assert isinstance(args.royalty_address, str)
    assert isinstance(args.royalty_percentage, float)
    assert isinstance(args.fee, float)
    assert isinstance(args.metadata_file, str)
    assert isinstance(args.nft_targets, bool)
except AssertionError as ae:
    error_msg = f"Invalid argument types: {ae}"
    print(f"Invalid argument types: {ae}")
    logging.error(error_msg)
    raise TypeError(error_msg)

# Validate file paths
if not path.exists(args.metadata_file):
    error_msg = f"Metadata file {args.metadata_file} not found."
    print(f"Metadata file {args.metadata_file} not found.")
    logging.error(error_msg)
    raise ValueError(error_msg)


xch_fee = args.fee / 1000000000000
net_prefix = 'xch' if args.network_name == 'mainnet' else 'txch'


# Use arguments in rest of the script
logger.info(f"Minting NFTs on {args.network_name} with wallet ID {args.wallet_id}")
print(f"Minting NFTs on {args.network_name} with wallet ID {args.wallet_id}")
logger.info(f"Royalties will be sent to {args.royalty_address} at a rate of {args.royalty_percentage}%")
print(f"Royalties will be sent to {args.royalty_address} at a rate of {args.royalty_percentage}%")
logger.info(f"The transaction fee will be {args.fee} mojo ({xch_fee} {net_prefix})  on {args.network_name}")
print(f"The transaction fee will be {args.fee} mojo ({xch_fee} {net_prefix}) on {args.network_name}")
logger.info(f"Using metadata file located at {args.metadata_file}")
print(f"Using metadata file located at {args.metadata_file}")
if args.nft_targets:
    logger.info("Minting NFTs as targets")
    print("Minting NFTs as targets")

########################################## Define Defaults ##########################################
NETWORK_NAME = args.network_name  # to-do add validation of selected network

nft_data = {"wallet_id": args.wallet_id,
            # 3 is default as this should be the NFT wallet if no additional wallets have been created
            "royalty_address": args.royalty_address,
            "royalty_percentage": args.royalty_percentage,
            "fee": args.fee}  # min recommended minting fee is default

metadata_file = args.metadata_file

nft_targets = args.nft_targets

########################################## System Defaults ##########################################
wallet_RPC_port = 'localhost:9256'
homeDir = path.expanduser('~')
cert = (homeDir + '/.chia/mainnet/config/ssl/wallet/private_wallet.crt',
        homeDir + '/.chia/mainnet/config/ssl/wallet/private_wallet.key')

logger.info(f"RPC port is set to {wallet_RPC_port}")
#print(f"RPC port is set to {wallet_RPC_port}")
logger.info(f"Home directory is {homeDir}")
#print(f"Home directory is {homeDir}")


def query_wallet(url_option, json_data: {}):
    try:
        response = requests.post(url='https://{}/{}'.format(wallet_RPC_port, url_option),
                                 verify=False,
                                 cert=cert,
                                 headers={'content-type': 'application/json'},
                                 json=json_data,
                                 timeout=10
                                 )
        response.raise_for_status()  # Raise an exception for 4xx and 5xx errors
        return response.json()
    except requests.exceptions.Timeout as e:
        print("Request timed out: ", e)
    except requests.exceptions.RequestException as e:
        print("Error occurred while making request: ", e)
    except Exception as e:
        print("Unexpected error occurred: ", e)
    return None


def get_network():
    url_option = "get_network_info"
    response = query_wallet(url_option=url_option, json_data={})
    if response is not None:
        network_name = response['network_name']
        logger.info(f"Wallet is connected to {network_name}")
        print(f"Wallet is connected to {network_name}")
    else:
        logger.info("The wallet RPC cannot be reached to verify network information, make sure Chia is running")
        print("The wallet RPC cannot be reached to verify network information, make sure Chia is running")
        network_name = 'unknown'
    return network_name


def get_sync():
    url_option = "get_sync_status"
    response = query_wallet(url_option=url_option, json_data={})
    if response is None:
        logger.info("The wallet RPC cannot be reached to verify network information, make sure Chia is running")
        print("The wallet RPC cannot be reached to verify network information, make sure Chia is running")
        return 'Not Synced'
    elif not response['synced']:
        logger.info(f"The wallet is currently {response['syncing']}")
        print(f"The wallet is currently {response['syncing']}")
        return 'Syncing' if response['syncing'] is True else 'Not Synced'
    else:
        logger.info(f"The wallet is currently Synced")
        print(f"The wallet is currently Synced")
        return 'Synced'


def nft_mint_nft(data):
    url_option = "nft_mint_nft"
    json_data = data
    logger.info(f"NFT is minting with data: {json_data}")
    print(f"NFT is minting with data: {json_data}")
    response = query_wallet(url_option=url_option, json_data=json_data)
    return response


def get_transactions():
    url_option = "get_transactions"
    logger.info("Verifying NFT transaction")
    print("Verifying NFT transaction")
    json_data = {"wallet_id": 1, "start": 0, "stop": 1, "reverse": False}
    response = query_wallet(url_option=url_option, json_data=json_data)

    return response['transactions'][0]['confirmed'] if response['success'] == True else 'Error identifying minting ' \
                                                                                        'transaction '


def mint_monitor(i):
    status = get_transactions()
    if status == 'Error identifying minting transaction':
        logger.info(f'Your transaction for NFT {i} cannot be identified! \nPlease monitor the chia client')
        print(f'Your transaction for NFT {i} cannot be identified! \nPlease monitor the chia client')
    elif status == True:
        logger.info(f'\nMinting has SUCCEEDED for NFT #{i}\n\n')
        print(f'\nMinting has SUCCEEDED for NFT #{i}\n\n')
    else:
        print('', end='\r')
    return status


# The read_metadata script has been adapted from the Chia network script with the same name from
# https://github.com/Chia-Network/chia-nft-minting-tool/blob/main/chianft/util/mint.py#L449
def read_metadata_csv(
        file_path: str,
        has_targets: Optional[bool] = False,
) -> list[dict[str, Any]]:
    logger.info(f'Reading {file_path} file with targets set to {has_targets}')
    print(f'Reading {file_path} file with targets set to {has_targets}')
    with open(file_path, "r") as f:
        csv_reader = csv.reader(f)
        bulk_data = list(csv_reader)
    metadata_list: List[Dict[str, Any]] = []
    header_row = [
        "hash",
        "uris",
        "meta_hash",
        "meta_uris",
        "license_hash",
        "license_uris",
        "edition_number",
        "edition_total",
    ]
    if has_targets:
        header_row.append("target")
    rows = bulk_data
    list_headers = ["uris", "meta_uris", "license_uris"]
    n = 0
    logger.info('\n#### STEP 2 / 3 #### Building Mint Queue\n')
    print('\n#### STEP 2 / 3 #### Building Mint Queue\n')
    for row in rows:
        if len(row) > 0:
            if n > 0:
                logger.info(f'Adding NFT #{n} to minting queue ({row[1]})')
                print(f'Adding NFT #{n} to minting queue ({row[1]})')
            meta_dict: Dict[str, Any] = {
                list_headers[i]: [] for i in range(len(list_headers))
            }
            for i, header in enumerate(header_row):
                if header in list_headers:
                    meta_dict[header].append(row[i])
                elif header in ("edition_number", "edition_total") and n >= 1:
                    num = int(row[i])
                    meta_dict[header] = num
                elif header == "target":
                    meta_dict['target_address'] = row[i]
                else:
                    meta_dict[header] = row[i]
            for d in nft_data:
                meta_dict[d] = nft_data[d]
            metadata_list.append(meta_dict)
            n += 1
    t = len(metadata_list) - 1
    logger.info(f'\n{t} NFTs have been added to the minting queue\n')
    print(f'\n{t} NFTs have been added to the minting queue\n')
    network_name = get_network()
    logger.info(f'The next step will start minting and monitoring minting of NFTs on {network_name}\nYou will not be able to cancel this process, please ensure all information is correct before continuing!')
    print(f'The next step will start minting and monitoring minting of NFTs {network_name}\nYou will not be able to cancel this process, please ensure all information is correct before continuing!')
    return metadata_list


def mint(metadata_list):  # formats the json object based on the dict object and submits the RPC command
    i = 1
    logger.info('\n#### STEP 3 / 3 #### Minting NFTs \n')
    print('\n#### STEP 3 / 3 #### Minting NFTs \n')
    while i <= (len(metadata_list) - 1):
        if get_sync() == 'Synced':
            data = metadata_list[i]
            nft_mint_nft(data)
            snooze = 0
            while not mint_monitor(i):
                asleep = snooze * 10
                logger.info(f'NFT #{i} is currently minting, please be patient #### seconds elapsed  {asleep}')
                print(f'NFT #{i} is currently minting, please be patient #### seconds elapsed  {asleep}')
                sleep(10)
                snooze += 1
        else:
            logger.info('Chia instance is not synced \nPlease verify your chia instance is synced and reconfirm this mint')
            print('Chia instance is not synced \nPlease verify your chia instance is synced and reconfirm this mint')
            continue_mint()
        i += 1


def cancel_mint():  # cancels minting to allow user to edit information
    proceed = input('Would you like to proceed? (y/n , default n):  ')
    if proceed in ('y', 'Y'):
        print('')
        pass
    else:
        logger.info('\n#### CANCELED ####\nMint Canceled by User\n#### CANCELED ####')
        print('\n#### CANCELED ####\nMint Canceled by User\n#### CANCELED ####')
        exit()


def continue_mint():  # cancels minting to allow user to edit information
    proceed = input('Would you like to proceed, cancel, or wait for 10 seconds? (y/w/n , default w):  ')
    if proceed in ('y', 'Y'):
        print('')
        return True
    elif proceed in ('n', 'N'):
        logger.info('\n#### CANCELED ####\nMint Canceled by User\n#### CANCELED ####')
        print('\n#### CANCELED ####\nMint Canceled by User\n#### CANCELED ####')
        exit()
    else:
        s = 1
        while s < 10:
            logger.info(f'#### WAITING #### Mint Paused #### SECONDS ELAPSED {s} ')
            print(f'#### WAITING #### Mint Paused #### SECONDS ELAPSED {s} ')
            sleep(1)
            s += 1


def sync_verify():  # sync and network verification
    try:
        if get_sync() == 'Synced':
            network_name = get_network()
            logger.info('\n#### STEP 1 / 3 #### Confirm Network\n')
            print('\n#### STEP 1 / 3 #### Confirm Network\n')
            logger.info(f'#### {network_name} ####\nChia instance is on {network_name}\n')
            print(f'#### {network_name} ####\nChia instance is on {network_name}\n#### {network_name} ####\n')
            logger.info(f'The next step will extract NFT data from the {metadata_file} file')
            print(f'The next step will extract NFT data from the {metadata_file} file')
            return True
        else:
            logger.info(f'Chia instance is not synced\nPlease verify your chia instance is synced and restart this client')
            print(f'Chia instance is not synced\nPlease verify your chia instance is synced and restart this client')
            continue_mint()
    except Exception as e:
        logger.info('Could not contact Chia instance, please make sure it is running and synced')
        print('Could not contact Chia instance, please make sure it is running and synced')
        logger.info(repr(e))
        print(repr(e))
        continue_mint()


########################################## Event Loop ##########################################
def main():
    sync_verify()
    cancel_mint()
    metadata_list = read_metadata_csv(metadata_file, nft_targets)
    cancel_mint()
    mint(metadata_list)


if __name__ == '__main__':
    main()
