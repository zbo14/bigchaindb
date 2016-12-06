from bigchaindb.common.schema import validate_transaction_schema

def test_inputs_outputs_spec():

    transfer = {
        "id": "2cae047109585d2f399b28ac6685078dd2a14b3e9ed0b74e5608aee61fac2005",
        "operation": "TRANSFER",
        "asset": {
            "id": "99a15f79-850d-45d6-9abb-91741cd0bc08"
        },
        "inputs": [
            {
                "spends": {
                    "idx": 0,
                    "txid": "0fd6ae9744f88303f7a473e8f3de1027fb1130af49c7bc85730cdc557abb4415"
                },
                "unlocking_script": "cf:4:__Y_Um6H73iwPe6ejWXEw930SQhqVGjtAHTXilPp0P1KyUuqP0PrHPi37sSPKVtI0xN2SjSWBHFxVn-2qTDQrgFYSHSCbALBJcA5dwvSxut49TA7koXx0bhWdxMjvhkO",
            }
        ],
        "outputs": [
            {
                "amount": 1,
                "language": "cc",
                "locking_script": {
                    "details": {
                        "bitmask": 32,
                        "type_id": 4,
                        "signature": None,
                        "type": "fulfillment",
                        "public_key": "JEAkEJqLbbgDRAtMm8YAjGp759Aq2qTn9eaEHUj2XePE"
                    },
                    "uri": "cc:4:20:__Y_Um6H73iwPe6ejWXEw930SQhqVGjtAHTXilPp0P0:96"
                },
                "public_keys": [
                    "JEAkEJqLbbgDRAtMm8YAjGp759Aq2qTn9eaEHUj2XePE"
                ]
            }
        ],
        "metadata": None,
        "version": 1
    }

    validate_transaction_schema(transfer)
