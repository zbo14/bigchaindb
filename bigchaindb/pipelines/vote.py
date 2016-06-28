from collections import Counter
import multiprocessing as mp

from pipes import Pipeline, Node

from bigchaindb.pipelines.utils import changes, PrefeedQueue
from bigchaindb import Bigchain


class Voter:

    def __init__(self):
        self.bigchain = Bigchain()
        last_voted = self.bigchain.get_last_voted_block()
        self.last_voted_id = last_voted['id']
        self.last_voted_number = last_voted['block_number']

        self.counters = Counter()
        self.validity = {}

    def ungroup(self, block):
        num_tx = len(block['block']['transactions'])
        for tx in block['block']['transactions']:
            yield tx, block['id'], num_tx

    def validate_tx(self, tx, block_id, num_tx):
        return bool(self.bigchain.is_valid_transaction(tx)), block_id, num_tx

    def vote(self, tx_validity, block_id, num_tx):
        self.counters[block_id] += 1
        self.validity[block_id] = tx_validity and self.validity.get(block_id,
                                                                    True)

        if self.counters[block_id] == num_tx:
            vote = self.bigchain.vote(block_id,
                                      self.last_voted_id,
                                      self.validity[block_id])
            self.last_voted_id = block_id
            del self.counters[block_id]
            del self.validity[block_id]
            return vote

    def write_vote(self, vote):
        self.bigchain.write_vote(vote)


def initial(queue):
    b = Bigchain()
    initial = b.get_unvoted_blocks()
    return initial


def create_pipeline():
    queue_changes = mp.Queue()
    mp.Process(target=changes(queue_changes, 'bigchain', 'insert')).start()
    inqueue = PrefeedQueue(initial(), queue_changes)

    voter = Voter()
    vote_pipeline = Pipeline([
        voter.ungroup,
        Node(voter.validate_tx, fraction_of_cores=1),
        voter.vote,
        voter.write_vote
    ], inqueue=inqueue)

    return vote_pipeline


if __name__ == '__main__':
    create_pipeline().start()

