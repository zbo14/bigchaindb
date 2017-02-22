import time

import pytest

pytestmark = [pytest.mark.bdb, pytest.mark.usefixtures('processes')]


def test_fast_double_create(b, user_pk):
    from bigchaindb.models import Transaction
    from bigchaindb.backend.query import count_blocks
    tx = Transaction.create([b.me], [([user_pk], 1)],
                            metadata={'test': 'test'}).sign([b.me_private])

    # write everything fast
    b.write_transaction(tx)
    b.write_transaction(tx)

    time.sleep(2)
    tx_returned = b.get_transaction(tx.id)

    # test that the tx can be queried
    assert tx_returned == tx
    # test the transaction appears only once
    last_voted_block = b.get_last_voted_block()
    assert len(last_voted_block.transactions) == 1
    assert count_blocks(b.connection) == 2


def test_double_create(b, user_pk):
    from bigchaindb.models import Transaction
    from bigchaindb.backend.query import count_blocks
    tx = Transaction.create([b.me], [([user_pk], 1)],
                            metadata={'test': 'test'}).sign([b.me_private])

    b.write_transaction(tx)
    time.sleep(2)
    b.write_transaction(tx)
    time.sleep(2)
    tx_returned = b.get_transaction(tx.id)

    # test that the tx can be queried
    assert tx_returned == tx
    # test the transaction appears only once
    last_voted_block = b.get_last_voted_block()
    assert len(last_voted_block.transactions) == 1
    assert count_blocks(b.connection) == 2


@pytest.mark.usefixtures('inputs')
def test_get_owned_ids_works_after_double_spend(b, user_pk, user_sk):
    """ Test for #633 https://github.com/bigchaindb/bigchaindb/issues/633 """
    from bigchaindb.common.exceptions import DoubleSpend
    from bigchaindb.models import Transaction
    input_valid = b.get_owned_ids(user_pk).pop()
    input_valid = b.get_transaction(input_valid.txid)
    tx_valid = Transaction.transfer(input_valid.to_inputs(),
                                    [([user_pk], 1)],
                                    input_valid.id,
                                    {'1': 1}).sign([user_sk])

    # write the valid tx and wait for voting/block to catch up
    b.write_transaction(tx_valid)
    time.sleep(2)

    # doesn't throw an exception
    b.get_owned_ids(user_pk)

    # create another transaction with the same input
    tx_double_spend = Transaction.transfer(input_valid.to_inputs(),
                                           [([user_pk], 1)],
                                           input_valid.id,
                                           {'2': 2}).sign([user_sk])

    # write the double spend tx
    b.write_transaction(tx_double_spend)
    time.sleep(2)

    # still doesn't throw an exception
    b.get_owned_ids(user_pk)
    with pytest.raises(DoubleSpend):
        b.validate_transaction(tx_double_spend)


def test_hyperchain_double_inclusion(b):
    from bigchaindb.models import Transaction
    from bigchaindb.common.crypto import generate_key_pair

    dimi = generate_key_pair()
    mark = generate_key_pair()

    def wait_tx(txid):
        while True:
            _, status = b.get_transaction(txid, include_status=True)
            if status in ('valid', 'invalid'):
                break
            time.sleep(0.1)

    for i in [0, 1]:
        tx = Transaction.create([dimi[1]], [([dimi[1]], 1)]).sign([dimi[0]])

        b.write_transaction(tx)
        wait_tx(tx.id)

        spend = Transaction.transfer(tx.to_inputs(), [([mark[1]], 1)],
                                     tx.id).sign([dimi[0]])

        b.write_transaction(spend)
        wait_tx(spend.id)

        b.write_transaction(spend)
        wait_tx(spend.id)

        assert [own.to_dict() for own in b.get_owned_ids(dimi[1])] == []
        assert [own.to_dict() for own in b.get_owned_ids(mark[1])] == \
               [{'txid': spend.id, 'output': 0}]
