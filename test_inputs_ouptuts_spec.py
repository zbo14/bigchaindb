from bigchaindb.common.schema import validate_transaction_schema

def test_inputs_outputs_spec():

    transfer = {
        "id": "2cae047109585d2f399b28ac6685078dd2a14b3e9ed0b74e5608aee61fac2005",
        "operation": "TRANSFER",
        "asset": {
            "id": "99a15f79-850d-45d6-9abb-91741cd0bc08"
        },
        "fulfillments": [
            {
                "fid": 0,
                "input": {
                    "cid": 0,
                    "txid": "346cd85088c30ac5e0b6beda000adb15e53a74b0f974ce98711e2c2c092093f2"
                },
                "fulfillment": "cf:4:__Y_Um6H73iwPe6ejWXEw930SQhqVGjtAHTXilPp0P3D7mHJpq4bGv8WwQu6bgl4m3Kjy0Zagi30RR-K6QzWUyWtO-ak3I69EdgdqygaAIEcJAVNrCWWDA_aamC7kZ8B",
                "owners_before": [
                    "JEAkEJqLbbgDRAtMm8YAjGp759Aq2qTn9eaEHUj2XePE"
                ]
            }
        ],
        "conditions": [
            {
                "amount": 1,
                "cid": 0,
                "condition": {
                    "details": {
                        "bitmask": 32,
                        "type_id": 4,
                        "signature": None,
                        "type": "fulfillment",
                        "public_key": "JEAkEJqLbbgDRAtMm8YAjGp759Aq2qTn9eaEHUj2XePE"
                    },
                    "uri": "cc:4:20:__Y_Um6H73iwPe6ejWXEw930SQhqVGjtAHTXilPp0P0:96"
                },
                "owners_after": [
                    "JEAkEJqLbbgDRAtMm8YAjGp759Aq2qTn9eaEHUj2XePE"
                ]
            }
        ],
        "metadata": None,
        "version": 1
    }

    validate_transaction_schema(transfer)
