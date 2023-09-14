import web3
import requests
from math import floor
from eth_abi import encode
from modules.log import Logger
from modules.convertions import Convertions as convert

LOGGER = Logger(level="INFO", name=__name__).logger

class Base:
    rollup_server = None

    def __init__(self, rollup_server=None):
        Base.rollup_server = rollup_server

    @property
    def rollup_server(self):
        return Base.rollup_server

    @classmethod
    def send_request(cls, endpoint, json_data):
        try:
            response = requests.post(f"{cls.rollup_server}/{endpoint}", json=json_data)
            LOGGER.info(f"/{endpoint}: Received response status {response.status_code} body {response.content}")  
        except requests.exceptions.RequestException as e:
            LOGGER.info(f"Failed to send request to /{endpoint}: {e}") 

class Voucher(Base):
    def __init__(self, rollup_server = None):
        super().__init__(rollup_server=rollup_server)

    ERC20_TRANSFER_FUNCTION_SELECTOR = convert.hex2binary(web3.Web3().keccak(b'transfer(address,uint256)')[:4].hex())
    ETHER_WITHDRAWAL_FUNCTION_SELECTOR = convert.hex2binary(web3.Web3().keccak(b'withdrawEther(address,uint256)')[:4].hex())

    @classmethod
    def create_erc20_transfer_voucher(cls, receiver, amount: int, token_address):
        data = encode(['address', 'uint256'], [receiver, amount])
        voucher_payload = convert.binary2hex(cls.ERC20_TRANSFER_FUNCTION_SELECTOR + data)
        voucher = {"destination": token_address, "payload": voucher_payload}
        Logger.logger.info(f"Created voucher {voucher}")
        return voucher

    @classmethod
    def create_ether_voucher(cls, receiver, amount: int, rollup_address):
        data = encode(['address', 'uint256'], [receiver, amount])
        voucher_payload = convert.binary2hex(cls.ETHER_WITHDRAWAL_FUNCTION_SELECTOR + data)
        voucher = {"destination": rollup_address, "payload": voucher_payload}
        Logger.logger.info(f"Created voucher {voucher}")
        return voucher

    @classmethod
    def send(cls, json_data: dict):
        LOGGER.info(f"Sending voucher {json_data}")
        cls.send_request("voucher", json_data)


class Notice(Base):
    def __init__(self, rollup_server):
        super().__init__(rollup_server=rollup_server)

    @classmethod
    def send(cls, json_data: dict):
        LOGGER.info(f"Sending notice {json_data}")
        cls.send_request("notice", json_data)


class Report(Base):
    def __init__(self, rollup_server=None):
        super().__init__(rollup_server=rollup_server)

    @classmethod
    def send(cls, json_data: dict):
        LOGGER.info(f"Sending report {json_data}")
        cls.send_request("report", json_data)
