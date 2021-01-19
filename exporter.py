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
ETH_BLOCK_NUMBER = Gauge('eth_block_number', 'The number of most recent block.')
PEERS = Gauge('peers', 'The number of peers currently connected to the client.', ['status'])

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

    def parity_net_peers(self):
        result = self.make_request('parity_netPeers')
        return len(result['peers']), int(result['active']), int(result['connected'])

# TODO: 
#   makeRequest(nodeURL, 'web3_clientVersion'),
#   makeRequest(nodeURL, 'parity_chain'),
#   makeRequest(nodeURL, 'eth_syncing'),
#   makeRequest(nodeURL, 'eth_gasPrice'),
#   makeRequest(nodeURL, 'parity_allTransactions')

def update_metrics(parity):
    total_peers, active_peers, connected_peers = parity.parity_net_peers()
    PEERS.labels('total').set(total_peers)
    PEERS.labels('active').set(active_peers)
    PEERS.labels('connected').set(connected_peers)

    ETH_BLOCK_NUMBER.set(parity.eth_blockNumber())

    logging.info('Metrics updated')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    p = Parity(RPC_ADDRESS)
    start_http_server(EXPORTER_PORT)

    while True:
        update_metrics(p)
        time.sleep(RUN_INTERVAL)