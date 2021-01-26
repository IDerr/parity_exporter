# coding=utf-8
import datetime
import logging
import os 
import requests
import time
from prometheus_client import start_http_server, Summary, Gauge

# Env Variables
RPC_ADDRESS = os.environ.get('RPC_ADDRESS', 'http://localhost:8545')
EXPORTER_PORT = int(os.environ.get('EXPORTER_PORT', 8000))
RUN_INTERVAL = int(os.environ.get('RUN_INTERVAL', 10))

REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')
ETH_BLOCK_NUMBER = Gauge('parity_eth_block_number', 'The number of most recent block.')
PEERS = Gauge('parity_peers', 'The number of peers currently connected to the client.', ['status'])
PARITY_VERSION = Gauge('parity_version', 'Client version')
PARITY_SYNCING = Gauge('parity_syncing', 'Is the client syncing ?')
GAS_PRICE = Gauge('parity_gas_price', 'Current gas price of the chain')

class RPCError(Exception):
    pass

# Thanks @dysnix for the class
class Parity:
    JSONRPC_VER = "2.0"

    def __init__(self, rpc_url):
        self.rpc_url = rpc_url

    def make_request(self, method, params=None):
        if params is None:
            params = []
        timestamp = int(datetime.datetime.now().timestamp())

        data = {
            'id': timestamp,
            'method': method,
            'params': params,
            'jsonrpc': self.JSONRPC_VER
        }

        try:
            result = requests.post(self.rpc_url, json=data).json()
        except Exception as e:
            logging.error('Error make request {}: {}'.format(method, e))
            raise RPCError('Error call {}'.format(method))

        try:
            return result['result']
        except:
            logging.error('Error get result for call {}'.format(method))
            raise RPCError('Error call {}'.format(method))

    def eth_blockNumber(self):
        result = self.make_request('eth_blockNumber')
        return int(result, 0)

    def peers(self):
        result = self.make_request('parity_netPeers')
        return len(result['peers']), int(result['active']), int(result['connected'])

    def version(self):
        result = self.make_request('web3_clientVersion')
        return result

    def chain(self):
        result = self.make_request('parity_chain')
        return result

    def is_syncing(self):
        result = self.make_request('eth_syncing')
        return result

    def gas_price(self):
        result = self.make_request('eth_gasPrice')
        return int(result, 0)

def update_metrics(parity):
    # RPC Calls
    total_peers, active_peers, connected_peers = parity.peers()
    version = parity.version()
    is_syncing = parity.is_syncing()
    gas_price = parity.gas_price()
    block_number = parity.eth_blockNumber()
    # Variable set
    PARITY_VERSION.set(version)
    PARITY_SYNCING.set(is_syncing)
    PEERS.labels('total').set(total_peers)
    PEERS.labels('active').set(active_peers)
    PEERS.labels('connected').set(connected_peers)
    ETH_BLOCK_NUMBER.set(block_number)
    GAS_PRICE.set(gas_price)
    logging.info('Metrics updated')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    p = Parity(RPC_ADDRESS)
    start_http_server(EXPORTER_PORT)

    while True:
        update_metrics(p)
        time.sleep(RUN_INTERVAL)