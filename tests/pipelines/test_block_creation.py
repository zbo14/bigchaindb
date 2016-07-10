import random

import rethinkdb as r

from bigchaindb.pipelines import block
from pipes import Pipe


def test_filter_by_assignee(b, user_vk):
    block_maker = block.Block()

    tx = b.create_transaction(b.me, user_vk, None, 'CREATE')
    tx = b.sign_transaction(tx, b.me_private)
    tx['assignee'] = b.me

    # filter_tx has side effects on the `tx` instance by popping 'assignee'
    assert block_maker.filter_tx(tx) == tx

    tx = b.create_transaction(b.me, user_vk, None, 'CREATE')
    tx = b.sign_transaction(tx, b.me_private)
    tx['assignee'] = 'nobody'

    assert block_maker.filter_tx(tx) is None


def test_validate_transactions(b, user_vk):
    block_maker = block.Block()

    tx = b.create_transaction(b.me, user_vk, None, 'CREATE')
    tx = b.sign_transaction(tx, b.me_private)
    tx['id'] = 'a' * 64

    assert block_maker.validate_tx(tx) is None

    tx = b.create_transaction(b.me, user_vk, None, 'CREATE')
    tx = b.sign_transaction(tx, b.me_private)

    assert block_maker.validate_tx(tx) == tx


def test_write_block(b, user_vk):
    block_maker = block.Block()

    # make sure that we only have the genesis block in bigchain
    r.table('bigchain').delete().run(b.conn)
    b.create_genesis_block()

    # create transactions
    for i in range(100):
        tx = b.create_transaction(b.me, user_vk, None, 'CREATE')
        tx = b.sign_transaction(tx, b.me_private)
        block_maker.create(tx)

    # force the output
    block_doc = block_maker.create(None, timeout=True)

    assert len(block_doc['block']['transactions']) == 100


def test_prefeed(b, user_vk):
    # make sure that there are no transactions in the backlog
    r.table('backlog').delete().run(b.conn)

    # create and write transactions to the backlog
    for i in range(100):
        tx = b.create_transaction(b.me, user_vk, None, 'CREATE')
        tx = b.sign_transaction(tx, b.me_private)
        b.write_transaction(tx)

    backlog = block.initial()

    assert len(list(backlog)) == 100


def test_block_creation(b, user_vk):
    # create transactions and randomly assigne them
    inpipe = Pipe()
    outpipe = Pipe()

    pipeline = block.create_pipeline()
    pipeline.setup(indata=inpipe, outdata=outpipe)

    count_assigned_to_me = 0
    for i in range(100):
        tx = b.create_transaction(b.me, user_vk, None, 'CREATE')
        tx = b.sign_transaction(tx, b.me_private)
        assignee = random.choice([b.me, 'aaa', 'bbb', 'ccc'])
        tx['assignee'] = assignee
        inpipe.put(tx)
        if assignee == b.me:
            count_assigned_to_me += 1

    pipeline.start()
    pipeline.poison_pill()
    pipeline.join()

    block_doc = outpipe.get()

    assert len(block_doc['block']['transactions']) == count_assigned_to_me

