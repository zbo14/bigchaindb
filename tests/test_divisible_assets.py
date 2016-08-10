import pytest


def test_amount_schema_validation(b):
    # `amount` needs to be an integer greater then 0

    # check amount is not int
    tx = b.create_transaction(b.me, b.me, None, 'CREATE', amount='1')
    tx_signed = b.sign_transaction(tx, b.me_private)
    with pytest.raises(ValueError):
        b.validate_transaction(tx_signed)

    # check value is greater then zero
    tx = b.create_transaction(b.me, b.me, None, 'CREATE', amount=0)
    tx_signed = b.sign_transaction(tx, b.me_private)
    with pytest.raises(ValueError):
        b.validate_transaction(tx_signed)
    tx = b.create_transaction(b.me, b.me, None, 'CREATE', amount=-1)
    tx_signed = b.sign_transaction(tx, b.me_private)
    with pytest.raises(ValueError):
        b.validate_transaction(tx_signed)

    # check that it correctly creates a valid transaction with default values
    tx = b.create_transaction(b.me, b.me, None, 'CREATE')
    tx_signed = b.sign_transaction(tx, b.me_private)
    assert b.validate_transaction(tx_signed) == tx_signed
    assert tx_signed['transaction']['conditions'][0]['amount'] == 1
