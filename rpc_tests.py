from chia.rpc.wallet_rpc_client import WalletRpcClient


def main():
    WalletRpcClient.get_logged_in_fingerprint()


if __name__ == "__main__":
    main()
