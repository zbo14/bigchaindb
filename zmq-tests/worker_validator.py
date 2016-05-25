import sys
import zmq
import rapidjson
import multiprocessing as mp

from bigchaindb import Bigchain


def validate_transactions(name):
    print('Starting worker-{}'.format(name))
    context = zmq.Context()
    b = Bigchain()

    # socket to receive messages on
    receiver = context.socket(zmq.PULL)
    receiver.connect("tcp://localhost:5557")

    # socket to send messages to
    sender = context.socket(zmq.PUSH)
    sender.connect("tcp://localhost:5558")

    # Process tasks forever
    while True:
        msg = receiver.recv()
        tx = rapidjson.loads(msg)
        if b.is_valid_transaction(tx):
            sender.send(msg)


if __name__ == '__main__':
    num_workers = int(sys.argv[1])
    for i in range(num_workers):
        mp.Process(target=validate_transactions, args=(i,)).start()
