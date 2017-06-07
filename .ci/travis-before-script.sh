#!/bin/bash

set -e -x

if [[ "${TOXENV}" == *-rdb ]]; then
    rethinkdb --daemon
elif [[ "${BIGCHAINDB_DATABASE_BACKEND}" == mongodb ]]; then
    wget http://downloads.mongodb.org/linux/mongodb-linux-x86_64-3.4.1.tgz -O /tmp/mongodb.tgz
    tar -xvf /tmp/mongodb.tgz
    mkdir /tmp/mongodb-data
    # Start a non-TLS/SSL instance on default port 27017
    ${PWD}/mongodb-linux-x86_64-3.4.1/bin/mongod --dbpath=/tmp/mongodb-data --replSet=bigchain-rs &> /dev/null &
    # Start a TLS/SSL instance on port 37017
    ${PWD}/mongodb-linux-x86_64-3.4.1/bin/mongod \
        --port=37017 \
        --dbpath=/tmp/mongodb-ssl-data \
        --replSet=bigchain-rs \
        --sslMode=requireSSL \
        --sslAllowInvalidHostnames \
        --sslPEMKeyFile=$TRAVIS_BUILD_DIR/tests/backend/mongodb/certs/test_mdb_ssl_cert_and_key.pem \
        --sslCAFile=$TRAVIS_BUILD_DIR/tests/backend/mongodb/certs/ca.crt \
        --sslPEMKeyPassword="" \
        --sslCRLFile=$TRAVIS_BUILD_DIR/tests/backend/mongodb/certs/crl.pem &> /dev/null &
fi
