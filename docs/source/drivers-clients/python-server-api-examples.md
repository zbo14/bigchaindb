# The Python Server API by Example

**Currently, the HTTP Client-Server API is very rudimentary, so you may want to use the Python Server API to develop prototype clients and applications, for now. Keep in mind that in the future, clients will only be able to use the HTTP Client-Server API (and possibly other Client-Server APIs) to communicate with BigchainDB nodes.**

This section has examples of using the Python Server API to interact _directly_ with a BigchainDB node running BigchainDB Server. That is, in these examples, the Python code and BigchainDB Server run on the same machine.

One can also interact with a BigchainDB node via other APIs, including the HTTP Client-Server API.


## Getting Started

First, make sure you have RethinkDB and BigchainDB _installed and running_, i.e. you [installed them](../dev-and-test/setup-run-node.html) and you ran:
```text
$ rethinkdb
$ bigchaindb configure
$ bigchaindb start
```

Don't shut them down! In a new terminal, open a Python shell:
```text
$ python
```

Now we can import the `Bigchain` class and create an instance:
```python
from bigchaindb import Bigchain
b = Bigchain()
```

This instantiates an object `b` of class `Bigchain`. When instantiating a `Bigchain` object without arguments (as above), it reads the configurations stored in `$HOME/.bigchaindb`.

In a federation of BigchainDB nodes, each node has its own `Bigchain` instance.

The `Bigchain` class is the main API for all BigchainDB interactions, right now. It does things that BigchainDB nodes do, but it also does things that BigchainDB clients do. In the future, it will be refactored into different parts. The `Bigchain` class is documented [elsewhere (link)](../appendices/the-Bigchain-class.html).


## Create a Digital Asset

At a high level, a "digital asset" is something which can be represented digitally and can be assigned to a user. In BigchainDB, users are identified by their public key, and the data payload in a digital asset is represented using a generic [Python dict](https://docs.python.org/3.4/tutorial/datastructures.html#dictionaries).

In BigchainDB, only the federation nodes are allowed to create digital assets, by doing a special kind of transaction: a `CREATE` transaction.

```python
from bigchaindb_common import crypto
from bigchaindb.model import Transaction

# Create a test user
testuser1_priv, testuser1_pub = crypto.generate_key_pair()

# Define a digital asset data payload
digital_asset_payload = {'msg': 'Hello BigchainDB!'}

# A create transaction uses the operation `CREATE` and has no inputs
tx = Transaction.create([b.me], [testuser1_pub], payload=digital_asset_payload)

# All transactions need to be signed by the user creating the transaction
tx_signed = tx.sign([b.me_private])

# Write the transaction to the bigchain.
# The transaction will be stored in a backlog where it will be validated,
# included in a block, and written to the bigchain
b.write_transaction(tx_signed)
```

## Read the Creation Transaction from the DB

After a couple of seconds, we can check if the transactions was included in the bigchain:
```python
# Retrieve a transaction from the bigchain
tx_retrieved = b.get_transaction(tx_signed.id)
tx_retrieved.to_dict()
```

```python
{
    "id":"933cd83a419d2735822a2154c84176a2f419cbd449a74b94e592ab807af23861",
    "transaction":{
        "conditions":[
            {
                "cid":0,
                "condition":{
                    "details":{
                        "bitmask":32,
                        "public_key":"BwuhqQX8FPsmqYiRV2CSZYWWsSWgSSQQFHjqxKEuqkPs",
                        "signature":None,
                        "type":"fulfillment",
                        "type_id":4
                    },
                    "uri":"cc:4:20:oqXTWvR3afHHX8OaOO84kZxS6nH4GEBXD4Vw8Mc5iBo:96"
                },
                "owners_after":[
                    "BwuhqQX8FPsmqYiRV2CSZYWWsSWgSSQQFHjqxKEuqkPs"
                ]
            }
        ],
        "data":{
            "hash":"872fa6e6f46246cd44afdb2ee9cfae0e72885fb0910e2bcf9a5a2a4eadb417b8",
            "payload":{
                "msg":"Hello BigchainDB!"
            }
        },
        "fulfillments":[
            {
                "owners_before":[
                    "3LQ5dTiddXymDhNzETB1rEkp4mA7fEV1Qeiu5ghHiJm9"
                ],
                "fid":0,
                "fulfillment":"cf:4:Iq-BcczwraM2UpF-TDPdwK8fQ6IXkD_6uJaxBZd984yxCGX7Csx-S2FBVe8LVyW2sAtmjsOSV0oiw9-s_9qSJB0dDUl_x8YQk5yxNdQyNVWVM1mWSGQL68gMngdmFG8O",
                "input":None
            }
        ],
        "operation":"CREATE",
        "timestamp":"1460981667.449279"
    },
    "version":1
}

```

The new owner of the digital asset is now `BwuhqQX8FPsmqYiRV2CSZYWWsSWgSSQQFHjqxKEuqkPs`, which is the public key of `testuser1`.

Note that the current owner (with public key `3LQ5dTiddXymDhNzETB1rEkp4mA7fEV1Qeiu5ghHiJm9`) is the federation node which created the asset and assigned it to `testuser1`.

## Transfer the Digital Asset

Now that `testuser1` has a digital asset assigned to him, he can transfer it to another user. Transfer transactions require an input. The input will be the transaction id of a digital asset that was assigned to `testuser1`, which in our case is `933cd83a419d2735822a2154c84176a2f419cbd449a74b94e592ab807af23861`.

BigchainDB makes use of the crypto-conditions library to both cryptographically lock and unlock transactions.
The locking script is refered to as a `condition` and a corresponding `fulfillment` unlocks the condition of the `input_tx`.

Since a transaction can have multiple outputs with each its own (crypto)condition, each transaction input should also refer to the condition index `cid`.

<p align="center">
  <img width="70%" height="70%" src ="../_static/tx_single_condition_single_fulfillment_v1.png" />
</p>


```python
# Create a second testuser
testuser2_priv, testuser2_pub = crypto.generate_key_pair()

# Retrieve the transaction with condition id
tx_unspent = b.get_owned_ids(testuser1_pub).pop()
tx_unspent.to_dict()
```

```python
{
    "cid":0,
    "txid":"933cd83a419d2735822a2154c84176a2f419cbd449a74b94e592ab807af23861"
}
```

```python
# Get the transaction to spend
tx_owned = b.get_transaction(tx_unspent.txid)

# Create a transfer transaction
tx_transfer = Transaction.transfer(tx_owned.to_inputs(), [testuser2_pub])

# Sign the transaction
tx_transfer_signed = tx_transfer.sign([testuser1_priv])

# Write the transaction
b.write_transaction(tx_transfer_signed)

# Check if the transaction is already in the bigchain
tx_transfer_retrieved = b.get_transaction(tx_transfer_signed.id)
tx_transfer_retrieved.to_dict()
```

```python
{
    "id":"aa11365317cb89bfdae2375bae76d6b8232008f8672507080e3766ca06976dcd",
    "transaction":{
        "conditions":[
            {
                "cid":0,
                "condition":{
                    "details":{
                        "bitmask":32,
                        "public_key":"qv8DvdNG5nZHWCP5aPSqgqxAvaPJpQj19abRvFCntor",
                        "signature":None,
                        "type":"fulfillment",
                        "type_id":4
                    },
                    "uri":"cc:4:20:DIfyalZvV_9ukoO01mxmK3nxsfAWSKYYF33XDYkbY4E:96"
                },
                "owners_after":[
                    "qv8DvdNG5nZHWCP5aPSqgqxAvaPJpQj19abRvFCntor"
                ]
            }
        ],
        "data":None,
        "fulfillments":[
            {
                "owners_before":[
                    "BwuhqQX8FPsmqYiRV2CSZYWWsSWgSSQQFHjqxKEuqkPs"
                ],
                "fid":0,
                "fulfillment":"cf:4:oqXTWvR3afHHX8OaOO84kZxS6nH4GEBXD4Vw8Mc5iBqzkVR6cFJhRvMGKa-Lc81sdYWVu0ZSMPGht-P7s6FZLkRXDqrwwInabLhjx14eABY34oHb6IyWcB-dyQnlVNEI",
                "input":{
                    "cid":0,
                    "txid":"933cd83a419d2735822a2154c84176a2f419cbd449a74b94e592ab807af23861"
                }
            }
        ],
        "operation":"TRANSFER",
        "timestamp":"1460981677.472037"
    },
    "version":1
}
```

## Double Spends

BigchainDB makes sure that a user can't transfer the same digital asset two or more times (i.e. it prevents double spends).

If we try to create another transaction with the same input as before, the transaction will be marked invalid and the validation will throw a double spend exception:

```python
# Create another transfer transaction with the same input
tx_transfer2 = Transaction.transfer(tx_retrieved.to_inputs(), [testuser2_pub])

# Sign the transaction
tx_transfer_signed2 = tx_transfer2.sign([testuser1_priv])

# Check if the transaction is valid
b.validate_transaction(tx_transfer_signed2)
```

```python
DoubleSpend: input `{'cid': 0, 'txid': '933cd83a419d2735822a2154c84176a2f419cbd449a74b94e592ab807af23861'}` was already spent
```

## Multiple Owners

To create a new digital asset with _multiple_ owners, one can simply provide a list of `owners_after`:

```python
# Create a new asset and assign it to multiple owners
tx_multisig = Transaction.create([b.me], [testuser1_pub, testuser2_pub])

# Sign the transaction
tx_multisig_signed = tx_multisig.sign([b.me_private])

# Write the transaction
b.write_transaction(tx_multisig_signed)

# Check if the transaction is already in the bigchain
tx_multisig_retrieved = b.get_transaction(tx_multisig_signed.id)
tx_multisig_retrieved.to_dict()
```

```python
{
    "id":"a9a6e5c74ea02b8885c83125f1b74a2ba8ca42236ec5e1c358aa1053ec721ccb",
    "transaction":{
        "conditions":[
            {
                "cid":0,
                "condition":{
                    "details":{
                        "bitmask":41,
                        "subfulfillments":[
                            {
                                "bitmask":32,
                                "public_key":"BwuhqQX8FPsmqYiRV2CSZYWWsSWgSSQQFHjqxKEuqkPs",
                                "signature":None,
                                "type":"fulfillment",
                                "type_id":4,
                                "weight":1
                            },
                            {
                                "bitmask":32,
                                "public_key":"qv8DvdNG5nZHWCP5aPSqgqxAvaPJpQj19abRvFCntor",
                                "signature":None,
                                "type":"fulfillment",
                                "type_id":4,
                                "weight":1
                            }
                        ],
                        "threshold":2,
                        "type":"fulfillment",
                        "type_id":2
                    },
                    "uri":"cc:2:29:DpflJzUSlnTUBx8lD8QUolOA-M9nQnrGwvWSk7f3REc:206"
                },
                "owners_after":[
                    "BwuhqQX8FPsmqYiRV2CSZYWWsSWgSSQQFHjqxKEuqkPs",
                    "qv8DvdNG5nZHWCP5aPSqgqxAvaPJpQj19abRvFCntor"
                ]
            }
        ],
        "data":None,
        "fulfillments":[
            {
                "owners_before":[
                    "3LQ5dTiddXymDhNzETB1rEkp4mA7fEV1Qeiu5ghHiJm9"
                ],
                "fid":0,
                "fulfillment":"cf:4:Iq-BcczwraM2UpF-TDPdwK8fQ6IXkD_6uJaxBZd984z5qdHRz9Jag68dkOyZS5_YoTR_0WpwiUnBGoNgwjwEuIn5JNm7Kksi0nUnHsWssyXISkmqRnHH-30HQhKjznIH",
                "input":None
            }
        ],
        "operation":"CREATE",
        "timestamp":"1460981687.501433"
    },
    "version":1
}
```

The asset can be transferred as soon as each of the `owners_after` signs the transaction.

To do so, simply provide a list of all private keys to the signing routine:

```python
# Create a third testuser
testuser3_priv, testuser3_pub = crypto.generate_key_pair()

# Retrieve the multisig transaction link
tx_multisig_unspents = b.get_owned_ids(testuser2_pub).pop()
tx_multisig_retrieved = b.get_transaction(tx_multisig_unspents.txid)

# Transfer the asset from the 2 owners to the third testuser
tx_multisig_transfer = Transaction.transfer(tx_multisig_retrieved.to_inputs(), [testuser3_pub])

# Sign with both private keys
tx_multisig_transfer_signed = tx_multisig_transfer.sign([testuser1_priv, testuser2_priv])

# Write the transaction
b.write_transaction(tx_multisig_transfer_signed)

# Check if the transaction is already in the bigchain
tx_multisig_transfer_retrieved = b.get_transaction(tx_multisig_transfer_signed.id)
tx_multisig_transfer_retrieved.to_dict()
```

```python
{
    "id":"e689e23f774e7c562eeb310c7c712b34fb6210bea5deb9175e48b68810029150",
    "transaction":{
        "conditions":[
            {
                "cid":0,
                "condition":{
                    "details":{
                        "bitmask":32,
                        "public_key":"8YN9fALMj9CkeCcmTiM2kxwurpkMzHg9RkwSLJKMasvG",
                        "signature":None,
                        "type":"fulfillment",
                        "type_id":4
                    },
                    "uri":"cc:4:20:cAq6JQJXtwlxURqrksiyqLThB9zh08ZxSPLTDSaReYE:96"
                },
                "owners_after":[
                    "8YN9fALMj9CkeCcmTiM2kxwurpkMzHg9RkwSLJKMasvG"
                ]
            }
        ],
        "data":None,
        "fulfillments":[
            {
                "owners_before":[
                    "BwuhqQX8FPsmqYiRV2CSZYWWsSWgSSQQFHjqxKEuqkPs",
                    "qv8DvdNG5nZHWCP5aPSqgqxAvaPJpQj19abRvFCntor"
                ],
                "fid":0,
                "fulfillment":"cf:4:oqXTWvR3afHHX8OaOO84kZxS6nH4GEBXD4Vw8Mc5iBrcuiGDNVgpH9SwiuNeYZ-nugSTbxykH8W1eH5UJiunmnBSlKnJb8_QYOQsMAXl3MyLq2pWAyI45ZSG1rr2CksI",
                "input":{
                    "cid":0,
                    "txid":"aa11365317cb89bfdae2375bae76d6b8232008f8672507080e3766ca06976dcd"
                }
            }
        ],
        "operation":"TRANSFER",
        "timestamp":"1460981697.526878"
    },
    "version":1
}
```

## Multiple Inputs and Outputs

With BigchainDB it is possible to send multiple assets to someone in a single transfer.

The transaction will create a `fulfillment` - `condition` pair for each input, which can be referred to by `fid` and `cid` respectively.

<p align="center">
  <img width="70%" height="70%" src ="../_static/tx_multi_condition_multi_fulfillment_v1.png" />
</p>

```python
# Create some assets for bulk transfer
for i in range(3):
    tx_mimo_asset = Transaction.create([b.me], [testuser1_pub])
    tx_mimo_asset_signed = tx_mimo_asset.sign([b.me_private])
    b.write_transaction(tx_mimo_asset_signed)

# Wait until they appear on the bigchain and retrieve the transactions
owned_mimo_unspents  = b.get_owned_ids(testuser1_pub)

# Check the number of assets
print(len(owned_mimo_inputs))

# get the transactions from the unspents
owned_mimo_transactions = [b.get_transaction(unspent.to_inputs() for unspent in owned_mimo_unspents]
# and flatten the list of inputs
owned_mimo_transactions = sum(owned_mimo_transactions, [])

# Create a signed TRANSFER transaction with all the assets and assign all of them
# to testuser2_pub
tx_mimo = Transaction.transfer(owned_mimo_transactions, len(owned_mimo_transactions) * [[testuser2_pub]])
tx_mimo_signed = tx_mimo.sign([testuser1_priv])

# Write the transaction
b.write_transaction(tx_mimo_signed)

# Check if the transaction is already in the bigchain
tx_mimo_retrieved = b.get_transaction(tx_mimo_signed.id)
tx_mimo_retrieved.to_dict()
```

```python
{
    "id":"8b63689691a3c2e8faba89c6efe3caa0661f862c14d88d1e63ebd65d49484de2",
    "transaction":{
        "conditions":[
            {
                "cid":0,
                "condition":{
                    "details":{
                        "bitmask":32,
                        "public_key":"qv8DvdNG5nZHWCP5aPSqgqxAvaPJpQj19abRvFCntor",
                        "signature":None,
                        "type":"fulfillment",
                        "type_id":4
                    },
                    "uri":"cc:4:20:2AXg2JJ7mQ8o2Q9-hafP-XmFh3YR7I2_Sz55AubfxIc:96"
                },
                "owners_after":[
                    "qv8DvdNG5nZHWCP5aPSqgqxAvaPJpQj19abRvFCntor"
                ]
            },
            {
                "cid":1,
                "condition":{
                    "details":{
                        "bitmask":32,
                        "public_key":"qv8DvdNG5nZHWCP5aPSqgqxAvaPJpQj19abRvFCntor",
                        "signature":None,
                        "type":"fulfillment",
                        "type_id":4
                    },
                    "uri":"cc:4:20:2AXg2JJ7mQ8o2Q9-hafP-XmFh3YR7I2_Sz55AubfxIc:96"
                },
                "owners_after":[
                    "qv8DvdNG5nZHWCP5aPSqgqxAvaPJpQj19abRvFCntor"
                ]
            },
            {
                "cid":2,
                "condition":{
                    "details":{
                        "bitmask":32,
                        "public_key":"qv8DvdNG5nZHWCP5aPSqgqxAvaPJpQj19abRvFCntor",
                        "signature":None,
                        "type":"fulfillment",
                        "type_id":4
                    },
                    "uri":"cc:4:20:2AXg2JJ7mQ8o2Q9-hafP-XmFh3YR7I2_Sz55AubfxIc:96"
                },
                "owners_after":[
                    "qv8DvdNG5nZHWCP5aPSqgqxAvaPJpQj19abRvFCntor"
                ]
            }
        ],
        "data":None,
        "fulfillments":[
            {
                "owners_before":[
                    "BwuhqQX8FPsmqYiRV2CSZYWWsSWgSSQQFHjqxKEuqkPs"
                ],
                "fid":0,
                "fulfillment":"cf:4:sTzo4fvm8U8XrlXcgcGkNZgkfS9QHg2grgrJiX-c0LT_a83V0wbNRVbmb0eOy6tLyRw0kW1FtsN29yTcTAILX5-fyBITrPUqPzIzF85l8yIAMSjVfH-h6YNcUQBj0o4B",
                "input":{
                    "cid":0,
                    "txid":"9a99f3c82aea23fb344acb1505926365e2c6b722761c4be6ab8916702c94c024"
                }
            },
            {
                "owners_before":[
                    "BwuhqQX8FPsmqYiRV2CSZYWWsSWgSSQQFHjqxKEuqkPs"
                ],
                "fid":1,
                "fulfillment":"cf:4:sTzo4fvm8U8XrlXcgcGkNZgkfS9QHg2grgrJiX-c0LSJe3B_yjgXd1JHPBJhAdywCzR_ykEezi3bPNucGHl5mgPvpsLpHWrdIvZa3arFD91AepXILaNCF0y8cxIBOyEE",
                "input":{
                    "cid":0,
                    "txid":"783014b92f35da0c2526e1db6f81452c61853d29eda50d057fd043d507d03ef9"
                }
            },
            {
                "owners_before":[
                    "BwuhqQX8FPsmqYiRV2CSZYWWsSWgSSQQFHjqxKEuqkPs"
                ],
                "fid":2,
                "fulfillment":"cf:4:sTzo4fvm8U8XrlXcgcGkNZgkfS9QHg2grgrJiX-c0LReUQd-vDMseuVi03qY5Fxetv81fYpy3z1ncHIGc2bX7R69aS-yH5_deV9qaKjc1ZZFN5xXsB9WFpQkf9VQ-T8B",
                "input":{
                    "cid":0,
                    "txid":"9ab6151334b06f3f3aab282597ee8a7c12b9d7a0c43f356713f7ef9663375f50"
                }
            }
        ],
        "operation":"TRANSFER",
        "timestamp":"1461049149.568927"
    },
    "version":1
}
```


## Crypto-Conditions (Advanced)

### Introduction

Crypto-conditions provide a mechanism to describe a signed message such that multiple actors in a distributed system can all verify the same signed message and agree on whether it matches the description.

This provides a useful primitive for event-based systems that are distributed on the Internet since we can describe events in a standard deterministic manner (represented by signed messages) and therefore define generic authenticated event handlers.

Crypto-conditions are part of the Interledger protocol and the full specification can be found [here](https://interledger.org/five-bells-condition/spec.html).

Implementations of the crypto-conditions are available in [Python](https://github.com/bigchaindb/cryptoconditions) and [JavaScript](https://github.com/interledger/five-bells-condition).


### Threshold Conditions

Threshold conditions introduce multi-signatures, m-of-n signatures or even more complex binary Merkle trees to BigchainDB.

Setting up a generic threshold condition is a bit more elaborate than regular transaction signing but allow for flexible signing between multiple parties or groups.

The basic workflow for creating a more complex cryptocondition is the following:

1. Create a transaction template that include the public key of all (nested) parties as `owners_after`
2. Set up the threshold condition using the [cryptocondition library](https://github.com/bigchaindb/cryptoconditions)
3. Update the condition and hash in the transaction template

We'll illustrate this by a threshold condition where 3 out of 3 `owners_after` need to sign the transaction:

```python
# Create some new testusers
thresholduser1_priv, thresholduser1_pub = crypto.generate_key_pair()
thresholduser2_priv, thresholduser2_pub = crypto.generate_key_pair()
thresholduser3_priv, thresholduser3_pub = crypto.generate_key_pair()

# Retrieve the last transaction of testuser2
tx_unspent = b.get_owned_ids(testuser2_pub).pop()
tx_owned = b.get_transaction(tx_unspent.txid)

# Create a threshold condition with a 3 out of 3 threshold
threshold_tx = Transaction.transfer(tx_owned.to_inputs(), [[thresholduser1_pub,
                                                             thresholduser2_pub,
                                                             thresholduser3_pub]]
# Sign the transaction
threshold_tx_signed = threshold_tx.sign([testuser2_priv])

# Write the transaction
b.write_transaction(threshold_tx_signed)

# Check if the transaction is already in the bigchain
tx_threshold_retrieved = b.get_transaction(threshold_tx_signed.id)
tx_threshold_retrieved.to_dict()
```

```python
{
    "id":"0057d29ff735d91505decf5e7195ea8da675b01676165abf23ea774bbb469383",
    "transaction":{
        "conditions":[
            {
                "cid":0,
                "condition":{
                    "details":{
                        "bitmask":41,
                        "subfulfillments":[
                            {
                                "bitmask":32,
                                "public_key":"8NaGq26YMcEvj8Sc5MnqspKzFTQd1eZBAuuPDw4ERHpz",
                                "signature":None,
                                "type":"fulfillment",
                                "type_id":4,
                                "weight":1
                            },
                            {
                                "bitmask":32,
                                "public_key":"ALE9Agojob28D1fHWCxFXJwpqrYPkcsUs26YksBVj27z",
                                "signature":None,
                                "type":"fulfillment",
                                "type_id":4,
                                "weight":1
                            },
                            {
                                "bitmask":32,
                                "public_key":"Cx4jWSGci7fw6z5QyeApCijbwnMpyuhp4C1kzuFc3XrM",
                                "signature":None,
                                "type":"fulfillment",
                                "type_id":4,
                                "weight":1
                            }
                        ],
                        "threshold":3,
                        "type":"fulfillment",
                        "type_id":2
                    },
                    "uri":"cc:2:29:FoElId4TE5TU2loonT7sayXhxwcmaJVoCeIduh56Dxw:246"
                },
                "owners_after":[
                    "8NaGq26YMcEvj8Sc5MnqspKzFTQd1eZBAuuPDw4ERHpz",
                    "ALE9Agojob28D1fHWCxFXJwpqrYPkcsUs26YksBVj27z",
                    "Cx4jWSGci7fw6z5QyeApCijbwnMpyuhp4C1kzuFc3XrM"
                ]
            }
        ],
        "data":None,
        "fulfillments":[
            {
                "owners_before":[
                    "qv8DvdNG5nZHWCP5aPSqgqxAvaPJpQj19abRvFCntor"
                ],
                "fid":0,
                "fulfillment":"cf:4:DIfyalZvV_9ukoO01mxmK3nxsfAWSKYYF33XDYkbY4EbD7-_neXJJEe_tVTDc1_EqldlP_ulysFMprcW3VG4gzLzCMMpxA8kCr_pvywSFIEVYJHnI1csMvPivvBGHvkD",
                "input":{
                    "cid":0,
                    "txid":"aa11365317cb89bfdae2375bae76d6b8232008f8672507080e3766ca06976dcd"
                }
            }
        ],
        "operation":"TRANSFER",
        "timestamp":"1460981707.559401"
    },
    "version":1
}
```

The transaction can now be transferred by fulfilling the threshold condition.


#### Custom Thresholds

Additionally, the Transaction model of BigchainDB allows to create ThresholdSha256 conditions with a customizable threshold.
In our previous example, we've created a 3 out of 3 threshold condition. However, in many cases a user might want to create
a X out of Y threshold condition.

Instead of simply submitting a list `owners_after` to `Transaction.transfer`, we can submit a tuple that specifies as a second
parameter, the threshold, we'd like to specify for the ThresholdSha256 condition:

```python
# Create a ThresholdSha256 condition with a 2 out of 3 threshold.
# Note that instead of submitting a list as the second argument to
# `Transaction.transfer`, we now submit a `tuple`, where the first position is
# the `owners_after` and the second position is the `threshold`, we'd like to set.
threshold_tx = Transaction.transfer(tx_owned.to_inputs(), [([thresholduser1_pub,
                                                             thresholduser2_pub,
                                                             thresholduser3_pub], 2)]
# Sign the transaction
threshold_tx_signed = threshold_tx.sign([testuser2_priv])


# Write the transaction
b.write_transaction(threshold_tx_signed)
```


#### Transferring a Threshold Condition

We continue with transferring out custom-made 2 out of 3 ThresholdSha256 Condition.
Creating a fulfillment for it involves the following:

1. Create a transaction template that include the public key of all (nested) parties as `owners_before`
2. Signing all necessary subfulfillments (in our case only two of them)


```python
# Create a new testuser to receive
thresholduser4_priv, thresholduser4_pub = crypto.generate_key_pair()

# Retrieve the last transaction of thresholduser1_pub
tx_unspent = b.get_owned_ids(thresholduser1_pub).pop()
tx_owned = b.get_transaction(tx_unspent.id)

# Create a base template for a transfer transaction
threshold_tx_transfer = Transaction.transfer(tx_owned.to_inputs(), [[thresholduser4_pub]])

# At this point, we can unfortunately not sign partially by simply calling
# `Transaction.sign`. We're working on it though!

# Sign and add the subconditions until threshold of 2 is reached
threshold_fulfillment = threshold_tx_transfer.fulfillments[0]

subfulfillment1 = threshold_fulfillment.get_subcondition_from_vk(thresholduser1_pub)[0]
subfulfillment2 = threshold_fulfillment.get_subcondition_from_vk(thresholduser2_pub)[0]
subfulfillment3 = threshold_fulfillment.get_subcondition_from_vk(thresholduser3_pub)[0]

message = str(threshold_tx_transfer)
subfulfillment1.sign(message, thresholduser1_priv)
subfulfillment2.sign(message, thresholduser2_priv)

# Remove the unfulfilled fulfillment and readd it as a condition
threshold_fulfillment.subconditions.remove(subfulfillment3)
threshold_fulfillment.add_subcondition(subfulfillment3.condition)

# Optional validation checks
# `fulfillments_valid` checks against the previous transactions' conditions,
# which is why we have to provide them as a parameter
assert threshold_tx_transfer.fulfillments_valid(tx_owned.conditions)
assert b.validate_transaction(threshold_tx_transfer)

b.write_transaction(threshold_tx_transfer)
threshold_tx_transfer.to_dict()
```

```python
{
    "id":"a45b2340c59df7422a5788b3c462dee708a18cdf09d1a10bd26be3f31af4b8d7",
    "transaction":{
        "conditions":[
            {
                "cid":0,
                "condition":{
                    "details":{
                        "bitmask":32,
                        "public_key":"ED2pyPfsbNRTHkdMnaFkAwCSpZWRmbaM1h8fYzgRRMmc",
                        "signature":None,
                        "type":"fulfillment",
                        "type_id":4
                    },
                    "uri":"cc:4:20:xDz3NhRG-3eVzIB9sgnd99LKjOyDF-KlxWuf1TgNT0s:96"
                },
                "owners_after":[
                    "ED2pyPfsbNRTHkdMnaFkAwCSpZWRmbaM1h8fYzgRRMmc"
                ]
            }
        ],
        "data":None,
        "fulfillments":[
            {
                "owners_before":[
                    "8NaGq26YMcEvj8Sc5MnqspKzFTQd1eZBAuuPDw4ERHpz",
                    "ALE9Agojob28D1fHWCxFXJwpqrYPkcsUs26YksBVj27z",
                    "Cx4jWSGci7fw6z5QyeApCijbwnMpyuhp4C1kzuFc3XrM"
                ],
                "fid":0,
                "fulfillment":"cf:2:AQIBAwEBACcABAEgILGLuLLaNHo-KE59tkrpYmlVeucu16Eg9TcSuBqnMVwmAWABAWMABGBtiKCT8NBtSdnxJNdGYkyWqoRy2qOeNZ5UdUvpALcBD4vGRaohuVP9pQYNHpAA5GjTNNQT9CVMB67D8QL_DJsRU8ICSIVIG2P8pRqX6oia-304Xqq67wY-wLh_3IKlUg0AAQFjAARgiqYTeWkT6-jRMriCK4i8ceE2TwPys0JXgIrbw4kbwElVNnc7Aqw5c-Ts8-ymLp3d9_xTIb3-mPaV4JjhBqcobKuq2msJAjrxZOEeuYuAyC0tpduwTajOyp_Kmwzhdm8PAA",
                "input":{
                    "cid":0,
                    "txid":"0057d29ff735d91505decf5e7195ea8da675b01676165abf23ea774bbb469383"
                }
            }
        ],
        "operation":"TRANSFER",
        "timestamp":"1460981717.579700"
    },
    "version":1
}
```


### Hash-locked Conditions

A hash-lock condition on an asset is like a password condition: anyone with the secret preimage (like a password) can fulfill the hash-lock condition and transfer the asset to themselves.

Under the hood, fulfilling a hash-lock condition amounts to finding a string (a "preimage") which, when hashed, results in a given value. It's easy to verify that a given preimage hashes to the given value, but it's computationally difficult to _find_ a string which hashes to the given value. The only practical way to get a valid preimage is to get it from the original creator (possibly via intermediaries).

One possible use case is to distribute preimages as "digital vouchers." The first person to redeem a voucher will get the associated asset.

A federation node can create an asset with a hash-lock condition and no `owners_after`. Anyone who can fullfill the hash-lock condition can transfer the asset to themselves.

```python
# Create a hash-locked asset without any owners_after
hashlock_tx = Transaction.create(b.me, None, secret=b'wow, much secret!')

# The asset needs to be signed by the owner_before
hashlock_tx_signed = hashlock_tx.sign([b.me_private])

# Some validations
assert b.validate_transaction(hashlock_tx_signed) == hashlock_tx_signed

b.write_transaction(hashlock_tx_signed)
hashlock_tx_signed.to_dict()
```

```python
{
    "id":"604c520244b7ff63604527baf269e0cbfb887122f503703120fd347d6b99a237",
    "transaction":{
        "conditions":[
            {
                "cid":0,
                "condition":{
                    "uri":"cc:0:3:nsW2IiYgk9EUtsg4uBe3pBnOgRoAEX2IIsPgjqZz47U:17"
                },
                "owners_after":None
            }
        ],
        "data":None,
        "fulfillments":[
            {
                "owners_before":[
                    "FmLm6MxCABc8TsiZKdeYaZKo5yZWMM6Vty7Q1B6EgcP2"
                ],
                "fid":0,
                "fulfillment":"cf:4:21-D-LfNhIQhvY5914ArFTUGpgPKc7EVC1ZtJqqOTHGx1p9FuRr9tRfkbdqtX2MZWh7sRVUmMnwp7I1-xZbCnCkeADf69IwDHbZvNS6aTr1CpekREsV9ZG8m_wjlZiUN",
                "input":None
            }
        ],
        "operation":"CREATE",
        "timestamp":"1461250387.910102"
    },
    "version":1
}
```

In order to redeem the asset, one needs to create a fulfillment with the correct secret:

```python
from bigchaindb_common.transaction import Fulfillment, TransactionLink

hashlockuser_priv, hashlockuser_pub = crypto.generate_key_pair()

# Create hashlock fulfillment
hashlock_tx_link = TransactionLink(hashlock.txid, 0)
# Provide a wrong secret
hashlock_fulfillment = Fulfillment(cc.PreimageSha256Fulfillment(preimage=b''), None, hashlock_tx_link)

hashlock_fulfill_tx = Transaction.transfer(hashlock_fulfillment, hashlockuser_priv)
assert b.is_valid_transaction(hashlock_fulfill_tx) is False

# Provide the correct secret
hashlock_fulfillment = Fulfillment(cc.PreimageSha256Fulfillment(preimage=b'wow, much secret!'), None, hashlock_tx_link)
# Replace wrong secret, with correct one
hashlock_fulfill_tx.fulfillments[0] = hashlock_fulfillment
assert b.is_valid_transaction(hashlock_fulfill_tx) is True

b.write_transaction(hashlock_fulfill_tx)
hashlock_fulfill_tx.to_dict()
```

```python
{
    "id":"fe6871bf3ca62eb61c52c5555cec2e07af51df817723f0cb76e5cf6248f449d2",
    "transaction":{
        "conditions":[
            {
                "cid":0,
                "condition":{
                    "details":{
                        "bitmask":32,
                        "public_key":"EiqCKxnBCmmNb83qyGch48tULK9RLaEt4xFA43UVCVDb",
                        "signature":None,
                        "type":"fulfillment",
                        "type_id":4
                    },
                    "uri":"cc:4:20:y9884Md2YI_wdnGSTJGhwvFaNsKLe8sqwimqk-2JLSI:96"
                },
                "owners_after":[
                    "EiqCKxnBCmmNb83qyGch48tULK9RLaEt4xFA43UVCVDb"
                ]
            }
        ],
        "data":None,
        "fulfillments":[
            {
                "owners_before":[],
                "fid":0,
                "fulfillment":"cf:0:bXVjaCBzZWNyZXQhIHdvdyE",
                "input":{
                    "cid":0,
                    "txid":"604c520244b7ff63604527baf269e0cbfb887122f503703120fd347d6b99a237"
                }
            }
        ],
        "operation":"TRANSFER",
        "timestamp":"1461250397.944510"
    },
    "version":1
}
```

### Timeout Conditions

Timeout conditions allow assets to expire after a certain time.
The primary use case of timeout conditions is to enable [Escrow](#escrow).

The condition can only be fulfilled before the expiry time.
Once expired, the asset is lost and cannot be fulfilled by anyone.

__Note__: The timeout conditions are BigchainDB-specific and not (yet) supported by the ILP standard.

__Caveat__: The times between nodes in a BigchainDB federation may (and will) differ slightly. In this case, the majority of the nodes will decide.

```python
from bigchaindb_common.transaction import Condition

ffill = Fulfillment(cc.Ed25519Fulfillment(public_key=b.me), [b.me])

time_sleep = 12
time_expire = str(float(util.timestamp()) + time_sleep)  # 12 secs from now
condition_timeout = cc.TimeoutFulfillment(expire_time=time_expire)
cond = Condition(condition_timeout)

# Create transaction with custom timeout condition
tx_timeout = Transaction('CREATE', [ffill], [cond])

# The asset needs to be signed by the owner_before
tx_timeout_signed = tx_timeout.sign([b.me_private])

# Some validations
assert b.validate_transaction(tx_timeout_signed) == tx_timeout_signed

b.write_transaction(tx_timeout_signed)
tx_timeout_signed.to_dict()
```

```python
{
    "id":"78145396cd368f7168fb01c97aaf1df6f85244d7b544073dfcb42397dae38f90",
    "transaction":{
        "conditions":[
            {
                "cid":0,
                "condition":{
                    "details":{
                        "bitmask":9,
                        "expire_time":"1464167910.643431",
                        "type":"fulfillment",
                        "type_id":99
                    },
                    "uri":"cc:63:9:sceU_NZc3cAjAvaR1TVmgj7am5y8hJEBoqLm-tbqGbQ:17"
                },
                "owners_after":null
            }
        ],
        "data":null,
        "fulfillments":[
            {
                "owners_before":[
                    "FmLm6MxCABc8TsiZKdeYaZKo5yZWMM6Vty7Q1B6EgcP2"
                ],
                "fid":0,
                "fulfillment":null,
                "input":null
            }
        ],
        "operation":"CREATE",
        "timestamp":"1464167898.643353"
    },
    "version":1
}
```

The following demonstrates that the transaction invalidates once the timeout occurs:

```python
from time import sleep

# Create a timeout fulfillment tx
tx_timeout_transfer = Transaction.transfer(tx_timeout.to_inputs(), testuser1_pub)

# No need to sign transaction, like with hashlocks

# Small test to see the state change
for i in range(time_sleep - 4):
    tx_timeout_valid = b.is_valid_transaction(tx_timeout_transfer) == tx_timeout_transfer
    seconds_to_timeout = int(float(time_expire) - float(util.timestamp()))
    print('tx_timeout valid: {} ({}s to timeout)'.format(tx_timeout_valid, seconds_to_timeout))
    sleep(1)
```

If you were fast enough, you should see the following output:

```python
tx_timeout valid: True (3s to timeout)
tx_timeout valid: True (2s to timeout)
tx_timeout valid: True (1s to timeout)
tx_timeout valid: True (0s to timeout)
tx_timeout valid: False (0s to timeout)
tx_timeout valid: False (-1s to timeout)
tx_timeout valid: False (-2s to timeout)
tx_timeout valid: False (-3s to timeout)
```

## Escrow

Escrow is a mechanism for conditional release of assets.

This means that the assets are locked up by a trusted party until an `execute` condition is presented. In order not to tie up the assets forever, the escrow foresees an `abort` condition, which is typically an expiry time.

BigchainDB and cryptoconditions provides escrow out-of-the-box, without the need of a trusted party.

A threshold condition is used to represent the escrow, since BigchainDB transactions cannot have a _pending_ state.

<p align="center">
  <img width="70%" height="70%" src ="../_static/tx_escrow_execute_abort.png" />
</p>

The logic for switching between `execute` and `abort` conditions is conceptually simple:

```python
if timeout_condition.validate(utcnow()):
    execute_fulfillment.validate(msg) is True
    abort_fulfillment.validate(msg) is False
else:
    execute_fulfillment.validate(msg) is False
    abort_fulfillment.validate(msg) is True
```

The above switch can be implemented as follows using threshold cryptoconditions:

<p align="center">
  <img width="100%" height="100%" src ="../_static/cc_escrow_execute_abort.png" />
</p>

The inverted timeout is denoted by a -1 threshold, which negates the output of the fulfillment.

```python
inverted_fulfillment.validate(msg) == not fulfillment.validate(msg)
```

__Note__: inverted thresholds are BigchainDB-specific and not supported by the ILP standard.
The main reason is that it's difficult to tell whether the fulfillment was negated, or just omitted.


The following code snippet shows how to create an escrow condition:

```python
# Retrieve the last transaction of testuser2_pub (or create a new asset)
tx_unspent = b.get_owned_ids(testuser2_pub).pop()
tx_owned = b.get_transaction(tx_unspent.id)

# Create a base template with the execute and abort address
ffill = Fulfillment(cc.Ed25519Fulfillment(public_key=testuser2_pub), [testuser2_pub])
tx_escrow = Transaction('TRANSFER', [ffill])

# Set expiry time - the execute address needs to fulfill before expiration
time_sleep = 12
time_expire = str(float(util.timestamp()) + time_sleep)  # 12 secs from now

# Create the escrow and timeout condition
condition_escrow = cc.ThresholdSha256Fulfillment(threshold=1)  # OR Gate
condition_timeout = cc.TimeoutFulfillment(expire_time=time_expire)  # only valid if now() <= time_expire
condition_timeout_inverted = cc.InvertedThresholdSha256Fulfillment(threshold=1)
condition_timeout_inverted.add_subfulfillment(condition_timeout)  # invert the timeout condition

# Create the execute branch
condition_execute = cc.ThresholdSha256Fulfillment(threshold=2)  # AND gate
condition_execute.add_subfulfillment(cc.Ed25519Fulfillment(public_key=testuser1_pub))  # execute address
condition_execute.add_subfulfillment(condition_timeout)  # federation checks on expiry
condition_escrow.add_subfulfillment(condition_execute)

# Create the abort branch
condition_abort = cc.ThresholdSha256Fulfillment(threshold=2)  # AND gate
condition_abort.add_subfulfillment(cc.Ed25519Fulfillment(public_key=testuser2_pub))  # abort address
condition_abort.add_subfulfillment(condition_timeout_inverted)
condition_escrow.add_subfulfillment(condition_abort)

cond = Condition(condition_escrow, [testuser2_pub, testuser1_pub])
# Add the condition to our transaction template
tx_escrow.add_condition(cond)

# The asset needs to be signed by the owner_before
tx_escrow_signed = tx_escrow.sign([testuser2_priv])

# Some validations
assert b.validate_transaction(tx_escrow_signed) == tx_escrow_signed

b.write_transaction(tx_escrow_signed)
tx_escrow_signed.to_dict()
```

```python
{
    "id":"1a281da2b9bc3d2beba92479058d440de3353427fd64045a61737bad0d0c809c",
    "transaction":{
        "conditions":[
            {
                "cid":0,
                "condition":{
                    "details":{
                        "bitmask":41,
                        "subfulfillments":[
                            {
                                "bitmask":41,
                                "subfulfillments":[
                                    {
                                        "bitmask":32,
                                        "public_key":"qv8DvdNG5nZHWCP5aPSqgqxAvaPJpQj19abRvFCntor",
                                        "signature":null,
                                        "type":"fulfillment",
                                        "type_id":4,
                                        "weight":1
                                    },
                                    {
                                        "bitmask":9,
                                        "expire_time":"1464242352.227917",
                                        "type":"fulfillment",
                                        "type_id":99,
                                        "weight":1
                                    }
                                ],
                                "threshold":2,
                                "type":"fulfillment",
                                "type_id":2,
                                "weight":1
                            },
                            {
                                "bitmask":41,
                                "subfulfillments":[
                                    {
                                        "bitmask":32,
                                        "public_key":"BwuhqQX8FPsmqYiRV2CSZYWWsSWgSSQQFHjqxKEuqkPs",
                                        "signature":null,
                                        "type":"fulfillment",
                                        "type_id":4,
                                        "weight":1
                                    },
                                    {
                                        "bitmask":9,
                                        "subfulfillments":[
                                            {
                                                "bitmask":9,
                                                "expire_time":"1464242352.227917",
                                                "type":"fulfillment",
                                                "type_id":99,
                                                "weight":1
                                            }
                                        ],
                                        "threshold":1,
                                        "type":"fulfillment",
                                        "type_id":98,
                                        "weight":1
                                    }
                                ],
                                "threshold":2,
                                "type":"fulfillment",
                                "type_id":2,
                                "weight":1
                            }
                        ],
                        "threshold":1,
                        "type":"fulfillment",
                        "type_id":2
                    },
                    "uri":"cc:2:29:sg08ERtppQrGxot7mu7XMdNkZTc29xCbWE1r8DgxuL8:181"
                },
                "owners_after":[
                    "BwuhqQX8FPsmqYiRV2CSZYWWsSWgSSQQFHjqxKEuqkPs",
                    "qv8DvdNG5nZHWCP5aPSqgqxAvaPJpQj19abRvFCntor"
                ]
            }
        ],
        "data":null,
        "fulfillments":[
            {
                "owners_before":[
                    "qv8DvdNG5nZHWCP5aPSqgqxAvaPJpQj19abRvFCntor"
                ],
                "fid":0,
                "fulfillment":"cf:4:B6VAa7KAMD1v-pyvDx9RuBLb6l2Qs3vhucgXqzU_RbuRucOp6tNY8AoNMoC-HAOZBJSnHXZsdJ7pLCZ6aDTwUHXf0zxyLaCgy1NpES3h8qcuxbfv4Nchw3BtUcVSY3AM",
                "input":{
                    "cid":1,
                    "txid":"d3f5e78f6d4346466178745f1c01cbcaf1c1dce1932a16cd653051b16ee29bac"
                }
            }
        ],
        "operation":"TRANSFER",
        "timestamp":"1464242340.227787"
    },
    "version":1
}
```

At any given moment `testuser1` and `testuser2` can try to fulfill the `execute` and `abort` branch respectively.
Whether the fulfillment will validate depends on the timeout condition.

We'll illustrate this by example.

In the case of `testuser1`, we create the `execute` fulfillment:

```python
# Create a basic condition
cond = Condition.generate([testuser1_pub])

# Create a base template for execute fulfillment
tx_escrow_execute = Transaction('TRANSFER', [], [cond])

# Get the Escrow cryptocondition
escrow_fulfillment = tx_escrow.condition[0].fulfillment

subfulfillment_testuser1 = escrow_fulfillment.get_subcondition_from_vk(testuser1_pub)[0]
subfulfillment_testuser2 = escrow_fulfillment.get_subcondition_from_vk(testuser2_pub)[0]
subfulfillment_timeout = escrow_fulfillment.subconditions[0]['body'].subconditions[1]['body']
subfulfillment_timeout_inverted = escrow_fulfillment.subconditions[1]['body'].subconditions[1]['body']

# Clear the subconditions of the escrow fulfillment
escrow_fulfillment.subconditions = []

# Fulfill the execute branch
fulfillment_execute = cc.ThresholdSha256Fulfillment(threshold=2)
subfulfillment_testuser1.sign(str(tx_escrow_execute), crypto.SigningKey(testuser1_priv))
fulfillment_execute.add_subfulfillment(subfulfillment_testuser1)
fulfillment_execute.add_subfulfillment(subfulfillment_timeout)
escrow_fulfillment.add_subfulfillment(fulfillment_execute)

# Do not fulfill the abort branch
condition_abort = cc.ThresholdSha256Fulfillment(threshold=2)
condition_abort.add_subfulfillment(subfulfillment_testuser2)
condition_abort.add_subfulfillment(subfulfillment_timeout_inverted)
escrow_fulfillment.add_subcondition(condition_abort.condition)  # Adding only the condition here

# Update the execute transaction with the fulfillment
tx_unspent = TransactionLink(tx_escrow_signed, 0)
ffill = Fulfillment(escrow_fulfillment, [testuser2_pub, testuser1_pub], tx_unspent)
tx_escrow_execute.add_fulfillment(ffill)
```

In the case of `testuser2`, we create the `abort` fulfillment:

```python
# Create a basic condition
cond = Condition.generate([testuser2_pub])

# Create a base template for abort fulfillment
tx_escrow_abort = Transaction('TRANSFER', [], [cond])

# Get the Escrow cryptocondition
escrow_fulfillment = tx_escrow.condition[0].fulfillment

subfulfillment_testuser1 = escrow_fulfillment.get_subcondition_from_vk(testuser1_pub)[0]
subfulfillment_testuser2 = escrow_fulfillment.get_subcondition_from_vk(testuser2_pub)[0]
subfulfillment_timeout = escrow_fulfillment.subconditions[0]['body'].subconditions[1]['body']
subfulfillment_timeout_inverted = escrow_fulfillment.subconditions[1]['body'].subconditions[1]['body']

# Clear the subconditions of the escrow fulfillment
escrow_fulfillment.subconditions = []

# Do not fulfill the execute branch
condition_execute = cc.ThresholdSha256Fulfillment(threshold=2)
condition_execute.add_subfulfillment(subfulfillment_testuser1)
condition_execute.add_subfulfillment(subfulfillment_timeout)
escrow_fulfillment.add_subcondition(condition_execute.condition) # Adding only the condition here

# Fulfill the abort branch
fulfillment_abort = cc.ThresholdSha256Fulfillment(threshold=2)
subfulfillment_testuser2.sign(str(tx_escrow_abort), crypto.SigningKey(testuser2_priv))
fulfillment_abort.add_subfulfillment(subfulfillment_testuser2)
fulfillment_abort.add_subfulfillment(subfulfillment_timeout_inverted)
escrow_fulfillment.add_subfulfillment(fulfillment_abort)

# Update the abort transaction with the fulfillment
tx_unspent = TransactionLink(tx_escrow_signed, 0)
ffill = Fulfillment(escrow_fulfillment, [testuser2_pub, testuser1_pub], tx_unspent)
tx_escrow_abort.add_fulfillment(ffill)
```

The following demonstrates that the transaction validation switches once the timeout occurs:

```python
for i in range(time_sleep - 4):
    valid_execute = b.is_valid_transaction(tx_escrow_execute) == tx_escrow_execute
    valid_abort = b.is_valid_transaction(tx_escrow_abort) == tx_escrow_abort

    seconds_to_timeout = int(float(time_expire) - float(util.timestamp()))
    print('tx_execute valid: {} - tx_abort valid {} ({}s to timeout)'.format(valid_execute, valid_abort, seconds_to_timeout))
    sleep(1)
```

If you execute in a timely fashion, you should see the following:

```python
tx_execute valid: True - tx_abort valid False (3s to timeout)
tx_execute valid: True - tx_abort valid False (2s to timeout)
tx_execute valid: True - tx_abort valid False (1s to timeout)
tx_execute valid: True - tx_abort valid False (0s to timeout)
tx_execute valid: False - tx_abort valid True (0s to timeout)
tx_execute valid: False - tx_abort valid True (-1s to timeout)
tx_execute valid: False - tx_abort valid True (-2s to timeout)
tx_execute valid: False - tx_abort valid True (-3s to timeout)
```

Of course, when the `execute` transaction was accepted in-time by bigchaindb, then writing the `abort` transaction after expiry will yield a `Doublespend` error.
