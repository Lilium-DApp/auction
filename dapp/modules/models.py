import math
from enum import Enum
from modules.log import Logger
from typing import List, Tuple

LOGGER = Logger(level="INFO", name=__name__).logger

class Bid:
    def __init__(self, ether_amount: int, sender, erc20_interested_amount: int) -> None:
        if any(arg is None for arg in [ether_amount, sender, erc20_interested_amount]):
            raise ValueError("None of the arguments can be None")
        
        self._sender = sender
        self._ether_amount = ether_amount
        self._erc20_interested_amount = erc20_interested_amount

    @property
    def ether_amount(self) -> int:
        return self._ether_amount

    @property
    def sender(self) -> str:
        return self._sender

    @property
    def erc20_interested_amount(self) -> int:
        return self._erc20_interested_amount

    @property
    def price_per_token(self) -> int:
        return math.floor(self._ether_amount / self._erc20_interested_amount)
    
class AuctionState(Enum):
    HAPPENING = 0
    NOT_HAPPENING = 1

class Auction:
    def __init__(self, sender: str, duration: int, amount: int, token_address: str, reserve_price_per_token: int, timestamp: int) -> None:
        self._bids: List[Bid] = []
        self._sender = sender
        self._duration = duration
        self._amount = amount
        self._timestamp_init = timestamp
        self._token_address = token_address
        self._reserve_price_per_token = reserve_price_per_token

    @property
    def sender(self) -> str:
        return self._sender

    @property
    def duration(self) -> int:
        return self._duration

    @property
    def reserve_price_per_token(self) -> int:
        return self._reserve_price_per_token

    @property
    def amount(self) -> int:
        return self._amount

    @property
    def timestamp_init(self) -> int:
        return self._timestamp_init

    @property
    def token_address(self) -> str:
        return self._token_address

    @property
    def bids(self) -> List[Bid]:
        return self._bids

    def remaining_time(self, timestamp):
        """Calculates and returns the remaining time for the auction."""
        return self.timestamp_init + self.duration - timestamp
    
    def add_bid(self, bid: Bid) -> bool:
        """Adds a bid to the auction if it meets the minimum price criteria."""
        if bid.price_per_token >= self.reserve_price_per_token:
            self.bids.append(bid)
            LOGGER.info(f"Added bid from {bid.sender} to auction with {bid.ether_amount} wei and {bid.erc20_interested_amount} tokens")
            return True
        else:
            return False

    def finish(self, timestamp: int) -> Tuple[List[Bid], List[Bid], int, str, int]:
        """Finishes the auction and returns the highest bid details if available."""        
        if not self.bids:
            LOGGER.info("No bids were placed during the auction.")
            return [], [], 0, self.token_address, self.amount
        
        total_ether = 0
        selected_bids = []
        unselected_bids = []
        partial_bid_remaining_ether_amount = 0
        remaining_erc20_amount = self.amount
        self.bids.sort(key=lambda bid: bid.price_per_token, reverse=True)

        for bid in self.bids:
            if bid.erc20_interested_amount <= remaining_erc20_amount:
                total_ether += bid.ether_amount
                remaining_erc20_amount -= bid.erc20_interested_amount
                selected_bids.append(bid)
                LOGGER.info(f"Added bid from {bid.sender} to selected bids with {bid.ether_amount} wei and {bid.erc20_interested_amount} tokens")
                
                if remaining_erc20_amount <= 0:
                    unselected_bids.extend(self.bids[len(selected_bids):])
                    LOGGER.info(f"Finished auction with {len(selected_bids)} bids selected and {len(unselected_bids)} bids unselected")
                    break
            else:
                partial_acceptance_rate = math.floor(remaining_erc20_amount / bid.erc20_interested_amount)
                total_ether += math.floor(bid.ether_amount * partial_acceptance_rate)
                partial_bid_remaining_ether_amount -= bid.ether_amount - math.floor(bid.erc20_interested_amount * partial_acceptance_rate)
                remaining_erc20_amount -= math.floor(bid.erc20_interested_amount * partial_acceptance_rate)
                
                partial_bid = bid.__class__(ether_amount=math.floor(bid.ether_amount * partial_acceptance_rate), sender=bid.sender, erc20_interested_amount=math.floor(bid.erc20_interested_amount * partial_acceptance_rate))
                selected_bids.append(partial_bid)
                LOGGER.info(f"Create partial bid from {bid.sender} with {partial_bid.ether_amount} wei and {partial_bid.erc20_interested_amount} tokens")

                if partial_acceptance_rate < 1:
                    unaccepted_bid = bid.__class__(ether_amount=partial_bid_remaining_ether_amount, sender=bid.sender, erc20_interested_amount=math.floor(bid.erc20_interested_amount * (1 - partial_acceptance_rate)))
                    unselected_bids.append(unaccepted_bid)
                    LOGGER.info(f"Create unaccepted part of patial bid from {bid.sender} with {unaccepted_bid.ether_amount} wei and {unaccepted_bid.erc20_interested_amount} tokens")
                
                unselected_bids.extend(self.bids[len(selected_bids):])
                LOGGER.info(f"Finished auction with {len(selected_bids)} bids selected and {len(unselected_bids)} bids unselected")
                break
        return selected_bids, unselected_bids, total_ether, self.token_address, remaining_erc20_amount,  self.sender


