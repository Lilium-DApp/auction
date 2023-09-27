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

import web3
import json
import requests
import traceback
from os import environ
from modules import Logger
from modules import Auction, Bid, AuctionState
from modules import Inputs as input
from modules import Notice, Report, Voucher
from modules import Convertions as convert

NETWORK = environ["NETWORK"]
ROLLUP_SERVER = environ["ROLLUP_HTTP_SERVER_URL"]

LOGGER = Logger(level="INFO", name=__name__).logger

AUCTION: Auction = None
AUCTION_STATE = AuctionState.NOT_HAPPENING
NOTICE = Notice(rollup_server=ROLLUP_SERVER)
REPORT = Report(rollup_server=ROLLUP_SERVER)
VOUCHER = Voucher(rollup_server=ROLLUP_SERVER)

networks = json.load(open("networks.json"))

ROLLUP_ADDRESS = None
DAPP_RELAY_ADDRESS = networks[NETWORK]["DAPP_RELAY_ADDRESS"].lower()
ETHER_PORTAL_ADDRESS = networks[NETWORK]["ETHER_PORTAL_ADDRESS"].lower()
ERC20_PORTAL_ADDRESS = networks[NETWORK]["ERC20_PORTAL_ADDRESS"].lower()
ERC721_PORTAL_ADDRESS = networks[NETWORK]["ERC721_PORTAL_ADDRESS"].lower()
LILIUM_COMPANY_ADDRESS = networks[NETWORK]["LILIUM_COMPANY_ADDRESS"].lower()

LOGGER.info(f"HTTP rollup_server url is {ROLLUP_SERVER}, network is {NETWORK} and rollup address is {ROLLUP_ADDRESS}")
LOGGER.info(f'Lilium company address is {LILIUM_COMPANY_ADDRESS}, EtherPortal address is {ETHER_PORTAL_ADDRESS}, ERC20Portal address is {ERC20_PORTAL_ADDRESS} and ERC721Portal address is {ERC721_PORTAL_ADDRESS}')

def new_auction(token_address, amount: int, function_signature, sender, duration: int, reserve_price_per_token: int, timestamp: int) -> None:
    global AUCTION
    global AUCTION_STATE

    if any(arg is None for arg in [sender, duration, amount, token_address, reserve_price_per_token, timestamp]):
        REPORT.send({"payload": convert.str2hex("None of the arguments can be None in new auction")})
        raise ValueError("None of the arguments can be None")
    
    if function_signature != hex(int.from_bytes(web3.Web3().keccak(b'newAuction(uint256,uint256,uint256)')[:4], 'big')):
        REPORT.send({"payload": convert.str2hex("Function signature is not correct in new auction")})
        raise ValueError("Function signature is not correct")
    
    if AUCTION_STATE == AuctionState.HAPPENING:
        REPORT.send({"payload": convert.str2hex("There is already an auction happening in new auction")})
        raise ValueError("There is already an auction happening")
    
    if any(arg <= 0 for arg in [duration, amount, reserve_price_per_token]):
        REPORT.send({"payload": convert.str2hex("Invalid arguments: Duration, amount, and reserve price per token must be greater than 0 in new auction")})
        raise ValueError("Invalid arguments: Duration, amount, and reserve price per token must be greater than 0")
    
    try:
        AUCTION = Auction(sender=sender, duration=duration, amount=amount, token_address=token_address, reserve_price_per_token=reserve_price_per_token, timestamp=timestamp)
        AUCTION_STATE = AuctionState.HAPPENING
        return True
    except Exception as e:
        msg = f"Error {e} processing new auction"
        LOGGER.info(f"{msg}\n{traceback.format_exc()}")
        REPORT.send({"payload": convert.str2hex(msg)})
        return False

def new_bid(amount: int, function_signature, sender, erc20_interested_amount: int):
    global AUCTION
    global AUCTION_STATE

    if any(arg is None for arg in [amount, sender, erc20_interested_amount]):
        REPORT.send({"payload": convert.str2hex("None of the arguments can be None in new bid")})
        raise ValueError("None of the arguments can be None")
    
    if function_signature != hex(int.from_bytes(web3.Web3().keccak(b'newBid(uint256)')[:4], 'big')):
        REPORT.send({"payload": convert.str2hex("Function signature is not correct in new bid")})
        raise ValueError("Function signature is not correct")
    
    if AUCTION_STATE == AuctionState.NOT_HAPPENING:
        REPORT.send({"payload": convert.str2hex("There is no auction happening in new bid")})
        raise ValueError("There is no auction happening")
    
    if any(arg <= 0 for arg in [amount, sender, erc20_interested_amount]):
        REPORT.send({"payload": convert.str2hex("Invalid arguments: Amount of Ether and ERC20 interested amount must be greater than 0")})
        raise ValueError("Invalid arguments: Amount of Ether and ERC20 interested amount must be greater than 0")

    if amount / erc20_interested_amount < AUCTION.reserve_price_per_token:
        REPORT.send({"payload": convert.str2hex("Bid is lower than reserve price in new bid")})
        raise ValueError("Bid is lower than reserve price")
    
    try:
        if AUCTION.add_bid(Bid(amount, sender, erc20_interested_amount)):
            return True
    except Exception as e:
        msg = f"Error {e} processing new bid"
        LOGGER.info(f"{msg}\n{traceback.format_exc()}")
        REPORT.send({"payload": convert.str2hex(msg)})
        return False

def finish_auction(function_signature, timestamp: int):
    global AUCTION
    global AUCTION_STATE

    if any(arg is None for arg in [function_signature, timestamp]):
        REPORT.send({"payload": convert.str2hex("None of the arguments can be None in finish auction")})
        raise ValueError("None of the arguments can be None")
    
    if function_signature != hex(int.from_bytes(web3.Web3().keccak(b'finishAuction()')[:4], 'big')):
        REPORT.send({"payload": convert.str2hex("Function signature is not correct in finish auction")})
        raise ValueError("Function signature is not correct")
    
    if AUCTION_STATE == AuctionState.NOT_HAPPENING:
        REPORT.send({"payload": convert.str2hex("There is no auction happening in finish auction")})
        raise ValueError("There is no auction happening")
    
    if AUCTION.remaining_time(timestamp) > 0:
        REPORT.send({"payload": convert.str2hex("Auction is not finished in finish auction")})
        raise ValueError("Auction is not finished")
    
    try:
        vouchers = []
        selected_bids, unselected_bids, total_ether, token_address, remaining_erc20_amount, sender = AUCTION.finish(timestamp=timestamp)

        if any(arg is None for arg in [selected_bids, unselected_bids, total_ether, token_address, remaining_erc20_amount, sender ]):
            REPORT.send({"payload": convert.str2hex("None of the arguments can be None in finish auction")})
            raise ValueError("None of the arguments can be None")
        
        for selected_bid, unselected_bid in zip(selected_bids, unselected_bids):
            voucher_selected = VOUCHER.create_erc20_transfer_voucher(selected_bid.sender, selected_bid.erc20_interested_amount, token_address)
            voucher_unselected = VOUCHER.create_ether_voucher(unselected_bid.sender, unselected_bid.ether_amount, ROLLUP_ADDRESS)

            LOGGER.info(f"partially accepted bid from {unselected_bid.sender} with {unselected_bid.ether_amount} wei and {unselected_bid.erc20_interested_amount} tokens")
            vouchers.append(voucher_selected)
            vouchers.append(voucher_unselected)

        vouchers.append(VOUCHER.create_ether_voucher(sender, total_ether, ROLLUP_ADDRESS))

        if remaining_erc20_amount > 0:
            vouchers.append(VOUCHER.create_erc20_transfer_voucher(sender, remaining_erc20_amount, token_address))

        AUCTION_STATE = AuctionState.NOT_HAPPENING

        return vouchers
    
    except Exception as e:
        msg = f"Error {e} processing finish auction"
        LOGGER.info(f"{msg}\n{traceback.format_exc()}")
        REPORT.send({"payload": convert.str2hex(msg)})
        return None, None, None

def handle_advance(data):
    global ROLLUP_ADDRESS

    LOGGER.info(f"Received advance request data {data}")
    try:
        vouchers = []
        payload = data["payload"]
        unknown_ether_deposit_withdrawal = None
        unknown_erc20_deposit_withdrawal = None
        binary = convert.hex2binary(payload)
        sender = data["metadata"]["msg_sender"]
        timestamp = data["metadata"]["timestamp"]

        if data['metadata']['msg_sender'] == DAPP_RELAY_ADDRESS:
            ROLLUP_ADDRESS = payload
            LOGGER.info(f"Set rollup_address {ROLLUP_ADDRESS}")
            NOTICE.send({"payload": convert.str2hex(f"Set rollup_address {ROLLUP_ADDRESS}")})

        elif data["metadata"]["msg_sender"] == ETHER_PORTAL_ADDRESS:
            decoded_data = input.decode_ether_deposit(binary)
            if new_bid(amount=decoded_data["amount"], function_signature=decoded_data["function_signature"], sender=decoded_data["sender"], erc20_interested_amount=decoded_data["erc20_interested_amount"]):
                NOTICE.send({"payload": convert.str2hex(f"New bid from {decoded_data['sender']}")})

        elif data["metadata"]["msg_sender"] == ERC20_PORTAL_ADDRESS:
            decoded_data = input.decode_erc20_deposit(binary)
            if new_auction(token_address=decoded_data["token_address"], amount=decoded_data["amount"], function_signature=decoded_data["function_signature"], sender=decoded_data["sender"], duration=decoded_data["duration"], reserve_price_per_token=decoded_data["reserve_price_per_token"], timestamp=timestamp):
                NOTICE.send({"payload": convert.str2hex(f"New auction from {decoded_data['sender']}")})
        
        elif data["metadata"]["msg_sender"] == LILIUM_COMPANY_ADDRESS:
            decoded_data = input.decode_finish_auction(binary)
            vouchers = finish_auction(decoded_data["function_signature"], timestamp)
            NOTICE.send({"payload": convert.str2hex(f"Finish auction")})
                
        else:
            try:
                decoded_data = input.decode_ether_deposit(binary)
                unknown_ether_deposit_withdrawal = VOUCHER.create_ether_voucher(decoded_data["sender"], decoded_data["amount"])
                LOGGER.info(f"Sender {sender} is unknown, creating voucher to withdraw {decoded_data['amount']} wei to {decoded_data['sender']}")
            except:
                try:
                    decoded_data = input.decode_erc20_deposit(binary)
                    unknown_erc20_deposit_withdrawal = VOUCHER.create_erc20_transfer_voucher(decoded_data["sender"], decoded_data["amount"], decoded_data["token_address"])
                    LOGGER.info(f"Sender {sender} is unknown, creating voucher to withdraw {decoded_data['amount']} tokens to {decoded_data['sender']}")
                except Exception as e:
                    msg = f"Error {e} processing data {data}"
                    LOGGER.error(f"{msg}\n{traceback.format_exc()}")
                    REPORT.send({"payload": convert.str2hex(msg)})
                    return "reject"
            
        if vouchers:
            for voucher in vouchers:
                VOUCHER.send(voucher)
                
        if unknown_ether_deposit_withdrawal:
            VOUCHER.send(unknown_ether_deposit_withdrawal)
            LOGGER.info(f"Created voucher to withdraw unknown sender to {decoded_data['sender']}")

        if unknown_erc20_deposit_withdrawal:
            VOUCHER.send(unknown_erc20_deposit_withdrawal)
            LOGGER.info(f"Created voucher to withdraw unknown sender to {decoded_data['sender']}")
        return "accept"

    except Exception as e:
        msg = f"Error {e} processing data {data}"
        LOGGER.error(f"{msg}\n{traceback.format_exc()}")
        REPORT.send({"payload": convert.str2hex(msg)})
        return "reject"

def handle_inspect(data):
    global AUCTION_STATE

    LOGGER.info(f"Received inspect request data {data}")
    data_decoded = convert.hex2binary(data["payload"]).decode('utf-8')
    try:
        if data_decoded == "status":
            REPORT.send({"payload": convert.str2hex(f'The Auction dApp state is {AUCTION_STATE.name} and the number of bids is {len(AUCTION.bids)}')})
            return "accept"
        else:
            raise Exception(
                f"Unknown payload {data['payload']}, send 'status' to get current state")

    except Exception as e:
        msg = f"Error {e} processing data {data}"
        LOGGER.error(f"{msg}\n{traceback.format_exc()}")
        REPORT.send({"payload": convert.str2hex(msg)})
        return "reject"

handlers = {
    "advance_state": handle_advance,
    "inspect_state": handle_inspect,
}

finish = {"status": "accept"}

while True:
    LOGGER.info("Sending finish")
    response = requests.post(ROLLUP_SERVER + "/finish", json=finish)
    LOGGER.info(f"Received finish status {response.status_code}")
    if response.status_code == 202:
        LOGGER.info("No pending rollup request, trying again")
    else:
        rollup_request = response.json()
        data = rollup_request["data"]
        handler = handlers[rollup_request["request_type"]]
        finish["status"] = handler(rollup_request["data"])