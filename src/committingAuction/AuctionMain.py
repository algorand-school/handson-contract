from time import time, sleep
from hashlib import sha256

# user declared account mnemonics
creator_mnemonic = "employ spot view century canyon fossil upon hollow tone chicken behave bamboo cool correct vehicle mirror movie scrap budget join music then poverty ability gadget"
# user declared algod connection parameters. Node must have EnableDeveloperAPI set to true in its config
algod_address = "http://localhost:4001"
algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

from src.committingAuction.AuctionContract import *
from algosdk.atomic_transaction_composer import AtomicTransactionComposer
from algosdk.logic import get_application_address

def closeAuction(
        client: algod.AlgodClient,
        app_id: int,
        closer: str,
):
    global_state = read_global_state(client, app_id)

    nft_id = global_state['nft_id']

    accounts: List[str] = [encoding.encode_address(global_state["seller"])]

    if any(global_state["bid_account"]):
        # if "bid_account" is not the zero address
        accounts.append(encoding.encode_address(global_state["bid_account"]))


    deleteTxn = transaction.ApplicationDeleteTxn(
        sender=account.address_from_private_key(closer),
        index=app_id,
        accounts=accounts,
        foreign_assets=[nft_id],
        sp=client.suggested_params(),
    )
    signedDeleteTxn = deleteTxn.sign(closer)

    client.send_transaction(signedDeleteTxn)
    transaction.wait_for_confirmation(client, signedDeleteTxn.get_txid())
    print(signedDeleteTxn.get_txid())

def placeBid(
        client: algod.AlgodClient,
        app_id: int,
        bidder_sk: str,
        bid_amount: int
) -> None:
    app_addr = get_application_address(app_id)

    suggestedParams = client.suggested_params()
    global_state = read_global_state(client, app_id)
    nft_id = global_state['nft_id']

    if any(global_state["bid_account"]):
        # if "bid_account" is not the zero address
        prevBidLeader = global_state["bid_account"]
    else:
        prevBidLeader = None

    atc = AtomicTransactionComposer()
    bidder_addr = account.address_from_private_key(bidder_sk)
    bidder_signer = AccountTransactionSigner(bidder_sk)

    ptxn = transaction.PaymentTxn(bidder_addr, suggestedParams, app_addr, bid_amount)
    tws = TransactionWithSigner(ptxn, bidder_signer)
    atc.add_transaction(tws)

    with open("./com_auction_contract.json") as f:
        js = f.read()
    if prevBidLeader == None:
        atc.add_method_call(app_id=app_id,
                            method=get_method('on_bid', js),
                            sender=bidder_addr,
                            sp=suggestedParams,
                            signer=bidder_signer,
                            foreign_assets=[nft_id],
                            )
    else:
        atc.add_method_call(app_id=app_id,
                            method=get_method('on_bid', js),
                            sender=bidder_addr,
                            sp=suggestedParams,
                            signer=bidder_signer,
                            foreign_assets=[nft_id],
                            accounts=[prevBidLeader]
                            )
    result = atc.execute(client, 10)

    print("Global state:", read_global_state(client, app_id))
    print("Local state:", read_local_state(client, bidder_addr, app_id))


def commitAuctionApp(
        client: algod.AlgodClient,
        app_id: int,
        bidder_sk: str,
        value: int,
        deposit: int
):
    app_addr = get_application_address(app_id)
    global_state = read_global_state(client, app_id)
    nft_id = global_state['nft_id']
    suggestedParams = client.suggested_params()

    atc = AtomicTransactionComposer()
    bidder_addr = account.address_from_private_key(bidder_sk)
    bidder_signer = AccountTransactionSigner(bidder_sk)

    ptxn = transaction.PaymentTxn(bidder_addr, suggestedParams, app_addr, deposit)
    tws = TransactionWithSigner(ptxn, bidder_signer)
    atc.add_transaction(tws)

    with open("./com_auction_contract.json") as f:
        js = f.read()

    commitment = bytes(bytearray.fromhex(sha256(value.to_bytes(8, 'big')).hexdigest()))
    app_args = [
        commitment
    ]
    print(commitment)

    atc.add_method_call(
        app_id=app_id,
        method=get_method("on_commit", js),
        sender=account.address_from_private_key(bidder_sk),
        sp=suggestedParams,
        signer=bidder_signer,
        method_args=app_args,
        on_complete=transaction.OnComplete.OptInOC,
        foreign_assets=[nft_id]
    )

    result = atc.execute(client, 10)
    print(transaction.wait_for_confirmation(client, result.tx_ids[1]))
    print("Local state:", read_local_state(client, bidder_addr, app_id))



def setupAuctionApp(
        client: algod.AlgodClient,
        app_id: int,
        funder_sk: str,
        nft_holder_sk: str,
        nft_id: int,
):
    app_addr = get_application_address(app_id)

    suggestedParams = client.suggested_params()

    fundingAmount = (
        # min account balance
            100_000
            # additional min balance to opt into NFT
            + 100_000
            # 3 * min txn fee
            + 3 * 1_000
    )

    atc = AtomicTransactionComposer()
    funder_addr = account.address_from_private_key(funder_sk)
    nft_holder_addr = account.address_from_private_key(nft_holder_sk)
    signer_funder = AccountTransactionSigner(funder_sk)
    signer_nft_holder = AccountTransactionSigner(nft_holder_sk)

    ptxn = transaction.PaymentTxn(funder_addr, suggestedParams, app_addr, fundingAmount)
    tws = TransactionWithSigner(ptxn, signer_funder)
    atc.add_transaction(tws)

    with open("./com_auction_contract.json") as f:
        js = f.read()
    atc.add_method_call(app_id=app_id, method=get_method('on_setup', js), sender=funder_addr,
                        sp=suggestedParams, signer=signer_funder, foreign_assets=[nft_id])

    atxn = transaction.AssetTransferTxn(nft_holder_addr, suggestedParams, app_addr, 1, nft_id)
    tws = TransactionWithSigner(atxn, signer_nft_holder)
    atc.add_transaction(tws)

    result = atc.execute(client, 10)
    for res in result.tx_ids:
        print(res)



def createAuctionApp(
        algod_client: algod.AlgodClient,
        senderSK: str,
        seller: str,
        nftID: int,
        startTime: int,
        commitTime: int,
        endTime: int,
        reserve: int,
        minBidIncrement: int,
        deposit: int
) -> int:
    # declare application state storage (immutable)
    local_ints = 1
    local_bytes = 1
    global_ints = 10
    global_bytes = 2
    global_schema = transaction.StateSchema(global_ints, global_bytes)
    local_schema = transaction.StateSchema(local_ints, local_bytes)

    # Compile the program
    router = getRouter()
    approval_program, clear_program, contract = router.compile_program(version=6)

    with open("./com_auction_approval.teal", "w") as f:
        f.write(approval_program)

    with open("./com_auction_clear.teal", "w") as f:
        f.write(clear_program)

    with open("./com_auction_contract.json", "w") as f:
        import json

        f.write(json.dumps(contract.dictify()))

    # compile program to binary
    approval_program_compiled = compile_program(algod_client, approval_program)

    # compile program to binary
    clear_state_program_compiled = compile_program(algod_client, clear_program)

    print("--------------------------------------------")
    print("Deploying Auction application......")

    app_args = [
        seller,
        nftID,
        startTime,
        commitTime,
        endTime,
        reserve,
        minBidIncrement,
        deposit
    ]

    atc = AtomicTransactionComposer()
    signer = AccountTransactionSigner(senderSK)
    sp = algod_client.suggested_params()

    with open("./com_auction_contract.json") as f:
        js = f.read()

    # Simple call to the `create_app` method, method_args can be any type but _must_
    # match those in the method signature of the contract
    atc.add_method_call(
        app_id=0,
        method=get_method("create_app", js),
        sender=account.address_from_private_key(senderSK),
        sp=sp,
        signer=signer,
        approval_program=approval_program_compiled,
        clear_program=clear_state_program_compiled,
        local_schema=local_schema,
        global_schema=global_schema,
        method_args=app_args
    )

    result = atc.execute(algod_client, 10)
    app_id = transaction.wait_for_confirmation(algod_client, result.tx_ids[0])['application-index']

    for res in result.abi_results:
        print(res.return_value)

    print("Global state:", read_global_state(algod_client, app_id))

    assert app_id is not None and app_id > 0
    return app_id, contract

def main():
    creator_private_key = get_private_key_from_mnemonic(creator_mnemonic)
    creator_address = account.address_from_private_key(creator_private_key)
    print(creator_address)

    # initialize an algodClient
    algod_client = algod.AlgodClient(algod_token, algod_address)
    seller_sk = account.generate_account()[0]
    seller = account.address_from_private_key(seller_sk)

    bidder_sk = account.generate_account()[0]
    bidder = account.address_from_private_key(bidder_sk)
    print(seller)

    txn = transaction.PaymentTxn(
        sender=creator_address,
        receiver=seller,
        amt=10000000,
        sp=algod_client.suggested_params(),
    )
    signedTxn = txn.sign(creator_private_key)
    algod_client.send_transaction(signedTxn)
    transaction.wait_for_confirmation(algod_client, signedTxn.get_txid())

    txn = transaction.PaymentTxn(
        sender=creator_address,
        receiver=bidder,
        amt=10000000,
        sp=algod_client.suggested_params(),
    )
    signedTxn = txn.sign(creator_private_key)
    algod_client.send_transaction(signedTxn)
    transaction.wait_for_confirmation(algod_client, signedTxn.get_txid())

    nftAmount = 1
    nftID = createDummyAsset(algod_client, nftAmount, seller, seller_sk)
    print("The NFT ID is", nftID)
    startTime = int(time()) + 10  # start time is 10 seconds in the future
    commitTime = startTime + 10
    endTime = startTime + 30  # end time is 30 seconds after start
    reserve = 1_000_000  # 1 Algo
    increment = 100_000  # 0.1 Algo
    deposit = 100_000 # 0.1 Algo
    print("Bob is creating an auction that lasts 30 seconds to auction off the NFT...")

    app_id, contract = createAuctionApp(algod_client, creator_private_key,
                                        seller, nftID, startTime, commitTime,
                                        endTime, reserve, increment, deposit)

    print("--------------------------------------------")
    print("Setup the Auction application......")
    setupAuctionApp(algod_client, app_id, creator_private_key, seller_sk, nftID)

    print("--------------------------------------------")
    print("Committing to the Auction application......")
    commitAuctionApp(algod_client, app_id, bidder_sk, reserve, deposit)

    sleep(10)

    print("--------------------------------------------")
    print("Bidding the Auction application......")
    placeBid(algod_client, app_id, bidder_sk, reserve)
    optInToAsset(algod_client, nftID, bidder_sk)

    sleep(10)
    print("--------------------------------------------")
    print("Closing the Auction application......")

    closeAuction(algod_client, app_id, seller_sk)

if __name__ == "__main__":
    main()