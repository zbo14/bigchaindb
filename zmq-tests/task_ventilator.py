import zmq
import rapidjson
import rethinkdb as r

from bigchaindb import Bigchain


def get_from_backlog():
    b = Bigchain()
    initial_results = r.table('backlog') \
        .between([b.me, r.minval], [b.me, r.maxval], index='assignee__transaction_timestamp') \
        .order_by(index=r.asc('assignee__transaction_timestamp')) \
        .run(b.conn)
    return initial_results


def ventilator():
    context = zmq.Context()

    # socket to send messages on
    sender = context.socket(zmq.PUSH)
    sender.bind("tcp://*:5557")

    # send a transactions
    backlog_transactions = get_from_backlog()
    for tx in backlog_transactions:
        sender.send(rapidjson.dumps(tx).encode())


if __name__ == '__main__':
    ventilator()
