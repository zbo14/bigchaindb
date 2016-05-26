from __future__ import with_statement, unicode_literals

import time

from fabric.api import sudo, env, hosts
from fabric.api import task, parallel
from fabric.contrib.files import sed
from fabric.operations import run, put
from fabric.context_managers import settings

from hostlist import public_dns_names

# Ignore known_hosts
# http://docs.fabfile.org/en/1.10/usage/env.html#disable-known-hosts
env.disable_known_hosts = True

# What remote servers should Fabric connect to? With what usernames?
env.user = 'ubuntu'
env.hosts = public_dns_names

# SSH key files to try when connecting:
# http://docs.fabfile.org/en/1.10/usage/env.html#key-filename
env.key_filename = 'pem/bigchaindb.pem'


@task
@parallel
def put_benchmark_utils():
    put('benchmark_utils.py')


@task
@parallel
def put_zmq():
    put('../zmq-tests/task_ventilator.py')
    put('../zmq-tests/worker_blocks.py')
    put('../zmq-tests/worker_validator.py')


@task
@parallel
def start_zmq_validators():
    run('python3 worker_validator.py 20')


@task
@parallel
def start_zmq_block():
    run('python3 worker_blocks.py')


@task
@parallel
def start_zmq_task():
    run('python3 task_ventilator.py')


@task
@parallel
def kill():
    run('killall python3')


@task
@parallel
def put_bottleneck_tests():
    put('bottleneck_tests.py')


@task
@parallel
def run_bottleneck_tests():
    run('python3 bottleneck_tests.py')


@task
@parallel
def set_statsd_host(statsd_host='localhost'):
    run('python3 benchmark_utils.py set-statsd-host {}'.format(statsd_host))
    print('update configuration')
    run('bigchaindb show-config')


@task
@parallel
def prepare_backlog(num_transactions=10000):
    run('python3 benchmark_utils.py add-backlog {}'.format(num_transactions))


@task
@parallel
def start_bigchaindb():
    run('bigchaindb start')


@task
@parallel
def kill_bigchaindb():
    run('killall bigchaindb')


@task
@parallel
def set_vmmap():
    sudo('echo 262144 > /proc/sys/vm/max_map_count')
