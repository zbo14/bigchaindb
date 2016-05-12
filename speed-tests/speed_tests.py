import multiprocessing as mp
import uuid

from line_profiler import LineProfiler

import bigchaindb
from bigchaindb.block import Block


def speedtest_validate_transaction():
    # create a transaction
    b = bigchaindb.Bigchain()
    tx = b.create_transaction(b.me, b.me, None, 'CREATE')
    tx_signed = b.sign_transaction(tx, b.me_private)

    # setup the profiler
    profiler = LineProfiler()
    profiler.enable_by_count()
    profiler.add_function(bigchaindb.Bigchain.validate_transaction)

    # validate_transaction 1000 times
    for i in range(1000):
        b.validate_transaction(tx_signed)

    profiler.print_stats()


def speedtest_block_filter():
    # create a transaction
    b = bigchaindb.Bigchain()
    tx = b.create_transaction(b.me, b.me, None, 'CREATE')
    tx_signed = b.sign_transaction(tx, b.me_private)
    # assign the transaction
    tx_signed.update({'assignee': b.me})

    # create a queue
    queue = mp.Queue()
    # fill the queue with 1000 transactions
    for i in range(1000):
        queue.put(tx_signed)
    queue.put('stop')

    # setup block process
    block = Block(None)
    block.q_new_transaction = queue

    # setup profiler
    profiler = LineProfiler()
    profiler.enable_by_count()
    profiler.add_function(block.filter_by_assignee)

    # filter 1000 transactions
    block.filter_by_assignee()

    profiler.print_stats()


def speedtest_block_validate_transactions():
    # create a transaction
    b = bigchaindb.Bigchain()
    tx = b.create_transaction(b.me, b.me, None, 'CREATE')
    tx_signed = b.sign_transaction(tx, b.me_private)

    # create a queue
    queue = mp.Queue()
    # fill the queue with 1000 transactions
    for i in range(1000):
        queue.put(tx_signed)
    queue.put('stop')

    # setup block process
    block = Block(None)
    block.q_tx_to_validate = queue

    # setup profiler
    profiler = LineProfiler()
    profiler.enable_by_count()
    profiler.add_function(block.validate_transactions)

    # validate 1000 transactions
    block.validate_transactions()

    profiler.print_stats()


def speedtest_block_create_blocks():
    # create a transaction
    b = bigchaindb.Bigchain()
    tx = b.create_transaction(b.me, b.me, None, 'CREATE')
    tx_signed = b.sign_transaction(tx, b.me_private)

    # create a queue
    queue = mp.Queue()
    # fill the queue with 1000 transactions
    for i in range(1000):
        queue.put(tx_signed)
    queue.put('stop')

    # setup block process
    block = Block(None)
    block.q_tx_validated = queue

    # setup profiler
    profiler = LineProfiler()
    profiler.enable_by_count()
    profiler.add_function(block.create_blocks)

    # create blocks
    block.create_blocks()

    profiler.print_stats()


def speedtest_block_write_blocks():
    # create a transaction
    b = bigchaindb.Bigchain()
    tx = b.create_transaction(b.me, b.me, None, 'CREATE')
    tx_signed = b.sign_transaction(tx, b.me_private)

    # create a queue
    queue = mp.Queue()
    # fill the queue with 1 blocks
    queue.put(b.create_block([tx_signed] * 1000))
    queue.put('stop')

    # setup block process
    block = Block(None)
    block.q_block = queue

    # setup profiler
    profiler = LineProfiler()
    profiler.enable_by_count()
    profiler.add_function(block.write_blocks)
    profiler.add_function(b.write_block)

    # create blocks
    block.write_blocks()

    profiler.print_stats()


def speedtest_block_delete_transactions():
    # create a transaction
    b = bigchaindb.Bigchain()
    tx = b.create_transaction(b.me, b.me, None, 'CREATE')
    tx_signed = b.sign_transaction(tx, b.me_private)

    # create a queue
    queue = mp.Queue()
    # write 1000 transactions to the backlog with random ids
    for i in range(1000):
        random_id = str(uuid.uuid4())
        tx_signed['id'] = random_id
        b.write_transaction(tx_signed)
        queue.put(random_id)
    queue.put('stop')

    # setup block process
    block = Block(None)
    block.q_tx_delete = queue

    # setup profiler
    profiler = LineProfiler()
    profiler.enable_by_count()
    profiler.add_function(block.delete_transactions)

    # create blocks
    block.delete_transactions()

    profiler.print_stats()


if __name__ == '__main__':
    speedtest_validate_transaction()
