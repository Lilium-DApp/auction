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
import logging
import requests
import traceback
from os import environ
from modules import Convertions, RollupClient, InputsAdvance, OutputsAdvance, NewBid, NewAuction

logging.basicConfig(level="INFO")
LOGGER = logging.getLogger(__name__)

ROLLUP_SERVER = environ["ROLLUP_HTTP_SERVER_URL"]
ROLLUP_CLIENT = RollupClient(ROLLUP_SERVER)
LOGGER.info(f"HTTP rollup_server url is {ROLLUP_SERVER}")

NETWORK = environ["NETWORK"]
LOGGER.info(f"NETWORK is {NETWORK}")

networks = json.load(open("networks.json"))

ROLLUP_ADDRESS = None
DAPP_RELAY_ADDRESS = networks[NETWORK]["DAPP_RELAY_ADDRESS"].lower()
ETHER_PORTAL_ADDRESS = networks[NETWORK]["ETHER_PORTAL_ADDRESS"].lower()
ERC20_PORTAL_ADDRESS = networks[NETWORK]["ERC20_PORTAL_ADDRESS"].lower()
ERC721_PORTAL_ADDRESS = networks[NETWORK]["ERC721_PORTAL_ADDRESS"].lower()
LILIUM_COMPANY_ADDRESS = networks[NETWORK]["LILIUM_COMPANY_ADDRESS"].lower()

rollup_address = None

w3 = web3.Web3()

ERC20_TRANSFER_FUNCTION_SELECTOR = Convertions.hex2binary(w3.keccak(b'transfer(address,uint256)')[:4].hex())
ETHER_WITHDRAWAL_FUNCTION_SELECTOR = Convertions.hex2binary(w3.keccak(b'withdrawEther(address,uint256)')[:4].hex())

###
#  Generate Voucher Functions 

def process_deposit_and_generate_voucher(sender, payload, metadata):
    binary = Convertions.hex2binary(payload)
          
    global AUCTION

    if sender == ERC20_PORTAL_ADDRESS:
        erc20_deposit = InputsAdvance.decode_erc20(binary)

        
        if AUCTION:
            if not AUCTION.status_auction():
                ROLLUP_CLIENT.send_report({"payload": Convertions.str2hex(f"Must wait before initiating a new auction")})


       
        else:
            try:
                AUCTION = NewAuction(erc20_deposit["depositor"], erc20_deposit["amount"], erc20_deposit["data"][1] , erc20_deposit["data"][0])
                ROLLUP_CLIENT.send_report({"payload": Convertions.str2hex(f"New auction created with {AUCTION}")})
            except Exception as e:
                msg = f"Error {e} processing data {data}"
                LOGGER.error(f"{msg}\n{traceback.format_exc()}")
                ROLLUP_CLIENT.send_report({"payload": Convertions.str2hex(msg)})
                return "reject"

    elif sender == ETHER_PORTAL_ADDRESS:
        # newbid
        ether_deposit = InputsAdvance.decode_ether(binary)
        try:
            
            if  AUCTION.status_auction():
                winners = AUCTION.return_tokens()
                #report that auction has ended
                ROLLUP_CLIENT.send_report({"payload": Convertions.str2hex(f"Auction has ended")})

                   
            else:
                new_bid = NewBid(ether_deposit["depositor"],  metadata["msg_value"], ether_deposit['data'][0],metadata['timestamp'])
                AUCTION.bid(new_bid)
                ROLLUP_CLIENT.send_report({"payload": Convertions.str2hex(f"New bid created with {new_bid}")})
        except Exception as e:
            msg = f"Error {e} processing data {data}"
            LOGGER.error(f"{msg}\n{traceback.format_exc()}")
            ROLLUP_CLIENT.send_report({"payload": Convertions.str2hex(msg)})
            return "reject"

        # send deposited ether back to depositor

    elif sender == LILIUM_COMPANY_ADDRESS:
        try:
            AUCTION.update_time(metadata['timestamp'])
            if  AUCTION.status_auction():
                    withdraw_list = []
                    winners = AUCTION.return_tokens()
                    losers = [ (bid.wallet,bid.value) for bid in AUCTION.offers if bid.wallet not in winners]
                    for wallet,value in losers:
                        if rollup_address is not None:
                            receiver = wallet
                            amount = value

                            withdraw_list.append(OutputsAdvance.create_ether_withdrawal_voucher(ETHER_WITHDRAWAL_FUNCTION_SELECTOR,receiver,amount))
                    for wallet,quantity,value in winners:
                        if rollup_address is not None:
                            receiver = wallet
                            amount = quantity

                            withdraw_list.append(OutputsAdvance.create_erc20_transfer_voucher(ERC20_TRANSFER_FUNCTION_SELECTOR,receiver,amount))
                   
                    AUCTION = None
        except Exception as e:
            msg = f"Error {e} processing data {data}"
            LOGGER.error(f"{msg}\n{traceback.format_exc()}")
            ROLLUP_CLIENT.send_report({"payload": Convertions.str2hex(msg)})
            return "reject"

        return withdraw_list



    else:
        pass

    return withdraw_list


###
# handlers

def handle_advance(data):
    global rollup_address
    LOGGER.info(f"Received advance request data {data}. Current rollup_address: {rollup_address}")
    
    try:
        metadata = data["metadata"]
        payload = data["payload"]
        

        # Check whether an input was sent by the relay
        if data['metadata']['msg_sender'] == DAPP_RELAY_ADDRESS:
            rollup_address = payload
            ROLLUP_CLIENT.send_report({"payload": Convertions.str2hex(f"Set rollup_address {rollup_address}")})

        elif data["metadata"]["msg_sender"] in [ETHER_PORTAL_ADDRESS,ERC20_PORTAL_ADDRESS,LILIUM_COMPANY_ADDRESS]:
            # or was sent by the Portals, which is where deposits must come from
            voucher_list = process_deposit_and_generate_voucher(data["metadata"]["msg_sender"], payload, metadata)   
        if len(voucher_list) >0 :
            LOGGER.info(f"voucher {voucher_list}")
            ROLLUP_CLIENT.send_voucher_list(voucher_list)

        return "accept"

    except Exception as e:
        msg = f"Error {e} processing data {data}"
        LOGGER.error(f"{msg}\n{traceback.format_exc()}")
        ROLLUP_CLIENT.send_report({"payload": Convertions.str2hex(msg)})
        return "reject"

def handle_inspect(data):
    LOGGER.info(f"Received inspect request data {data}")

    try:
        payload = data["payload"]
        report_payload = Convertions.str2hex(json.dumps(payload))
        LOGGER.info(f"report_payload {report_payload}")

        return "accept"

    except Exception as e:
        msg = f"Error {e} processing data {data}"
        LOGGER.error(f"{msg}\n{traceback.format_exc()}")
        ROLLUP_CLIENT.send_report({"payload": Convertions.str2hex(msg)})
        return "reject"


handlers = {
    "advance_state": handle_advance,
    "inspect_state": handle_inspect,
}


###
# Main Loop

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
