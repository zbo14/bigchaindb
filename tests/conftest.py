"""
Fixtures and setup / teardown functions

Tasks:
1. setup test database before starting the tests
2. delete test database after running the tests
"""

import os
import copy
import random

import pytest

from logging import getLogger
from logging.config import dictConfig
from bigchaindb.common import crypto

TEST_DB_NAME = 'bigchain_test'

USER2_SK, USER2_PK = crypto.generate_key_pair()

# Test user. inputs will be created for this user. Cryptography Keys
USER_PRIVATE_KEY = '8eJ8q9ZQpReWyQT5aFCiwtZ5wDZC4eDnCen88p3tQ6ie'
USER_PUBLIC_KEY = 'JEAkEJqLbbgDRAtMm8YAjGp759Aq2qTn9eaEHUj2XePE'


def pytest_addoption(parser):
    from bigchaindb.backend import connection

    backends = ', '.join(connection.BACKENDS.keys())
    parser.addoption(
        '--database-backend',
        action='store',
        default=os.environ.get('BIGCHAINDB_DATABASE_BACKEND', 'rethinkdb'),
        help='Defines the backend to use (available: {})'.format(backends),
    )


def pytest_ignore_collect(path, config):
    from bigchaindb.backend.connection import BACKENDS
    path = str(path)

    if os.path.isdir(path):
        dirname = os.path.split(path)[1]
        if dirname in BACKENDS.keys() and dirname != config.getoption('--database-backend'):
            print('Ignoring unrequested backend test dir: ', path)
            return True


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'bdb(): Mark the test as needing BigchainDB, i.e. a database with '
        'the three tables: "backlog", "bigchain", "votes". BigchainDB will '
        'be configured such that the database and tables are available for an '
        'entire test session. For distributed tests, the database name will '
        'be suffixed with the process identifier, e.g.: "bigchain_test_gw0", '
        'to ensure that each process session has its own separate database.'
    )
    config.addinivalue_line(
        'markers',
        'genesis(): Mark the test as needing a genesis block in place. The '
        'prerequisite steps of configuration and database setup are taken '
        'care of at session scope (if needed), prior to creating the genesis '
        'block. The genesis block has function scope: it is destroyed after '
        'each test function/method.'
    )


@pytest.fixture(autouse=True)
def _bdb_marker(request):
    if request.keywords.get('bdb', None):
        request.getfixturevalue('_bdb')


@pytest.fixture(autouse=True)
def _genesis_marker(request):
    if request.keywords.get('genesis', None):
        request.getfixturevalue('_genesis')


@pytest.fixture(autouse=True)
def _restore_config(_configure_bigchaindb):
    from bigchaindb import config, config_utils
    config_before_test = copy.deepcopy(config)
    yield
    config_utils.set_config(config_before_test)


@pytest.fixture
def _restore_dbs(request):
    from bigchaindb.backend import connect, schema
    from bigchaindb.common.exceptions import DatabaseDoesNotExist
    from .utils import list_dbs
    conn = connect()
    dbs_before_test = list_dbs(conn)
    yield
    dbs_after_test = list_dbs(conn)
    dbs_to_delete = (
        db for db in set(dbs_after_test) - set(dbs_before_test)
        if TEST_DB_NAME not in db
    )
    print(dbs_to_delete)
    for db in dbs_to_delete:
        try:
            schema.drop_database(conn, db)
        except DatabaseDoesNotExist:
            pass


@pytest.fixture(scope='session')
def _configure_bigchaindb(request):
    import bigchaindb
    from bigchaindb import config_utils
    test_db_name = TEST_DB_NAME
    # Put a suffix like _gw0, _gw1 etc on xdist processes
    xdist_suffix = getattr(request.config, 'slaveinput', {}).get('slaveid')
    if xdist_suffix:
        test_db_name = '{}_{}'.format(TEST_DB_NAME, xdist_suffix)

    backend = request.config.getoption('--database-backend')
    config = {
        'database': bigchaindb._database_map[backend],
        'keypair': {
            'private': '31Lb1ZGKTyHnmVK3LUMrAUrPNfd4sE2YyBt3UA4A25aA',
            'public': '4XYfCbabAWVUCbjTmRTFEu2sc3dFEdkse4r6X498B1s8',
        }
    }
    config['database']['name'] = test_db_name
    config_utils.set_config(config)


"""
@pytest.fixture(scope='session')
def _configure_bigchaindb_with_ssl(request):
    import bigchaindb
    from bigchaindb import config_utils
    test_db_name = TEST_DB_NAME
    # Put a suffix like _gw0, _gw1 etc on xdist processes
    xdist_suffix = getattr(request.config, 'slaveinput', {}).get('slaveid')
    if xdist_suffix:
        test_db_name = '{}_{}'.format(TEST_DB_NAME, xdist_suffix)

    backend = request.config.getoption('--database-backend')
    config = {
        'database': bigchaindb._database_map[backend],
        'keypair': {
            'private': '31Lb1ZGKTyHnmVK3LUMrAUrPNfd4sE2YyBt3UA4A25aA',
            'public': '4XYfCbabAWVUCbjTmRTFEu2sc3dFEdkse4r6X498B1s8',
        }
    }
    config['database']['name'] = test_db_name
    config_utils.set_config(config)
"""


@pytest.fixture(scope='session')
def _setup_database(_configure_bigchaindb):
    from bigchaindb import config
    from bigchaindb.backend import connect, schema
    from bigchaindb.common.exceptions import DatabaseDoesNotExist
    print('Initializing test db')
    dbname = config['database']['name']
    conn = connect()

    try:
        schema.drop_database(conn, dbname)
    except DatabaseDoesNotExist:
        pass

    schema.init_database(conn)
    print('Finishing init database')

    yield

    print('Deleting `{}` database'.format(dbname))
    conn = connect()
    try:
        schema.drop_database(conn, dbname)
    except DatabaseDoesNotExist:
        pass

    print('Finished deleting `{}`'.format(dbname))


@pytest.fixture
def _bdb(_setup_database, _configure_bigchaindb):
    from bigchaindb import config
    from bigchaindb.backend import connect
    from bigchaindb.backend.admin import get_config
    from bigchaindb.backend.schema import TABLES
    from .utils import flush_db, update_table_config
    conn = connect()
    # TODO remove condition once the mongodb implementation is done
    if config['database']['backend'] == 'rethinkdb':
        table_configs_before = {
            t: get_config(conn, table=t) for t in TABLES
        }
    yield
    dbname = config['database']['name']
    flush_db(conn, dbname)
    # TODO remove condition once the mongodb implementation is done
    if config['database']['backend'] == 'rethinkdb':
        for t, c in table_configs_before.items():
            update_table_config(conn, t, **c)


@pytest.fixture
def _genesis(_bdb, genesis_block):
    # TODO for precision's sake, delete the block once the test is done. The
    # deletion is done indirectly via the teardown code of _bdb but explicit
    # deletion of the block would make things clearer. E.g.:
    # yield
    # tests.utils.delete_genesis_block(conn, dbname)
    pass


# We need this function to avoid loading an existing
# conf file located in the home of the user running
# the tests. If it's too aggressive we can change it
# later.
@pytest.fixture
def ignore_local_config_file(monkeypatch):
    def mock_file_config(filename=None):
        return {}

    monkeypatch.setattr('bigchaindb.config_utils.file_config',
                        mock_file_config)


@pytest.fixture
def reset_logging_config():
    # root_logger_level = getLogger().level
    root_logger_level = 'DEBUG'
    dictConfig({'version': 1, 'root': {'level': 'NOTSET'}})
    yield
    getLogger().setLevel(root_logger_level)


@pytest.fixture
def user_sk():
    return USER_PRIVATE_KEY


@pytest.fixture
def user_pk():
    return USER_PUBLIC_KEY


@pytest.fixture
def user2_sk():
    return USER2_SK


@pytest.fixture
def user2_pk():
    return USER2_PK


@pytest.fixture
def alice():
    from bigchaindb.common.crypto import generate_key_pair
    return generate_key_pair()


@pytest.fixture
def alice_privkey(alice):
    return alice.private_key


@pytest.fixture
def alice_pubkey(alice):
    return alice.public_key


@pytest.fixture
def bob():
    from bigchaindb.common.crypto import generate_key_pair
    return generate_key_pair()


@pytest.fixture
def bob_privkey(bob):
    return bob.private_key


@pytest.fixture
def bob_pubkey(carol):
    return bob.public_key


@pytest.fixture
def carol():
    from bigchaindb.common.crypto import generate_key_pair
    return generate_key_pair()


@pytest.fixture
def carol_privkey(carol):
    return carol.private_key


@pytest.fixture
def carol_pubkey(carol):
    return carol.public_key


@pytest.fixture
def b():
    from bigchaindb import Bigchain
    return Bigchain()


@pytest.fixture
def create_tx(b, user_pk):
    from bigchaindb.models import Transaction
    return Transaction.create([b.me], [([user_pk], 1)])


@pytest.fixture
def signed_create_tx(b, create_tx):
    return create_tx.sign([b.me_private])


@pytest.fixture
def signed_transfer_tx(signed_create_tx, user_pk, user_sk):
    from bigchaindb.models import Transaction
    inputs = signed_create_tx.to_inputs()
    tx = Transaction.transfer(inputs, [([user_pk], 1)], asset_id=signed_create_tx.id)
    return tx.sign([user_sk])


@pytest.fixture
def structurally_valid_vote():
    return {
        'node_pubkey': 'c' * 44,
        'signature': 'd' * 86,
        'vote': {
            'voting_for_block': 'a' * 64,
            'previous_block': 'b' * 64,
            'is_block_valid': False,
            'invalid_reason': None,
            'timestamp': '1111111111'
        }
    }


@pytest.fixture
def genesis_block(b):
    return b.create_genesis_block()


@pytest.fixture
def inputs(user_pk, b, genesis_block):
    from bigchaindb.models import Transaction

    # create blocks with transactions for `USER` to spend
    prev_block_id = genesis_block.id
    for block in range(4):
        transactions = [
            Transaction.create(
                [b.me],
                [([user_pk], 1)],
                metadata={'msg': random.random()},
            ).sign([b.me_private])
            for _ in range(10)
        ]
        block = b.create_block(transactions)
        b.write_block(block)

        # vote the blocks valid, so that the inputs are valid
        vote = b.vote(block.id, prev_block_id, True)
        prev_block_id = block.id
        b.write_vote(vote)


@pytest.fixture
def inputs_shared(user_pk, user2_pk, genesis_block):
    from bigchaindb.models import Transaction

    # create blocks with transactions for `USER` to spend
    prev_block_id = genesis_block.id
    for block in range(4):
        transactions = [
            Transaction.create(
                [b.me],
                [user_pk, user2_pk],
                metadata={'msg': random.random()},
            ).sign([b.me_private])
            for _ in range(10)
        ]
        block = b.create_block(transactions)
        b.write_block(block)

        # vote the blocks valid, so that the inputs are valid
        vote = b.vote(block.id, prev_block_id, True)
        prev_block_id = block.id
        b.write_vote(vote)


@pytest.fixture
def dummy_db(request):
    from bigchaindb.backend import connect, schema
    from bigchaindb.common.exceptions import (DatabaseDoesNotExist,
                                              DatabaseAlreadyExists)
    conn = connect()
    dbname = request.fixturename
    xdist_suffix = getattr(request.config, 'slaveinput', {}).get('slaveid')
    if xdist_suffix:
        dbname = '{}_{}'.format(dbname, xdist_suffix)
    try:
        schema.init_database(conn, dbname)
    except DatabaseAlreadyExists:
        schema.drop_database(conn, dbname)
        schema.init_database(conn, dbname)
    yield dbname
    try:
        schema.drop_database(conn, dbname)
    except DatabaseDoesNotExist:
        pass


@pytest.fixture
def not_yet_created_db(request):
    from bigchaindb.backend import connect, schema
    from bigchaindb.common.exceptions import DatabaseDoesNotExist
    conn = connect()
    dbname = request.fixturename
    xdist_suffix = getattr(request.config, 'slaveinput', {}).get('slaveid')
    if xdist_suffix:
        dbname = '{}_{}'.format(dbname, xdist_suffix)
    try:
        schema.drop_database(conn, dbname)
    except DatabaseDoesNotExist:
        pass
    yield dbname
    try:
        schema.drop_database(conn, dbname)
    except DatabaseDoesNotExist:
        pass


@pytest.fixture
def db_config():
    from bigchaindb import config
    return config['database']


@pytest.fixture
def db_host(db_config):
    return db_config['host']


@pytest.fixture
def db_port(db_config):
    return db_config['port']


@pytest.fixture
def db_name(db_config):
    return db_config['name']


@pytest.fixture
def db_conn():
    from bigchaindb.backend import connect
    return connect()


@pytest.fixture
def mocked_setup_pub_logger(mocker):
    return mocker.patch(
        'bigchaindb.log.setup.setup_pub_logger', autospec=True, spec_set=True)


@pytest.fixture
def mocked_setup_sub_logger(mocker):
    return mocker.patch(
        'bigchaindb.log.setup.setup_sub_logger', autospec=True, spec_set=True)


ca_crt="""-----BEGIN CERTIFICATE-----
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
Qs3HMrZBFYSooUdps/9YA9mZtfI=
-----END CERTIFICATE-----"""

crl_pem="""-----BEGIN X509 CRL-----
MIIDoTCCAYkCAQEwDQYJKoZIhvcNAQELBQAwgYwxCzAJBgNVBAYTAkRFMQ8wDQYD
VQQIDAZCZXJsaW4xDzANBgNVBAcMBkJlcmxpbjEYMBYGA1UECgwPQmlnY2hhaW5E
QiBHbWJIMQwwCgYDVQQLDANFTkcxEDAOBgNVBAMMB1RFU1QtQ0ExITAfBgkqhkiG
9w0BCQEWEmRldkBiaWdjaGFpbmRiLmNvbRcNMTcwNjAyMDcwNDA3WhcNMTcxMTI5
MDcwNDA3WqCBxzCBxDCBwQYDVR0jBIG5MIG2gBSXyNzI7q/icMQJmxlQj4YdLP9u
JqGBkqSBjzCBjDELMAkGA1UEBhMCREUxDzANBgNVBAgMBkJlcmxpbjEPMA0GA1UE
BwwGQmVybGluMRgwFgYDVQQKDA9CaWdjaGFpbkRCIEdtYkgxDDAKBgNVBAsMA0VO
RzEQMA4GA1UEAwwHVEVTVC1DQTEhMB8GCSqGSIb3DQEJARYSZGV2QGJpZ2NoYWlu
ZGIuY29tggkApMTf2xrbg8cwDQYJKoZIhvcNAQELBQADggIBAEDFXjmlQhBafb9u
IId7ZrHFeueCiDsWJd2cI7BOIU4gsJzrL+SCjvAWyADd1np0gB86M7JK1W3iUfKI
FbwAbsxgJSnwyzwoQcTCp8/vD7z7+7uTxvbaEGOEiW9sVqRs/CKIzVoSQPB/R6cM
9WHwRuXeLALPIrVsxRaeIMbhEUgmfi9R2KvzKvc6yLMxWd1mmW8xdq7zZ6nlGl9Y
mrnRwOEdfgOUvuAaQgBculK3eKZmzJzzh1t+hJstmzdjtM+0gw3bzGLg3IJJ2uTK
D6nnSLG/QGTvnOmhIlnr26sYvVSMJrPrT7EyI/pN4GYWHwJ3rIJm9ii1+4q+D6YX
a6iyywOL/T0Sb7EUXmM9KHhnoaLXQetGmP2bgMprUF+3rgj/KjPHk2eXFyW++GWs
jlcyRvBd8a5AA9L2pPmoKQEQNL65YJcJSzfT3ZpkPxw/kD08Y29Vn7i86ol+MSdz
4dYuI4dTyU5IcMX4eQi4rdTm8rS55EE3MkL0OePeq375GROoInSyKeLpqPDPdpZx
Fo0AX0Rn3lt4vXFba84Vz5EveXt/jP2c01CXjTDzwfL13B7cbNl8yjD+Qopt9qXw
BPet7/eZs9gwcpcYooRjSD0zYvW3/wngqTPY/nPMZ4Wpm6QivGZo7LfMz5regjeT
DMQWkWlP8aup1aPeoDFXC2tzQhVK
-----END X509 CRL-----"""

test_mdb_ssl_cert_and_key_file="""Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number: 1 (0x1)
    Signature Algorithm: sha256WithRSAEncryption
        Issuer: C=DE, ST=Berlin, L=Berlin, O=BigchainDB GmbH, OU=ENG, CN=TEST-CA/emailAddress=dev@bigchaindb.com
        Validity
            Not Before: Jun  2 07:09:28 2017 GMT
            Not After : May 31 07:09:28 2027 GMT
        Subject: C=DE, ST=Berlin, L=Berlin, O=BigchainDB GmbH, OU=ENG, CN=test-mdb-ssl/emailAddress=dev@bigchaindb.com
        Subject Public Key Info:
            Public Key Algorithm: rsaEncryption
                Public-Key: (4096 bit)
                Modulus:
                    00:e4:71:43:91:f2:3a:26:4d:6d:61:f5:54:dd:a4:
                    a2:8b:e8:79:b7:44:94:9f:30:5d:86:d8:f5:9d:80:
                    cb:51:e8:c0:8c:9e:2f:fe:cb:9f:bb:f1:b5:97:47:
                    d1:9e:43:64:2b:f0:3f:99:30:1c:27:34:74:87:1e:
                    73:8f:86:66:89:0b:b9:64:05:8a:95:d7:81:da:fa:
                    b7:d0:4c:59:0e:1c:d7:1f:07:74:7d:38:9d:b0:6d:
                    02:a8:c3:63:f4:5d:d5:29:5b:df:8a:56:c5:51:29:
                    32:5b:ea:cc:ea:00:a0:04:e9:8a:f5:a0:e1:c3:77:
                    c9:3d:1b:99:fa:e8:bb:08:e5:98:bb:ec:5d:7e:d9:
                    7e:39:98:ab:16:cf:e6:e8:df:a9:6b:37:72:83:4d:
                    43:94:3e:99:39:ae:1f:5a:c9:51:71:30:5e:20:70:
                    c9:90:ff:ba:8b:6c:d9:5f:3d:df:03:d5:fe:f7:52:
                    ea:41:6d:4b:fe:6e:04:30:ef:a4:19:20:a8:fd:fb:
                    0c:72:76:2c:30:54:5d:f4:2b:e9:cd:96:3f:bb:e9:
                    6d:7e:79:8f:fe:06:6f:40:b1:42:a8:54:80:65:56:
                    50:af:c2:e2:68:e0:ac:22:90:00:ae:bc:6f:55:1a:
                    b7:ed:90:22:e8:c7:34:1e:4a:7d:d2:26:b0:35:16:
                    ec:30:45:cd:ac:f3:87:f6:8b:fe:84:8b:b3:9f:13:
                    08:f2:59:9f:3f:64:ee:20:a0:dc:87:8a:28:89:87:
                    1c:a1:91:63:81:01:66:43:7b:5f:5f:38:69:a7:f7:
                    ce:da:07:0b:7c:2c:87:df:9d:a5:12:db:b4:97:ed:
                    e9:2c:31:d5:14:cc:f0:f5:a4:6c:7e:59:4f:73:36:
                    eb:28:1c:be:69:98:1f:12:c1:e0:db:6f:f0:1a:62:
                    51:45:71:58:88:68:7e:06:42:cb:b3:31:85:53:90:
                    70:84:f4:08:18:d5:4e:07:8b:db:6f:d2:0f:ac:c4:
                    c2:52:a5:ed:07:b9:1b:1a:e9:22:4a:21:f8:1a:27:
                    9f:47:b5:ef:cb:24:3a:36:29:dc:68:fa:f1:9f:2e:
                    02:f8:8d:ab:25:6e:ba:3b:0a:0e:9e:c1:40:f4:56:
                    74:75:fc:b8:84:fa:bb:05:17:b7:b7:d8:36:02:40:
                    16:03:c9:75:a0:68:7e:e0:f4:c9:ae:fa:3d:0c:a3:
                    81:3b:e8:a2:84:dd:73:6e:d4:9f:e6:1c:db:d9:9c:
                    d6:c2:b9:fb:34:8f:f6:46:33:9e:29:bd:0d:11:33:
                    03:25:dc:1a:c7:44:00:76:83:16:5a:a5:d3:35:bb:
                    47:2d:9e:77:16:e0:b0:48:9b:dd:7c:20:56:56:1e:
                    1f:40:87
                Exponent: 65537 (0x10001)
        X509v3 extensions:
            X509v3 Basic Constraints: 
                CA:FALSE
            X509v3 Subject Key Identifier: 
                F5:2B:26:62:47:74:FC:75:6A:9E:76:8F:35:EB:23:64:BF:DD:18:3F
            X509v3 Authority Key Identifier: 
                keyid:97:C8:DC:C8:EE:AF:E2:70:C4:09:9B:19:50:8F:86:1D:2C:FF:6E:26
                DirName:/C=DE/ST=Berlin/L=Berlin/O=BigchainDB GmbH/OU=ENG/CN=TEST-CA/emailAddress=dev@bigchaindb.com
                serial:A4:C4:DF:DB:1A:DB:83:C7

            X509v3 Extended Key Usage: 
                TLS Web Server Authentication, TLS Web Client Authentication
            X509v3 Key Usage: 
                Digital Signature, Key Encipherment
            X509v3 Subject Alternative Name: 
                DNS:localhost, DNS:test-mdb-ssl
    Signature Algorithm: sha256WithRSAEncryption
         35:75:46:2b:6a:b9:a7:cc:24:ac:88:83:d5:e1:28:08:c1:0b:
         ff:9e:c1:57:86:92:c1:63:c3:bf:82:e7:11:d2:83:89:58:78:
         94:51:87:81:e7:fb:78:53:0c:19:2e:9e:41:84:26:91:2d:4a:
         e5:cf:7f:9b:4e:80:ad:5c:27:11:d7:62:81:4f:87:f4:59:d4:
         8d:ba:73:df:13:48:c5:b7:f1:21:1c:9a:59:17:d9:12:3e:4f:
         84:5a:ba:16:92:2d:5a:7a:f7:b7:af:76:c7:be:6e:96:b0:a3:
         8f:62:9a:ff:bc:16:db:e0:c5:f6:57:db:f6:1c:d7:eb:75:24:
         98:43:08:17:0c:9f:6e:42:b5:ee:74:b1:12:1e:1e:86:2d:72:
         6b:62:ab:33:ff:38:57:db:96:d5:98:c3:6e:97:36:26:f9:1b:
         e7:05:0f:db:e4:a7:4c:ca:2c:4c:d8:b8:d7:92:52:b0:fa:aa:
         c0:ee:b7:9c:33:25:85:77:3a:b8:50:6f:61:a4:59:54:89:fe:
         0d:f3:d2:7f:7d:91:64:7e:d1:e1:d1:02:5f:cf:e4:b1:47:70:
         98:37:4e:9f:33:94:7c:67:5a:66:11:d8:c4:33:0b:e9:a6:9a:
         86:cb:ab:27:e1:44:41:36:3d:8e:47:6f:73:eb:84:a7:90:eb:
         3a:6e:3a:16:1b:a1:68:60:6b:3a:93:47:1d:32:29:1c:d2:1b:
         c5:d6:cf:11:c5:0e:b0:67:4f:c2:07:82:bc:d4:9c:b4:a8:58:
         4c:a4:47:22:09:0a:e2:72:83:4e:e9:74:14:b7:2d:04:31:f6:
         37:e4:62:48:18:63:42:31:df:f6:2f:0f:ab:f2:ef:75:a8:a4:
         bf:96:5a:49:fb:ce:72:57:64:c9:c1:d3:56:67:5f:16:69:48:
         35:9c:98:14:f3:25:72:ef:18:38:38:43:f3:c4:29:55:fd:37:
         c8:ae:db:00:5d:96:50:ae:50:ca:14:a3:58:ae:84:21:c2:8f:
         24:cf:ce:f2:55:e1:60:37:67:ec:5a:08:81:85:8d:9b:13:c6:
         81:e7:66:0b:4e:76:1f:3b:14:a7:c0:ce:18:16:ec:77:e5:c8:
         33:47:1b:63:03:4b:9d:dd:fb:98:ff:0f:50:25:0c:88:a4:0e:
         67:a3:26:8d:1b:38:9f:9e:7e:25:dc:4b:49:ba:75:b5:3b:ae:
         9c:68:37:09:bb:59:c4:9a:14:6a:d3:c1:6c:19:55:b3:6c:95:
         bb:24:8b:55:f8:35:c6:1e:1d:fb:8f:60:33:fa:f8:94:a9:e2:
         6a:93:12:b8:d0:18:42:4e:8c:24:1f:96:2b:4c:49:fd:53:11:
         a0:aa:01:30:b2:3e:2c:9f
-----BEGIN CERTIFICATE-----
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
-----END CERTIFICATE-----
-----BEGIN PRIVATE KEY-----
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
gHiBIz7uxpEmV18w8MA+aiVZw3Ov3lE=
-----END PRIVATE KEY-----"""

test_bdb_ssl_cert_file="""Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number: 2 (0x2)
    Signature Algorithm: sha256WithRSAEncryption
        Issuer: C=DE, ST=Berlin, L=Berlin, O=BigchainDB GmbH, OU=ENG, CN=TEST-CA/emailAddress=dev@bigchaindb.com
        Validity
            Not Before: Jun  2 07:13:16 2017 GMT
            Not After : May 31 07:13:16 2027 GMT
        Subject: C=DE, ST=Berlin, L=Berlin, O=BigchainDB GmbH, OU=ENG, CN=test-bdb-ssl/emailAddress=dev@bigchaindb.com
        Subject Public Key Info:
            Public Key Algorithm: rsaEncryption
                Public-Key: (4096 bit)
                Modulus:
                    00:cb:59:21:c4:6e:b7:93:c7:d1:87:e1:8f:06:07:
                    c6:4f:31:35:4d:cc:43:8e:25:bf:4a:08:3e:df:3a:
                    b0:d8:3c:b5:45:39:49:aa:ef:17:53:2c:fa:74:73:
                    4e:f6:36:ae:ad:9a:88:3c:1a:ad:c2:ac:1c:b3:14:
                    39:18:8a:33:54:54:59:11:31:b8:8a:1a:0f:d5:79:
                    dd:6d:8d:63:a0:8f:0a:a3:5e:b2:40:d0:67:84:b7:
                    b6:4b:66:43:85:8a:18:a0:51:08:c9:b0:09:0b:8d:
                    bc:89:6c:47:a1:b2:bb:b8:1e:04:77:cb:7e:f4:ae:
                    c7:50:43:0b:49:48:90:4c:7d:72:17:0b:bb:57:72:
                    dd:ad:62:ba:8d:b4:80:c4:b8:83:a2:c9:08:f7:11:
                    44:0b:67:7f:d4:df:b8:59:5b:c0:32:26:04:95:bc:
                    c2:eb:92:7b:e9:5d:99:d7:d9:86:be:f0:a7:c5:e5:
                    1e:95:f3:86:21:74:3d:03:ca:4a:c0:4d:59:75:b5:
                    62:24:04:09:8a:47:0f:a6:c3:ee:99:82:dc:02:53:
                    70:f1:77:61:58:2e:9b:db:20:40:9f:15:08:de:3d:
                    c4:11:29:2f:6f:51:1b:36:19:b2:27:03:b8:15:ec:
                    3e:56:65:77:97:46:58:07:0b:85:87:a1:f4:ee:4f:
                    fc:bc:22:10:da:3c:83:dd:80:26:d7:3e:23:f6:0e:
                    3f:4d:f9:1a:eb:2f:ca:60:ea:97:40:23:d4:14:c3:
                    b5:c1:46:f2:15:2a:7e:18:56:3a:58:51:fb:a7:42:
                    14:19:0d:79:1e:25:b4:1a:51:74:7b:93:e0:9e:a9:
                    41:83:ab:94:6f:3c:6f:23:0c:7e:bc:14:31:54:ca:
                    8a:47:0e:a8:01:bd:f6:e9:bd:54:dd:10:84:5f:3f:
                    54:05:47:ae:4e:5d:e1:10:9d:a1:7b:08:b5:96:c6:
                    ba:fc:97:e0:22:c7:07:23:a2:ad:be:e2:7a:a8:8c:
                    e9:8a:e4:8e:64:4a:e9:45:b9:2b:55:e0:5c:3a:e8:
                    92:fd:48:54:6b:1e:14:d9:98:72:53:6e:0b:bd:e8:
                    ea:a9:c1:b2:29:ac:35:7b:0d:a8:22:13:83:d7:af:
                    90:ec:4a:74:41:3c:fd:32:f6:46:a7:96:02:a3:23:
                    a2:f1:6f:0f:55:e6:aa:8b:47:17:74:a8:c9:5f:ab:
                    46:68:6e:d8:11:dc:bd:83:96:3a:a9:04:e0:4c:d2:
                    03:a8:9e:fd:00:c8:09:f9:71:69:92:10:75:8e:8f:
                    9e:e4:d6:1c:bd:fd:3f:32:fb:ce:a4:af:cf:9c:f6:
                    29:6e:15:ed:c7:df:2d:27:8f:03:b9:fc:ac:3f:23:
                    ac:2a:f3
                Exponent: 65537 (0x10001)
        X509v3 extensions:
            X509v3 Basic Constraints: 
                CA:FALSE
            X509v3 Subject Key Identifier: 
                56:19:A1:BA:91:22:9C:E0:84:71:47:64:A2:CD:F9:28:C0:C0:EB:67
            X509v3 Authority Key Identifier: 
                keyid:97:C8:DC:C8:EE:AF:E2:70:C4:09:9B:19:50:8F:86:1D:2C:FF:6E:26
                DirName:/C=DE/ST=Berlin/L=Berlin/O=BigchainDB GmbH/OU=ENG/CN=TEST-CA/emailAddress=dev@bigchaindb.com
                serial:A4:C4:DF:DB:1A:DB:83:C7

            X509v3 Extended Key Usage: 
                TLS Web Client Authentication
            X509v3 Key Usage: 
                Digital Signature
    Signature Algorithm: sha256WithRSAEncryption
         18:50:cd:6d:2b:0f:aa:e4:25:1e:b9:16:1f:b5:39:17:b7:5c:
         d8:c0:a6:97:17:3d:0b:39:6f:5f:d2:2c:42:c1:6f:06:e8:72:
         a1:f6:ee:40:47:6c:d6:f0:84:dc:4d:67:07:e9:4b:dc:fe:5c:
         05:a4:af:54:ac:92:f3:14:48:4a:e1:28:b0:cb:7e:3b:68:da:
         98:b7:08:44:16:30:a8:94:32:1c:f8:2b:6a:ab:01:95:e9:10:
         a1:b6:bd:08:ee:0d:27:be:95:ed:9b:ce:e0:70:e8:b2:7d:9b:
         c9:4b:18:33:09:1b:91:78:29:f5:22:2f:59:18:40:95:ea:6b:
         3c:e9:e6:30:ab:f1:e2:ab:a2:0b:97:30:a1:39:f5:5f:4b:97:
         f2:7d:54:e8:51:85:19:8e:09:69:93:5e:96:40:79:74:45:6f:
         93:dd:47:55:1e:7d:76:8d:ad:84:3d:d6:f4:4e:a0:62:59:e3:
         62:98:2c:c7:44:21:aa:5c:77:71:ef:8a:25:16:d9:dc:ab:32:
         d1:da:aa:86:40:a4:2f:07:4a:bf:f0:45:83:8d:fe:0b:89:e6:
         c9:88:42:0a:5c:ea:ba:b1:e2:e5:22:e0:17:74:7e:ae:ec:d4:
         2c:0d:4e:35:69:7b:a5:89:c6:a6:b0:44:24:b4:12:02:5c:ad:
         40:ae:ae:e2:8f:e1:aa:25:89:32:d8:ab:1e:37:00:a3:2c:43:
         e2:cd:ad:8e:91:97:14:61:ff:dd:48:6f:8e:0f:07:8c:9d:c0:
         dd:bc:c8:c6:4f:eb:33:d8:40:64:bb:82:56:75:78:0c:d7:40:
         9b:12:ea:2a:82:ef:70:cf:75:3e:75:45:80:18:70:c1:10:41:
         5b:7f:32:fe:f0:cc:e7:98:56:c7:7e:b3:99:a7:6a:37:1d:80:
         0d:0f:26:56:12:b9:9e:64:8b:90:39:5e:2b:f4:01:c2:9b:fc:
         34:4d:c1:be:c4:44:54:3b:f9:b9:0b:2c:ad:ac:04:f1:be:6a:
         74:70:0f:a4:fb:86:1f:81:a6:3f:69:ed:96:52:0e:1f:32:5e:
         49:8a:9d:26:2c:15:62:3a:9a:bf:da:2d:4c:31:36:7f:93:5e:
         27:b0:f4:dd:13:44:18:70:f2:97:0a:a6:69:ed:63:34:f1:fc:
         94:a1:1f:3f:1c:e2:a1:fa:4a:8d:a2:9c:46:5b:8f:d8:e6:d9:
         9f:34:d8:97:84:3f:09:be:66:74:1a:51:96:73:52:80:9c:51:
         ad:78:18:15:54:90:3a:1c:18:61:90:77:b0:10:b3:18:5b:77:
         11:f3:1e:18:12:08:dd:95:22:d4:41:06:96:2a:b5:11:8c:3f:
         33:71:32:99:12:de:42:29
-----BEGIN CERTIFICATE-----
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
-----END CERTIFICATE-----"""

test_bdb_ssl_key_file="""-----BEGIN PRIVATE KEY-----
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
ygiQ48fCpPjwXP/+v5TyNchX2aTRCqA=
-----END PRIVATE KEY-----"""

@pytest.fixture(scope='session')
def mock_certificates(tmpdir_factory):
    config_files = [
                        {
                            'file_name': 'ca.crt',
                            'file_data': ca_crt
                        },
                        {
                            'file_name': 'crl.pem',
                            'file_data': crl_pem
                        },
                        {
                            'file_name': 'test_mdb_ssl_cert_and_key.pem',
                            'file_data': test_mdb_ssl_cert_and_key_file
                        },
                        {
                            'file_name': 'test_bdb_ssl.crt',
                            'file_data': test_bdb_ssl_cert_file
                        },
                        {
                            'file_name': 'test_bdb_ssl.key',
                            'file_data': test_bdb_ssl_key_file
                        }
                   ]
    try:
        base = tmpdir_factory.mktemp('test-ssl', numbered=True)
        for element in config_files:
            fh = base.join(element['file_name'])
            fh.write(element['file_data'])
        return base
    except Exception as generic_exception:
        print('Caught an exception: ', generic_exception)
