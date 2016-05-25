import zmq
import rapidjson

from bigchaindb import Bigchain


def create_blocks():
    context = zmq.Context()
    receiver = context.socket(zmq.PULL)
    receiver.bind("tcp://*:5558")
    poller = zmq.Poller()
    poller.register(receiver, zmq.POLLIN)
    b = Bigchain()

    while True:
        validated_transactions = []
        for _ in range(1000):
            evts = poller.poll(5000)
            if evts:
                validated_transactions.append(rapidjson.loads(receiver.recv()))
            else:
                break

        if validated_transactions:
            block = b.create_block(validated_transactions)
            b.write_block(block)


if __name__ == '__main__':
    create_blocks()
