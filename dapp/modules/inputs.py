from modules.log import Logger
from modules.outputs import Report
from modules.eth_abi_ext import decode_packed
from modules.convertions import Convertions as convert

LOGGER = Logger(level="INFO", name=__name__).logger

class Inputs(Report):

    def __init__(rollup_server):
        Report.__init__(rollup_server=rollup_server)

    @classmethod
    def decode_erc20_deposit(cls, binary):
        ret = binary[:1]
        token_address = binary[1:21]
        depositor = binary[21:41]
        amount = int.from_bytes(binary[41:73], "big")
        function_signature = binary[73:77]
        data = decode_packed(['address', 'uint256', 'uint256'], binary[77:])
        erc20_deposit = {
            "depositor": convert.binary2hex(depositor),
            "token_address": convert.binary2hex(token_address),
            "amount": amount,
            "function_signature": convert.binary2hex(function_signature),
            "sender": data[0],
            "duration": data[1],
            "reserve_price_per_token": data[2]
        }
        cls.send({"payload": convert.str2hex(f"Decode new erc20 deposit {erc20_deposit}")})
        LOGGER.info(f'erc20_deposit: {erc20_deposit}')
        return erc20_deposit

    @classmethod
    def decode_ether_deposit(cls, binary):
        depositor = binary[:20]
        amount = int.from_bytes(binary[20:52], "big")
        function_signature = binary[52:56]
        data = decode_packed(['address', 'uint256'],binary[56:])
        ether_deposit = {
            "depositor": convert.binary2hex(depositor),
            "amount": amount,
            "function_signature": convert.binary2hex(function_signature),
            "sender": data[0],
            "erc20_interested_amount": data[1]
        }
        cls.send({"payload": convert.str2hex(f"Decode new ether deposit {ether_deposit}")})
        LOGGER.info(ether_deposit)
        return ether_deposit

    @classmethod
    def decode_finish_auction(cls, binary):
        function_signature = binary[:4]
        finish_auction = {
            "function_signature": convert.binary2hex(function_signature),
        }
        cls.send({"payload": convert.str2hex(f"Decode finish auction {finish_auction}")})
        LOGGER.info(finish_auction)
        return finish_auction