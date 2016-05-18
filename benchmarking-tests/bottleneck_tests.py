import time
import multiprocessing as mp
import rethinkdb as r

from bigchaindb import Bigchain


def validate_transactions_single_core():
    b = Bigchain()
    tx = b.create_transaction(b.me, b.me, None, 'CREATE')
    tx_signed = b.sign_transaction(tx, b.me_private)

    t_start = time.time()
    for i in range(1000000):
        b.validate_transaction(tx_signed)
    t_elapsed = time.time() - t_start

    print('validate_transasctions_single_core: {} s'.format(t_elapsed))


def validate_transactions_multicore():
    b = Bigchain()
    tx = b.create_transaction(b.me, b.me, None, 'CREATE')
    tx_signed = b.sign_transaction(tx, b.me_private)

    t_start = time.time()
    with mp.Pool() as pool:
        pool.map(b.validate_transaction, [tx_signed for _ in range(1000000)])
    t_elapsed = time.time() - t_start

    print('validate_transasctions_multicore: {} s'.format(t_elapsed))


def filter_transactions_single_core():
    pass


def filter_transactions_multicore():
    pass


def write_blocks_single_core():
    pass


def _write_blocks_worker(block):
    b = Bigchain()
    while True:
        b.write_block(block)


def write_blocks_multicore():
    b = Bigchain()
    tx = b.create_transaction(b.me, b.me, None, 'CREATE')
    tx_signed = b.sign_transaction(tx, b.me_private)

    block = b.create_block([tx_signed] * 1000)
    block.pop('id')

    # procs = []
    # for _ in range(2):
    #     procs.append(mp.Process(target=_write_blocks_worker, args=(block,)))
#
    # for p in procs:
    #     p.start()

    with mp.Pool(processes=32) as pool:
        pool.map(_write_blocks_worker, [block] * 32)


if __name__ == '__main__':
    # validate_transactions_multicore()
    write_blocks_multicore()
