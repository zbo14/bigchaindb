import collections

import rethinkdb as r

from bigchaindb import Bigchain


def changes(outqueue, table, operation, prefeed=None):
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


class PrefeedQueue:

    def __init__(self, prefeed, queue):
        if not isinstance(prefeed, collections.Iterable):
            prefeed = iter(prefeed)

        self.prefeed = prefeed
        self.queue = queue
        self.exhausted = False

    def get(self, timeout=None):
        if not self.exhausted:
            try:
                return next(self.prefeed)
            except StopIteration:
                self.exhausted = True
        else:
            return self.queue.pop(timeout)

