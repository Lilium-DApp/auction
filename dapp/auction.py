# Copyright 2022 Cartesi Pte. Ltd.
#
# SPDX-License-Identifier: Apache-2.0
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use
# this file except in compliance with the License. You may obtain a copy of the
# License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

from os import environ
import traceback
import logging
import requests
from time import sleep
import json
from eth_abi import encode
import re
from eth_abi_ext import decode_packed
from enum import Enum
import web3



class AUCTION_STATE(Enum):
    HAPPENING = 0
    NOT_HAPPENING = 1


STATE = AUCTION_STATE.NOT_HAPPENING


class Bid:
    def __init__(self, sender, value):
        self.value = value
        self.sender = sender

class Auction:
    def __init__(self, agent, duration, reserve_price_per_token, quantity, timestamp_init, token_address):
        self.agent = agent
        self.duration = duration
        self.reserve_price_per_token = reserve_price_per_token
        self.quantity = quantity
        self.timestamp_init = timestamp_init
        self.token_address = token_address
        self.bids = []

    def add_bid(self, bid: Bid):
        if bid.value >= self.reserve_price_per_token * self.quantity:
            self.bids.append(bid)
        else:
            logger.info(f"Bid is less than reserve price")
            return "Bid is less than reserve price"

    def finish(self, timestamp_finish):
        if timestamp_finish >= self.timestamp_init + self.duration:
            if self.bids:
                max_bid = max(self.bids, key=lambda bid: bid.value)
                return max_bid, self.token_address, self.quantity, self.bids
            else:
                logger.info(f"Time is up and no bids were received")
                return None, None, None, None
        else:
            logger.info(f"Auction has not finished yet")
            return "Auction has not finished yet"

    def remaining_time(self, timestamp):
        return self.timestamp_init + self.duration - timestamp
    
AUCTION: Auction = None


logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

rollup_server = environ["ROLLUP_HTTP_SERVER_URL"]
logger.info(f"HTTP rollup_server url is {rollup_server}")

NETWORK = environ["NETWORK"]
logger.info(f"NETWORK is {NETWORK}")

networks = json.load(open("networks.json"))

DAPP_RELAY_ADDRESS = networks[NETWORK]["DAPP_RELAY_ADDRESS"].lower()
ETHER_PORTAL_ADDRESS = networks[NETWORK]["ETHER_PORTAL_ADDRESS"].lower()
ERC20_PORTAL_ADDRESS = networks[NETWORK]["ERC20_PORTAL_ADDRESS"].lower()
ERC721_PORTAL_ADDRESS = networks[NETWORK]["ERC721_PORTAL_ADDRESS"].lower()
LILIUM_COMPANY_ADDRESS = networks[NETWORK]["LILIUM_COMPANY_ADDRESS"].lower()


rollup_address = None

w3 = web3.Web3()


###
# Aux Functions 

def str2hex(string):
    """
    Encode a string as an hex string
    """
    return binary2hex(str2binary(string))

def str2binary(string):
    """
    Encode a string as an binary string
    """
    return string.encode("utf-8")

def binary2hex(binary):
    """
    Encode a binary as an hex string
    """
    return "0x" + binary.hex()

def hex2binary(hexstr):
    """
    Decodes a hex string into a regular byte string
    """
    return bytes.fromhex(hexstr[2:])

def hex2str(hexstr):
    """
    Decodes a hex string into a regular string
    """
    return hex2binary(hexstr).decode("utf-8")

def send_notice(notice: str) -> None:
    send_post("notice", notice)

def send_voucher(voucher):
    send_post("voucher",voucher)

def send_report(report):
    send_post("report",report)

def send_post(endpoint,json_data):
    response = requests.post(rollup_server + f"/{endpoint}", json=json_data)
    logger.info(f"/{endpoint}: Received response status {response.status_code} body {response.content}")


###
# Selector of functions for solidity <contract>.call(<payload>)

# ERC-20 contract function selector to be called during the execution of a voucher,
#   which corresponds to the first 4 bytes of the Keccak256-encoded result of "transfer(address,uint256)"
ERC20_TRANSFER_FUNCTION_SELECTOR = hex2binary(w3.keccak(b'transfer(address,uint256)')[:4].hex())

# ERC-721 contract function selector to be called during the execution of a voucher,
#   which corresponds to the first 4 bytes of the Keccak256-encoded result of "safeTransferFrom(address,address,uint256)"
ERC721_SAFETRANSFER_FUNCTION_SELECTOR = hex2binary(w3.keccak(b'safeTransferFrom(address,address,uint256)')[:4].hex())

# EtherPortalFacet contract function selector to be called during the execution of a voucher,
#   which corresponds to the first 4 bytes of the Keccak256-encoded result of "etherWithdrawal(bytes)", as defined at
#   https://github.com/cartesi/rollups/blob/v0.8.2/onchain/rollups/contracts/interfaces/IEtherPortal.sol
ETHER_WITHDRAWAL_FUNCTION_SELECTOR = hex2binary(w3.keccak(b'withdrawEther(address,uint256)')[:4].hex())


NEW_AUCTION_FUNCTION_SIGNATURE = hex(int.from_bytes(
    w3.keccak(b'newAuction(uint256,uint256,uint256)')[:4], 'big'))
NEW_BID_FUNCTION_SIGNATURE = hex(int.from_bytes(
    w3.keccak(b'newBid(uint256)')[:4], 'big'))
FINISH_AUCTION_FUNCTION_SIGNATURE = hex(int.from_bytes(
    w3.keccak(b'finishAuction()')[:4], 'big'))

###
# Decode Aux Functions 

def decode_erc20_deposit(binary):
    ret = binary[:1]
    token_address = binary[1:21]
    depositor = binary[21:41]
    amount = int.from_bytes(binary[41:73], "big")
    function_signature = binary[73:77]
    data = decode_packed(['address', 'uint256', 'uint256'], binary[77:])
    erc20_deposit = {
        "depositor": binary2hex(depositor),
        "token_address": binary2hex(token_address),
        "amount": amount,
        "function_signature": binary2hex(function_signature),
        "sender": data[0],
        "duration": data[1],
        "reserve_price_per_token": data[2]
    }
    logger.info(erc20_deposit)
    return erc20_deposit

def decode_ether_deposit(binary):
    depositor = binary[:20]
    amount = int.from_bytes(binary[20:52], "big")
    function_signature = binary[52:56]
    data = decode_packed(['address', 'uint256'],binary[56:])
    ether_deposit = {
        "depositor": binary2hex(depositor),
        "amount": amount,
        "function_signature": binary2hex(function_signature),
        "sender": data[0],
        "interested_quantity": data[1]
    }
    logger.info(ether_deposit)
    return ether_deposit

def decode_finish_auction(binary):
    function_signature = binary[:4]
    finish_auction = {
        "function_signature": binary2hex(function_signature),
    }
    logger.info(finish_auction)
    return finish_auction


###
# Create Voucher Aux Functions 

def create_erc20_transfer_voucher(token_address,receiver,amount):
    # Function to be called in voucher [token_address].transfer([address receiver],[uint256 amount])
    data = encode(['address', 'uint256'], [receiver,amount])
    voucher_payload = binary2hex(ERC20_TRANSFER_FUNCTION_SELECTOR + data)
    voucher = {"destination": token_address, "payload": voucher_payload}
    return voucher

def create_ether_withdrawal_voucher(receiver,amount):
    # Function to be called in voucher [rollups_address].etherWithdrawal(bytes) where bytes is ([address receiver],[uint256 amount])
    data = encode(['address', 'uint256'], [receiver,amount])
    voucher_payload = binary2hex(ETHER_WITHDRAWAL_FUNCTION_SELECTOR + data)
    voucher = {"destination": rollup_address, "payload": voucher_payload}
    return voucher

###
# 
def process_new_auction(wallet, duration, reserve_price_per_token, quantity, timestamp_init, token_address):
    global AUCTION
    global STATE
    if STATE == AUCTION_STATE.HAPPENING:
        logger.info(f"Auction already happening. Current state: {STATE.name}")
        return
    else:
        AUCTION= Auction(wallet, duration, reserve_price_per_token, quantity, timestamp_init, token_address)
        STATE = AUCTION_STATE.HAPPENING
        logger.info(f"New auction started. Current state: AUCTION_{STATE.name}")


def process_new_bid(wallet, value):
    global AUCTION
    global STATE
    if STATE == AUCTION_STATE.NOT_HAPPENING:
        logger.info(f"Auction not happening. Current state: {STATE.name}")
        return
    else:
        AUCTION.add_bid(Bid(wallet, value))
        logger.info(f"New bid added. Current state: AUCTION_{STATE.name}")

def process_finish_auction(timestamp_finish):
    global AUCTION
    global STATE
    if STATE == AUCTION_STATE.NOT_HAPPENING:
        logger.info(f"Auction not happening. Current state: {STATE.name}")
        return
    else:
        max_bid, token_address, erc20_value, bids = AUCTION.finish(timestamp_finish)
        if max_bid:
            voucher_bidder = create_erc20_transfer_voucher(token_address, max_bid.sender, erc20_value)
            voucher_seller = create_ether_withdrawal_voucher(AUCTION.agent, max_bid.value)
            vouchers = [voucher_bidder, voucher_seller]
            for loser in bids:
                if loser!= max_bid:
                    voucher_loser = create_ether_withdrawal_voucher(loser.sender, loser.value)
                    vouchers.append(voucher_loser)
                    logger.info(f'The loser {loser.sender} was refunded with {loser.value}')
            print(vouchers)
            return vouchers

        elif not bids:
            voucher = []
            logger.info(f'No bids received')
            voucher_withdrawal = create_erc20_transfer_voucher(token_address, AUCTION.agent, erc20_value)
            voucher.append(voucher_withdrawal)
            return voucher
        STATE = AUCTION_STATE.NOT_HAPPENING
        logger.info(f"Auction finished. Current state: AUCTION_{STATE.name}")


###
# handlers

def handle_advance(data):
    global rollup_address
    logger.info(f"Received advance request data {data}. Current rollup_address: {rollup_address}")
    
    try:
        vouchers = []
        payload = data["payload"]
        binary = hex2binary(payload)
        sender = data["metadata"]["msg_sender"]
        timestamp = data["metadata"]["timestamp"]

        # # Check whether an input was sent by the relay
        if data['metadata']['msg_sender'] == DAPP_RELAY_ADDRESS:
            rollup_address = payload
            logger.info(f"Set rollup_address {rollup_address}")
            send_report({"payload": str2hex(f"Set rollup_address {rollup_address}")})

        elif data["metadata"]["msg_sender"] == ETHER_PORTAL_ADDRESS:
            decoded_data = decode_ether_deposit(binary)
            if decoded_data["function_signature"] == NEW_BID_FUNCTION_SIGNATURE:
                process_new_bid(decoded_data["sender"], decoded_data["amount"])
                logger.info(f'New bid received from {decoded_data["sender"]} with value {decoded_data["amount"]}')
                send_report({"payload": str2hex(f'New bid received from {decoded_data["sender"]} with value {decoded_data["amount"]}')})

        elif data["metadata"]["msg_sender"] == ERC20_PORTAL_ADDRESS:
            decoded_data = decode_erc20_deposit(binary)
            if decoded_data["function_signature"] == NEW_AUCTION_FUNCTION_SIGNATURE:
                process_new_auction(decoded_data["sender"], decoded_data["duration"], decoded_data["reserve_price_per_token"], decoded_data["amount"], timestamp, decoded_data["token_address"])
                logger.info(f'New auction received from {decoded_data["sender"]} with duration {decoded_data["duration"]}, reserve_price_per_token {decoded_data["reserve_price_per_token"]} and quantity {decoded_data["amount"]}')
                send_report({"payload": str2hex(f'New auction received from {decoded_data["sender"]} with duration {decoded_data["duration"]}, reserve_price_per_token {decoded_data["reserve_price_per_token"]} and quantity {decoded_data["amount"]}')})
        
        elif data["metadata"]["msg_sender"] == LILIUM_COMPANY_ADDRESS:
            decoded_data = decode_finish_auction(binary)
            if decoded_data["function_signature"] == FINISH_AUCTION_FUNCTION_SIGNATURE:
                vouchers = process_finish_auction(timestamp)
        else:
            logger.info(
                f"Sender {sender} is unknown")
        if vouchers:
            for voucher in vouchers:
                send_voucher(voucher)
        return "accept"

    except Exception as e:
        msg = f"Error {e} processing data {data}"
        logger.error(f"{msg}\n{traceback.format_exc()}")
        send_report({"payload": str2hex(msg)})
        return "reject"

def handle_inspect(data):
    global STATE
    logger.info(f"Received inspect request data {data}")
    data_decoded = hex2binary(data["payload"]).decode('utf-8')
    try:
        if data_decoded == "status":
            send_report({"payload": str2hex(STATE.name)})
            return "accept"
        else:
            raise Exception(
                f"Unknown payload {data['payload']}, send 'status' to get current state")

    except Exception as e:
        msg = f"Error {e} processing data {data}"
        logger.error(f"{msg}\n{traceback.format_exc()}")
        send_report({"payload": str2hex(msg)})
        return "reject"


handlers = {
    "advance_state": handle_advance,
    "inspect_state": handle_inspect,
}

###
# Main Loop

finish = {"status": "accept"}

while True:
    logger.info("Sending finish")
    response = requests.post(rollup_server + "/finish", json=finish)
    logger.info(f"Received finish status {response.status_code}")
    if response.status_code == 202:
        logger.info("No pending rollup request, trying again")
    else:
        rollup_request = response.json()
        data = rollup_request["data"]
        handler = handlers[rollup_request["request_type"]]
        finish["status"] = handler(rollup_request["data"])