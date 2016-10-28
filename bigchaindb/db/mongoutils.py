"""Utils to initialize and drop the database."""

import time
import logging

from bigchaindb_common import exceptions
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure

import bigchaindb


logger = logging.getLogger(__name__)


class Connection:
    """This class is a proxy to run queries against the database,
    it is:
    - lazy, since it creates a connection only when needed
    - resilient, because before raising exceptions it tries
      more times to run the query or open a connection.
    """

    def __init__(self, host=None, port=None, db=None, max_tries=3):
        """Create a new Connection instance.

        Args:
            host (str, optional): the host to connect to.
            port (int, optional): the port to connect to.
            db (str, optional): the database to use.
            max_tries (int, optional): how many tries before giving up.
        """

        self.host = host or bigchaindb.config['database']['host']
        self.port = port or bigchaindb.config['database']['port']
        self.db = db or bigchaindb.config['database']['name']
        self.max_tries = max_tries
        self.conn = None

    def run(self, query):
        """Run a query.

        Args:
            query: the RethinkDB query.
        """

        if self.conn is None:
            self._connect()

        for i in range(self.max_tries):
            try:
                return query.run(self.conn)
            except ConnectionFailure as exc:
                if i + 1 == self.max_tries:
                    raise
                else:
                    self._connect()

    def _connect(self):
        for i in range(self.max_tries):
            try:
                self.conn = MongoClient(self.host, self.port)

            except ConnectionFailure as exc:
                if i + 1 == self.max_tries:
                    raise
                else:
                    time.sleep(2**i)


def get_conn():
    '''Get the connection to the database.'''

    return MongoClient(bigchaindb.config['database']['host'],
                       bigchaindb.config['database']['port'])


def get_database_name():
    return bigchaindb.config['database']['name']


def create_database(conn, dbname):
    if dbname in conn.database_names():
        raise exceptions.DatabaseAlreadyExists('Database `{}` already exists'.format(dbname))

    logger.info('Create database `%s`.', dbname)
    # TODO: read and write concerns can be declared here
    conn.get_database(dbname)


def create_table(conn, dbname, table_name):
    logger.info('Create `%s` table.', table_name)
    # create the table
    # TODO: read and write concerns can be declared here
    conn[dbname].create_collection(table_name)


def create_bigchain_secondary_index(conn, dbname):
    logger.info('Create `bigchain` secondary index.')
    # to select blocks by id 
    conn[dbname]['bigchain'].create_index('id', name='block_id')
    # to order blocks by timestamp
    conn[dbname]['bigchain'].create_index('block.timestamp', ASCENDING,
                                      name='block_timestamp')
    # to query the bigchain for a transaction id, this field is unique
    conn[dbname]['bigchain'].create_index('block.transactions.id',
                                      name='transaction_id', unique=True)
    # secondary index for payload data by UUID, this field is unique
    conn[dbname]['bigchain'] \
            .create_index('block.transactions.transaction.metadata.id',
                          name='metadata_id', unique=True)
    # secondary index for asset uuid, this field is unique
    conn[dbname]['bigchain'] \
            .create_index('block.transactions.transaction.asset.id',
                          name='asset_id', unique=True)
    # compound index on fulfillment and transactions id
    conn[dbname]['bigchain'] \
            .create_index(['block.transactions.transaction.fulfillments.txid',
                           'block.transactions.transaction.fulfillments.cid'],
                         name='tx_and_fulfillment')

def create_backlog_secondary_index(conn, dbname):
    logger.info('Create `backlog` secondary index.')
    # to order transactions by timestamp
    conn[dbname]['backlog'].create_index('transaction.timestamp', ASCENDING,
                                     name='transaction_timestamp')
    # compound index to read transactions from the backlog per assignee
    conn[dbname]['backlog'].create_index(['assignee',
                                      ('assignment_timestamp', DESCENDING)],
                                     name='assignee__transaction_timestamp')


def create_votes_secondary_index(conn, dbname):
    logger.info('Create `votes` secondary index.')
    # index on block id to quickly poll
    conn[dbname]['votes'].create_index('vote.voting_for_block',
                                       name='voting_for')
    # is the first index redundant then?
    # compound index to order votes by block id and node
    conn[dbname]['votes'].create_index(['vote.voting_for_block',
                                        'node_pubkey'], name='block_and_voter')


def init():
    # Try to access the keypair, throws an exception if it does not exist
    b = bigchaindb.Bigchain()

    conn = get_conn()
    dbname = get_database_name()
    create_database(conn, dbname)

    table_names = ['bigchain', 'backlog', 'votes']
    for table_name in table_names:
        create_table(conn, dbname, table_name)
    create_bigchain_secondary_index(conn, dbname)
    create_backlog_secondary_index(conn, dbname)
    create_votes_secondary_index(conn, dbname)

    logger.info('Create genesis block.')
    b.create_genesis_block()
    logger.info('Done, have fun!')


def drop(assume_yes=False):
    conn = get_conn()
    dbname = bigchaindb.config['database']['name']

    if assume_yes:
        response = 'y'
    else:
        response = input('Do you want to drop `{}` database? [y/n]: '.format(dbname))

    if response == 'y':
        logger.info('Drop database `%s`', dbname)
        conn.drop_database(dbname)
        logger.info('Done.')
    else:
        logger.info('Drop aborted')
