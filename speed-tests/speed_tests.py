import time
import json
import multiprocessing as mp

import rapidjson
from line_profiler import LineProfiler

import bigchaindb


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


def speedtest_serialize_block_json():
    # create a block
    b = bigchaindb.Bigchain()
    tx = b.create_transaction(b.me, b.me, None, 'CREATE')
    tx_signed = b.sign_transaction(tx, b.me_private)
    block = b.create_block([tx_signed] * 1000)

    time_start = time.time()
    for _ in range(1000):
        _ = json.dumps(block, skipkeys=False, ensure_ascii=False, sort_keys=True)
    time_elapsed = time.time() - time_start

    print('speedtest_serialize_block_json: {} s'.format(time_elapsed))


def speedtest_serialize_block_rapidjson():
    # create a block
    b = bigchaindb.Bigchain()
    tx = b.create_transaction(b.me, b.me, None, 'CREATE')
    tx_signed = b.sign_transaction(tx, b.me_private)
    block = b.create_block([tx_signed] * 1000)

    time_start = time.time()
    for _ in range(1000):
        _ = rapidjson.dumps(block, skipkeys=False, ensure_ascii=False, sort_keys=True)
    time_elapsed = time.time() - time_start

    print('speedtest_serialize_block_rapidjson: {} s'.format(time_elapsed))


def speedtest_deserialize_block_json():
    # create a block
    b = bigchaindb.Bigchain()
    tx = b.create_transaction(b.me, b.me, None, 'CREATE')
    tx_signed = b.sign_transaction(tx, b.me_private)
    block = b.create_block([tx_signed] * 1000)
    block_serialized = json.dumps(block, skipkeys=False, ensure_ascii=False, sort_keys=True)

    time_start = time.time()
    for _ in range(1000):
        _ = json.loads(block_serialized)
    time_elapsed = time.time() - time_start

    print('speedtest_deserialize_block_json: {} s'.format(time_elapsed))


def speedtest_deserialize_block_rapidjson():
    # create a block
    b = bigchaindb.Bigchain()
    tx = b.create_transaction(b.me, b.me, None, 'CREATE')
    tx_signed = b.sign_transaction(tx, b.me_private)
    block = b.create_block([tx_signed] * 1000)
    block_serialized = rapidjson.dumps(block, skipkeys=False, ensure_ascii=False, sort_keys=True)

    time_start = time.time()
    for _ in range(1000):
        _ = rapidjson.loads(block_serialized)
    time_elapsed = time.time() - time_start

    print('speedtest_deserialize_block_rapidjson: {} s'.format(time_elapsed))


def _queue_writer_worker(queue, tx, n):
    for _ in range(n):
        queue.put(tx)
    queue.cancel_join_thread()


def _queue_reader_worker(queue, tx, n):
    for i in range(n):
        print('reading from queue', i)
        queue.get(tx)
    queue.cancel_join_thread()



def speedtest_write_to_queue_single_core():
    # create a transaction
    b = bigchaindb.Bigchain()
    tx = b.create_transaction(b.me, b.me, None, 'CREATE')
    tx_signed = b.sign_transaction(tx, b.me_private)

    # create queue
    queue = mp.Queue()

    time_start = time.time()
    for _ in range(1000):
        queue.put(tx_signed)
    time_elapsed = time.time() - time_start

    print('speedtest_write_to_queue_single_core: {} s'.format(time_elapsed))


def speedtest_write_to_queue_multicore():
    # create a transaction
    b = bigchaindb.Bigchain()
    tx = b.create_transaction(b.me, b.me, None, 'CREATE')
    tx_signed = b.sign_transaction(tx, b.me_private)
    num_transactions = 1000000

    # create queue
    queue = mp.Queue()

    # create the processes
    processes = []
    for _ in range(mp.cpu_count()):
        processes.append(mp.Process(target=_queue_writer_worker,
                                    args=(queue, tx_signed, num_transactions // mp.cpu_count())))

    time_start = time.time()
    for p in processes:
        p.start()

    for p in processes:
        p.join()
    time_elapsed = time.time() - time_start

    print('speedtest_write_to_queue_multicore: {} s'.format(time_elapsed))


def speedtest_read_queue_single_core():
    # create a transaction
    b = bigchaindb.Bigchain()
    tx = b.create_transaction(b.me, b.me, None, 'CREATE')
    tx_signed = b.sign_transaction(tx, b.me_private)

    # create queue
    queue = mp.Queue()
    for _ in range(1000):
        queue.put(tx_signed)

    time_start = time.time()
    for _ in range(1000):
        queue.get()
    time_elapsed = time.time() - time_start

    print('speedtest_read_queue_single_core: {} s'.format(time_elapsed))


def speedtest_read_queue_multicore():
    # create a transaction
    b = bigchaindb.Bigchain()
    tx = b.create_transaction(b.me, b.me, None, 'CREATE')
    tx_signed = b.sign_transaction(tx, b.me_private)
    num_transactions = 10000

    # create queue
    queue = mp.Queue()
    processes = []
    for _ in range(mp.cpu_count()):
        processes.append(mp.Process(target=_queue_writer_worker,
                                    args=(queue, tx_signed, num_transactions // mp.cpu_count())))
    for p in processes:
        p.start()
    for p in processes:
        p.join()

    print('finished filling queue')

    # create the processes
    processes = []
    for _ in range(mp.cpu_count()):
        processes.append(mp.Process(target=_queue_reader_worker,
                                    args=(queue, tx_signed, num_transactions // mp.cpu_count())))

    time_start = time.time()
    for p in processes:
        p.start()
    print('started reading transactions')
    for p in processes:
        p.join()

    print('finished reading transactions')
    time_elapsed = time.time() - time_start

    print('speedtest_read_queue_multicore: {} s'.format(time_elapsed))


if __name__ == '__main__':
    speedtest_validate_transaction()
    speedtest_serialize_block_json()
    speedtest_serialize_block_rapidjson()
    speedtest_deserialize_block_json()
    speedtest_deserialize_block_rapidjson()
