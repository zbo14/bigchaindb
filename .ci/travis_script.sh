#!/bin/bash

set -e -x

if [[ -n ${TOXENV} ]]; then
  tox -e ${TOXENV}
elif [[ "${BIGCHAINDB_DATABASE_BACKEND}" == mongodb ]]; then
  pytest -v --database-backend=mongodb --cov=bigchaindb
  # TODO Run separate tests for different features, ex. for ssl and non-ssl tests
  #pytest -v --database-backend=mongodb --cov=bigchaindb -m bdb
  #pytest -v --database-backend=mongodb-ssl --cov=bigchaindb -m bdb_ssl
else
  pytest -v -n auto --cov=bigchaindb
fi
