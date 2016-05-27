import logging
import threading
import multiprocessing as mp
import queue

import time
import logstats
import rethinkdb as r

import bigchaindb
from bigchaindb import Bigchain
from bigchaindb.monitor import Monitor
from bigchaindb.util import ProcessGroup, BufferedQueue


logger = logging.getLogger(__name__)


class Block(object):

    def __init__(self, q_new_transaction):
        """
        Initialize the class with the needed
        """
        self.ls = logstats.Logstats(msg='new tx: {new_tx:<6} validated tx: {tx_validated:<6} blocks: {block_ready:<2}')
        self._q_new_transaction = q_new_transaction
        self.q_new_transaction = BufferedQueue(buffer_size=4096*4, maxsize=32)
        self.q_tx_to_validate = BufferedQueue()
        self.q_tx_validated = BufferedQueue(buffer_size=256, maxsize=1000)
        self.q_tx_delete = BufferedQueue()
        self.q_block = mp.Queue()
        self.initialized = mp.Event()
        self.monitor = Monitor()

    def filter_by_assignee(self):
        """
        Handle transactions that are assigned to me
        """

        # create a bigchain instance
        b = Bigchain()

        while True:
            tx = self.q_new_transaction.get()

            # poison pill
            if tx == 'stop':
                self.q_tx_to_validate.put('stop')
                return

            if tx['assignee'] == b.me:
                tx.pop('assignee')
                self.q_tx_to_validate.put(tx)

    def validate_transactions(self):
        """
        Checks if the incoming transactions are valid
        """

        # create a bigchain instance
        b = Bigchain()

        while True:
            tx = self.q_new_transaction.get()

            # poison pill
            if tx == 'stop':
                self.q_tx_delete.put('stop')
                self.q_tx_validated.put('stop')
                return

            #self.q_tx_delete.put(tx['id'])

            with self.monitor.timer('validate_transaction', rate=bigchaindb.config['statsd']['rate']):
                is_valid_transaction = b.is_valid_transaction(tx)

            if is_valid_transaction:
                self.q_tx_validated.put(tx)

    def create_blocks(self):
        """
        Create a block with valid transactions
        """

        # create a bigchain instance
        b = Bigchain()
        stop = False

        while True:

            # read up to 1000 transactions
            validated_transactions = []
            for i in range(1000):
                try:
                    txs = self.q_tx_validated.get(timeout=5)
                except queue.Empty:
                    break

                # poison pill
                if txs == 'stop':
                    stop = True
                    break

                validated_transactions.extend(txs)

            # if there are no transactions skip block creation
            if validated_transactions:
                # create block
                block = b.create_block(validated_transactions)
                self.q_block.put(block)

            if stop:
                self.q_block.put('stop')
                return

    def write_blocks(self):
        """
        Write blocks to the bigchain
        """

        # create bigchain instance
        b = Bigchain()

        # Write blocks
        while True:
            block = self.q_block.get()

            # poison pill
            if block == 'stop':
                return

            with self.monitor.timer('write_block'):
                b.write_block(block)

    def delete_transactions(self):
        """
        Delete transactions from the backlog
        """
        # create bigchain instance
        b = Bigchain()
        stop = False

        while True:
            # try to delete in batch to reduce io
            tx_to_delete = []
            for i in range(1000):
                try:
                    tx = self.q_tx_delete.get(timeout=5)
                except queue.Empty:
                    break

                # poison pill
                if tx == 'stop':
                    stop = True
                    break

                tx_to_delete.append(tx)

            if tx_to_delete:
                r.table('backlog').get_all(*tx_to_delete).delete(durability='soft').run(b.conn)

            if stop:
                return

    def bootstrap(self):
        """
        Get transactions from the backlog that may have been assigned to this while it was
        online (not listening to the changefeed)
        """
        # create bigchain instance
        b = Bigchain()


        # get initial results
        initial_results = r.table('backlog')\
            .between([b.me, r.minval], [b.me, r.maxval], index='assignee__transaction_timestamp')\
            .order_by(index=r.asc('assignee__transaction_timestamp'))\
            .run(b.conn)

        # add results to the queue
        for result in initial_results:
            self.q_new_transaction.put(result)

        for i in range(mp.cpu_count()):
            self.q_new_transaction.put('stop')

        return queue

    def start(self):
        """
        Bootstrap and start the processes
        """

        threading.Thread(target=self.queue_status).start()
        logstats.thread.start(self.ls)

        logger.info('bootstraping block module...')
        #self.q_new_transaction = self.bootstrap()
        logger.info('finished reading past transactions')
        self._start()

        # LOOK AT ME
        # LOOK AT ME
        # LOOK AT ME
        # LOOK AT ME
        # LOOK AT ME
        # LOOK AT ME
        return

        logger.info('finished bootstraping block module...')

        logger.info('starting block module...')
        self.q_new_transaction = self._q_new_transaction

        # signal initialization complete
        self.initialized.set()

        self._start()
        logger.info('exiting block module...')

    def kill(self):
        for i in range(mp.cpu_count()):
            self.q_new_transaction.put('stop')

    def queue_status(self):
        while True:
            self.ls['new_tx'] = self.q_new_transaction.qsize() if self.q_new_transaction else self._q_new_transaction.qsize()
            #self.ls['tx_to_validate'] = self.q_tx_to_validate.qsize()
            self.ls['tx_validated'] = self.q_tx_validated.qsize()
            #self.ls['tx_delete'] = self.q_tx_delete.qsize()
            self.ls['block_ready'] = self.q_block.qsize()
            time.sleep(1)

    def _start(self):
        """
        Initialize, spawn, and start the processes
        """
        # initialize the processes
        p_filter = ProcessGroup(concurrency=1, name='bootstrap', target=self.bootstrap)
        p_validate = ProcessGroup(name='tx_validate', target=self.validate_transactions)
        p_blocks = ProcessGroup(concurrency=1, name='tx_create', target=self.create_blocks)
        p_write = ProcessGroup(concurrency=1, name='write_blocks', target=self.write_blocks)
        #p_delete = ProcessGroup(name='delete_transactions', target=self.delete_transactions)

        # start the processes
        p_filter.start()
        p_validate.start()
        p_blocks.start()
        p_write.start()

        #p_delete.start()

