# BigchainDB
[![Codeship Status for
ascribe/bigchain](https://codeship.com/projects/a66d2f80-b25c-0133-6b70-02105821d9b0/status?branch=develop)
](https://codeship.com/projects/115150) [![codecov.io](https://codecov.io/github/bigchaindb/bigchaindb/coverage.svg?branch=develop)](https://codecov.io/github/bigchaindb/bigchaindb?branch=develop) 


## Documentation

Documentation is available at https://bigchaindb.readthedocs.org/

## Getting started

#### Install RethinkDB on Ubuntu

```sh
# install rethinkdb https://rethinkdb.com/docs/install/ubuntu/
$ source /etc/lsb-release && echo "deb http://download.rethinkdb.com/apt $DISTRIB_CODENAME main" | sudo tee /etc/apt/sources.list.d/rethinkdb.list
$ wget -qO- http://download.rethinkdb.com/apt/pubkey.gpg | sudo apt-key add -
$ sudo apt-get update
$ sudo apt-get install rethinkdb

# start rethinkdb
$ rethinkdb
```

#### Install BigchainDB
```sh
$ pip install bigchaindb
```

#### Running BigchainDB
Currently BigchainDB only supports Python 3.4+


Start the main process. If it's the first time `bigchaindb` will generate a default
configuration file for you.
```sh
$ bigchaindb start
```

Generate some tests transactions:

```sh
$ bigchaindb-benchmark load # add '-m' if you want to use all your cores
```

To know more about the bigchain command run
```sh
$ bigchaindb -h
```

#### Importing `BigchainDB` from the interpreter (python/ipython)
Make sure your `rethinkdb` process is running.

```python
>>> from bigchaindb import Bigchain
>>> b = Bigchain()
>>> b.me
'2B8C8PJxhycFzn4wncRhBNmMWwE5Frr9nLBUa1dGGxj5W'
```

#### Configuration

BigchainDB creates a default configuration file on `$HOME/.bigchaindb` on the
first run.

```sh
$ bigchaindb show-config
```

#### Testing

```
$ py.test -v
```
