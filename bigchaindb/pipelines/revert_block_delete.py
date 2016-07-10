from pipes import Pipeline, Node

from bigchaindb.pipelines.utils import ChangeFeed
from bigchaindb import Bigchain


class BlockDeleteRevert:

    def __init__(self):
        self.bigchain = Bigchain()

    def revert(self, block):
        self.bigchain.write_block(block)


def create_pipeline():
    changefeed = ChangeFeed('bigchain', 'delete')
    reverter = BlockDeleteRevert()

    pipeline = Pipeline([
        changefeed,
        Node(reverter)
    ])

    return pipeline


if __name__ == '__main__':
    create_pipeline().start()
