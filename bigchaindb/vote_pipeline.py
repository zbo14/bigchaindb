from collections import Counter
import multiprocessing as mp

import rethinkdb as r
from pipes import Pipeline, Node

from bigchaindb import Bigchain


def initial_txs(queue):
    b = Bigchain()

    initial = r.table('backlog')\
        .between([b.me, r.minval], [b.me, r.maxval], index='assignee__transaction_timestamp')\
        .order_by(index=r.asc('assignee__transaction_timestamp'))\
        .run(b.conn)

    for result in initial:
        queue.put(result)


def initial_blocks(queue):
    b = Bigchain()

    initial = b.get_unvoted_blocks()
    print(len(initial))
    for result in initial:
        queue.put(result)


def changes(outqueue, table, operation):
    b = Bigchain()

    def _changes():
        for change in r.table(table).changes().run(b.conn):
            is_insert = change['old_val'] is None
            is_delete = change['new_val'] is None
            is_update = not is_insert and not is_delete

            if is_insert and operation == 'insert':
                outqueue.put(change['new_val'])
            elif is_delete and operation == 'delete':
                outqueue.put(change['old_val'])
            elif is_update and operation == 'update':
                outqueue.put(change)
    return _changes


BIGCHAIN = None


def create_bigchain_instance():
    global BIGCHAIN
    BIGCHAIN = Bigchain()
    print('create instance')


def is_valid_tx(tx):
    print('is_valid_tx', tx)
    return bool(BIGCHAIN.is_valid_transaction(tx))


class Voter:

    def __init__(self):
        self.bigchain = Bigchain()
        last_voted = self.bigchain.get_last_voted_block()
        self.last_voted_id = last_voted['id']
        self.last_voted_number = last_voted['block_number']

        self.counters = Counter()
        self.validity = {}

    def ungroup(self, block):
        total = len(block['block']['transactions'])
        for tx in block['block']['transactions']:
            yield tx, block['id'], total

    def validate_tx(self, tx, block_id, total):
        return bool(self.bigchain.is_valid_transaction(tx)), block_id, total

    def vote(self, tx_validity, block_id, total):
        self.counters[block_id] += 1
        self.validity[block_id] = tx_validity and self.validity.get(block_id,
                                                                    True)

        if self.counters[block_id] == total:
            vote = self.bigchain.vote(block_id,
                                      self.last_voted_id,
                                      self.validity[block_id])
            self.last_voted_id = block_id
            del self.counters[block_id]
            del self.validity[block_id]
            return vote

    def write_vote(self, vote):
        self.bigchain.write_vote(vote)


class Blocker:

    def __init__(self):
        self.bigchain = Bigchain()
        self.txs = []

    def validate_tx(self, tx):
        return self.bigchain.is_valid_transaction(tx)

    def create(self, tx):
        if tx:
            self.txs.append(tx)
        if len(self.txs) == 10:
            block = self.bigchain.create_block(self.txs)
            self.txs = []
            return block

    def write(self, block):
        self.bigchain.write_block(block)


def main():
    queue_changes = mp.Queue()

    initial_txs(queue_changes)

    # mp.Process(target=changes(queue_changes, 'backlog', 'insert'))

    blocker = Blocker()
    blocker_pipeline = Pipeline([
        Node(blocker.validate_tx, fraction_of_cores=1),
        blocker.create,
        blocker.write
    ], inqueue=queue_changes)

    blocker_pipeline.start()


def _main():
    queue_changes = mp.Queue()

    initial_blocks(queue_changes)

    # mp.Process(target=changes(queue_changes, 'bigchain', 'insert'))

    voter = Voter()
    vote_pipeline = Pipeline([
        voter.ungroup,
        Node(voter.validate_tx, fraction_of_cores=1),
        voter.vote,
        voter.write_vote
    ], inqueue=queue_changes)

    vote_pipeline.start()


if __name__ == '__main__':
    _main()
