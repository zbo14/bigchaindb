import multiprocessing as mp

import rethinkdb as r
from pipes import Pipeline, Node

from bigchaindb.pipelines.utils import changes, PrefeedQueue
from bigchaindb import Bigchain


class Block:

    def __init__(self):
        self.bigchain = Bigchain()
        self.txs = []

    def validate_tx(self, tx):
        return self.bigchain.is_valid_transaction(tx)

    def create(self, tx, timeout=False):
        if tx:
            self.txs.append(tx)
        if self.txs and (len(self.txs) == 1000 or timeout):
            block = self.bigchain.create_block(self.txs)
            self.txs = []
            return block

    def write(self, block):
        self.bigchain.write_block(block)


def initial():
    b = Bigchain()

    initial = r.table('backlog')\
        .between([b.me, r.minval],
                 [b.me, r.maxval],
                 index='assignee__transaction_timestamp')\
        .order_by(index=r.asc('assignee__transaction_timestamp'))\
        .run(b.conn)

    return initial


def create_pipeline():
    queue_changes = mp.Queue()
    mp.Process(target=changes(queue_changes, 'backlog', 'insert')).start()
    inqueue = PrefeedQueue(initial(), queue_changes)

    block = Block()
    block_pipeline = Pipeline([
        Node(block.validate_tx, fraction_of_cores=1),
        Node(block.create, timeout=1),
        Node(block.write)
    ], inqueue=inqueue)

    return block_pipeline


if __name__ == '__main__':
    create_pipeline().start()
