from time import sleep
from typing import Any, Dict, List, Optional
import csv
import requests
from os import path
import urllib3
urllib3.disable_warnings()


########################################## Define Defaults ##########################################
NETWORK_NAME = 'testnet10'  # to-do add validation of selected network

nft_data = {"wallet_id": 6,  # 3 is default as this should be the NFT wallet if no additional wallets have been created
            "royalty_address": "txch1u0kmn26srtwfppjyvgcvqxfejnps0m80378sxl9gchsprplla3qqk9lxgm",
            "royalty_percentage": 6,
            "fee": 615000000}  # min recommended minting fee is default

metadata_file = 'bulk_mint_metadata.csv'

nft_targets = False


########################################## System Defaults ##########################################
json_data = {}
wallet_RPC_port = 'localhost:9256'
homeDir = path.expanduser('~')
cert = (homeDir + '/.chia/mainnet/config/ssl/wallet/private_wallet.crt',
        homeDir + '/.chia/mainnet/config/ssl/wallet/private_wallet.key')


def query_wallet(url_option,
                 json_data):
    try:
        return requests.post(url='https://{}/{}'.format(wallet_RPC_port, url_option),
                             verify=False,
                             cert=cert,
                             headers={'content-type': 'application/json'},
                             json=json_data,
                             ).json()
    except Exception as e:
        print(e)
        return None


def get_network():
    url_option = "get_network_info"
    response = query_wallet(url_option=url_option, json_data=json_data)
    if response is not None:
        network_name = response['network_name']
    else:
        print('The wallet RPC cannot be reached to verify network information, make sure Chia is running')
        network_name = 'unknown'
    return network_name


def get_sync():
    url_option = "get_sync_status"
    response = query_wallet(url_option=url_option, json_data=json_data)
    if response is None:
        print('The wallet RPC cannot be reached to verify sync status, make sure Chia is running')
        return 'Not Synced'
    elif not response['synced']:
        return 'Syncing' if response['syncing'] is True else 'Not Synced'
    else:
        return 'Synced'


def nft_mint_nft(data):
    url_option = "nft_mint_nft"
    json_data = data
    response = query_wallet(url_option=url_option, json_data=json_data)
    return response


def get_transactions():
    url_option = "get_transactions"
    json_data = {"wallet_id": 1, "start": 0, "stop": 1, "reverse": False}
    response = query_wallet(url_option=url_option, json_data=json_data)

    return response['transactions'][0]['confirmed'] if response[
                                                           'success'] == True else 'Error identifying minting transaction'


def mint_monitor(i):
    status = get_transactions()
    if status == 'Error identifying minting transaction':
        print('Your NFT minting transaction cannot be identified! \nPlease monitor the chia client')
    elif status == True:
        print(f'Minting has SUCCEEDED for NFT #{i}')
    else:
        print('', end='\r')
    return status


# The read_metadata script has been adapted from the Chia network script with the same name from
# https://github.com/Chia-Network/chia-nft-minting-tool/blob/main/chianft/util/mint.py#L449
def read_metadata_csv(
        file_path: str,
        has_targets: Optional[bool] = False,
) -> list[dict[str, Any]]:
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
    print('\n#### STEP 2 / 3 #### Building Mint Queue\n')
    for row in rows:
        if len(row) > 0:
            if n > 0:
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
    print(f'\n{t} NFTs have been added to the minting queue\n')
    print('The next step will start minting and monitoring minting of NFTs')
    return metadata_list


def mint(metadata_list):  # formats the json object based on the dict object and submits the RPC command
    i = 1
    print('\n#### STEP 3 / 3 #### Minting NFTs \n')
    while i <= (len(metadata_list) - 1):
        if get_sync() == 'Synced':
            data = metadata_list[i]
            nft_mint_nft(data)
            snooze = 0
            while not mint_monitor(i):
                asleep = snooze * 10
                print(f'NFT #{i} is currently minting, please be patient #### seconds elapsed  {asleep}', end='\r')
                sleep(10)
                snooze += 1
        else:
            print('Chia instance is not synced \nPlease verify your chia instance is synced and reconfirm this mint')
            continue_mint()
        i += 1


def cancel_mint():  # cancels minting to allow user to edit information
    proceed = input('Would you like to proceed? (y/n , default n):  ')
    if proceed in ('y', 'Y'):
        print('')
        pass
    else:
        print('\n#### CANCELED ####\nMint Canceled by User\n#### CANCELED ####')
        exit()


def continue_mint():  # cancels minting to allow user to edit information
    proceed = input('Would you like to proceed, cancel, or wait for 10 seconds? (y/w/n , default w):  ')
    if proceed in ('y', 'Y'):
        print('')
        return True
    elif proceed in ('n', 'N'):
        print('\n#### CANCELED ####\nMint Canceled by User\n#### CANCELED ####')
        exit()
    else:
        s = 1
        while s < 10:
            print(f'#### WAITING #### Mint Paused #### SECONDS ELAPSED {s} ')
            sleep(1)
            s += 1


def sync_verify():  # sync and network verification
    try:
        if get_sync() == 'Synced':
            network_name = get_network()
            print('\n#### STEP 1 / 3 #### Confirm Network\n')
            print(f'#### {network_name} ####\nChia instance is on {network_name}\n#### {network_name} ####\n')
            print(f'The next step will extract NFT data from the {metadata_file} file')
            return True
        else:
            print(f'Chia instance is not synced\nPlease verify your chia instance is synced and restart this client')
            continue_mint()
    except Exception as e:
        print('Could not contact Chia instance, please make sure it is running and synced')
        print(repr(e))
        continue_mint()


########################################## Event Loop ##########################################
def main():
    sync_verify()
    cancel_mint()
    metadata_list = read_metadata_csv(metadata_file, nft_targets)
    cancel_mint()
    mint(metadata_list)


main()
