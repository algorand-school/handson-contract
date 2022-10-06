import base64

from algosdk import account, mnemonic, encoding
from random import choice, randint
from algosdk.atomic_transaction_composer import *
from algosdk.abi import Method, Contract

# helper function to compile program source
def compile_program(client, source_code):
    compile_response = client.compile(source_code)
    return base64.b64decode(compile_response["result"])


# helper function that converts a mnemonic passphrase into a private signing key
def get_private_key_from_mnemonic(mn):
    private_key = mnemonic.to_private_key(mn)
    return private_key


# helper function that formats global state for printing
def format_state(state):
    formatted = {}
    for item in state:
        key = item["key"]
        value = item["value"]
        formatted_key = base64.b64decode(key).decode("utf-8")
        if value["type"] == 1:
            # byte string
            formatted_value = base64.b64decode(value["bytes"])
            formatted[formatted_key] = formatted_value
        else:
            # integer
            formatted[formatted_key] = value["uint"]
    return formatted


# helper function to read app global state
def read_global_state(client, app_id):
    app = client.application_info(app_id)
    global_state = (
        app["params"]["global-state"] if "global-state" in app["params"] else []
    )
    return format_state(global_state)

def read_local_state(client, addr, app_id) :
    results = client.account_info(addr)
    local_state = results['apps-local-state'][0]
    for index in local_state:
        if local_state[index] == app_id :
            local = local_state['key-value']
    return format_state(local)

def optInToAsset(
        client: algod.AlgodClient, assetID: int, sk: str
):
    txn = transaction.AssetOptInTxn(
        sender=account.address_from_private_key(sk),
        index=assetID,
        sp=client.suggested_params(),
    )
    signedTxn = txn.sign(sk)

    client.send_transaction(signedTxn)
    return transaction.wait_for_confirmation(client, signedTxn.get_txid())

# create new application
def create_app(
        client, private_key, approval_program, clear_program, global_schema, local_schema, args=[]
):
    # define sender as creator
    sender = account.address_from_private_key(private_key)

    # declare on_complete as NoOp
    on_complete = transaction.OnComplete.NoOpOC.real

    # get node suggested parameters
    params = client.suggested_params()

    # create unsigned transaction
    txn = transaction.ApplicationCreateTxn(
        sender,
        params,
        on_complete,
        approval_program,
        clear_program,
        global_schema,
        local_schema,
        args,
    )

    # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()
    client.send_transactions([signed_txn])

    # wait for confirmation
    try:
        transaction_response = transaction.wait_for_confirmation(client, tx_id, 10)
        print("TXID: ", tx_id)
        print(
            "Result confirmed in round: {}".format(
                transaction_response["confirmed-round"]
            )
        )

    except Exception as err:
        print(err)
        return

    # display results
    transaction_response = client.pending_transaction_info(tx_id)
    app_id = transaction_response["application-index"]
    print("Created new app-id:", app_id)

    return app_id

# Utility function to get the Method object for a given method name
def get_method(name: str, js: str) -> Method:
    c = Contract.from_json(js)
    for m in c.methods:
        if m.name == name:
            return m
    raise Exception("No method with the name {}".format(name))


# call application
def call_app(client, private_key, index, contract, method_name="increment", method_args=[]):
    # get sender address
    sender = account.address_from_private_key(private_key)
    # create a Signer object
    signer = AccountTransactionSigner(private_key)

    # get node suggested parameters
    sp = client.suggested_params()

    # Create an instance of AtomicTransactionComposer
    atc = AtomicTransactionComposer()
    atc.add_method_call(
        app_id=index,
        method=contract.get_method_by_name(method_name),
        sender=sender,
        sp=sp,
        signer=signer,
        method_args=method_args,  # No method args needed here
    )

    # send transaction
    results = atc.execute(client, 2)

    # wait for confirmation
    print("TXID: ", results.tx_ids[0])
    print("Result confirmed in round: {}".format(results.confirmed_round))

def createDummyAsset(client: algod.AlgodClient, total: int,
                     account: str, sk:str) -> int:

    randomNumber = randint(0, 999)
    # this random note reduces the likelihood of this transaction looking like a duplicate
    randomNote = bytes(randint(0, 255) for _ in range(20))

    txn = transaction.AssetCreateTxn(
        sender=account,
        total=total,
        decimals=0,
        default_frozen=False,
        manager=account,
        reserve=account,
        freeze=account,
        clawback=account,
        unit_name=f"ALGOT",
        asset_name=f"AlgorandGOT",
        url=f"https://github.com/algorand-school/handson-contract/blob/main/image/algorand_throne.jpg",
        note=randomNote,
        sp=client.suggested_params(),
    )
    signedTxn = txn.sign(sk)

    client.send_transaction(signedTxn)

    response = transaction.wait_for_confirmation(client, signedTxn.get_txid())
    print(response)
    assert response['asset-index'] is not None and response['asset-index'] > 0
    return response['asset-index']