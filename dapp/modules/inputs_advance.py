import logging
from modules.convertions import Convertions
from modules.eth_abi_ext import decode_packed


logging.basicConfig(level="INFO")

logger = logging.getLogger(__name__)

class InputsAdvance:
    @staticmethod
    def decode_default_input(binary) -> dict:
        logger.info("Default input")
        return {"data": binary}

    @staticmethod
    def decode_erc20(binary) -> dict:
        ret = binary[:1]
        token_address = binary[1:21]
        depositor = binary[21:41]
        amount = int.from_bytes(binary[41:73], "big")
        data = binary[73:]
        erc20_deposit = {
            "depositor": Convertions.binary2hex(depositor),
            "token_address": Convertions.binary2hex(token_address),
            "amount": amount,
            "data": decode_packed(["uint256", "uint256"], data)
        }
        logger.info(erc20_deposit)
        return erc20_deposit

    @staticmethod
    def decode_ether(binary) -> dict:
        depositor = binary[:20]
        amount = int.from_bytes(binary[20:52], "big")
        data = binary[52:]
        ether_deposit = {
            "depositor": Convertions.binary2hex(depositor),
            "amount": amount,
            "data": decode_packed(["uint256"], data)
        }
        logger.info(ether_deposit)
        return ether_deposit
    
    @staticmethod
    def decode_heartbeat(binary):
        timestamp = decode_packed(["uint256"], binary)
        logger.info(timestamp)
        return timestamp