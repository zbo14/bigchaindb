import time
import logging
import logging.config
import multiprocessing as mp

import bigchaindb
from bigchaindb.pipelines import vote, block, election, stale
from bigchaindb.web import server


BANNER = """
****************************************************************************
*                                                                          *
*   Initialization complete. BigchainDB Server is ready and waiting.       *
*   You can send HTTP requests via the HTTP API documented in the          *
*   BigchainDB Server docs at:                                             *
*    https://bigchaindb.com/http-api                                       *
*                                                                          *
*   Listening to client connections on: {:<15}                    *
*                                                                          *
****************************************************************************
"""

log_queue = mp.Queue()

config_initial = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'class': 'logging.Formatter',
            'format': '%(asctime)s %(processName)s %(threadName)s %(message)s',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'detailed',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console']
    },
}

config_listener = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'class': 'logging.Formatter',
            'format': '%(name)-15s %(levelname)-8s %(processName)-10s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'simple',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console']
    },
}


class MyHandler:
    """
    A simple handler for logging events. It runs in the listener process and
    dispatches events to loggers based on the name in the received record,
    which then get dispatched, by the logging system, to the handlers
    configured for those loggers.
    """
    def handle(self, record):
        logger = logging.getLogger('logger')
        # The process name is transformed just to show that it's the listener
        # doing the logging to files and console
        record.processName = '%s (for %s)' % (mp.current_process().name, record.processName)
        logger.handle(record)


def listener_process(q):
    print('***********')
    print('IN LISTENER')
    print('***********')
    listener = logging.handlers.QueueListener(q, MyHandler())
    listener.start()


logging.config.dictConfig(config_initial)

logger = logging.getLogger()
logger.addHandler(logging.handlers.QueueHandler(log_queue))


def start():
    print('***********')
    print('STARTING')
    print('***********')
    logger.info('Initializing BigchainDB...')

    # start the processes
    logger.info('Starting block')
    block.start(log_queue)

    logger.info('Starting voter')
    vote.start(log_queue)

    logger.info('Starting stale transaction monitor')
    stale.start(log_queue)

    logger.info('Starting election')
    election.start(log_queue)

    # start the web api
    app_server = server.create_server(bigchaindb.config['server'])
    p_webapi = mp.Process(name='webapi', target=app_server.run)
    p_webapi.start()

    # start message
    logger.info(BANNER.format(bigchaindb.config['server']['bind']))

    logger.info('Starting listener')
    listener_process(log_queue)
