
class NewBid():
    def __init__(self, walletBid, value: int, quantity: int, time_stamp: int) -> None:
        self.value = value
        self.quantity = quantity
        self.time_stamp = time_stamp
        self.walletBid = walletBid
        self.price_per_unit = value / quantity
    
    def __repr__(self) -> str:
        return f"walletBID: {self.walletBid}, value: {self.value}, quantity: {self.quantity}, time_stamp: {self.time_stamp}"

class NewAuction():
    def __init__(self, wallet, amount: int, minimum_price: int, duration: int) -> None:
        self.amount = amount
        self.minimum_price = minimum_price
        self.duration = duration
        self.wallet = wallet
        self.status = True
        self.offers = []    

    def __repr__(self) -> str:
        return f"wallet: {self.wallet}, amount: {self.amount}, prince: {self.minimum_price}, duration: {self.duration}"
    def update_time(self, time_stamp):
        self.time_stamp = time_stamp

    def bid(self, offer: NewBid) -> None:

        if offer.value <= 0 or offer.quantity <= 0:
          
            return
        
        self.time_stamp = offer.time_stamp
        self.price_per_unit = offer.price_per_unit
    

        self.status_auction()
        if self.verify_offer():
            self.offers.append(offer)
            self.offers.sort(key=lambda x: x.price_per_unit, reverse=True)
        else:
           pass
    def status_auction(self) -> bool:
        self.status = self.time_stamp <= self.duration  
        return self.status 
            
    def verify_offer(self):
        return self.price_per_unit >= self.minimum_price
        
    @property
    def remaining_time(self):
        return self.duration - self.time_stamp if self.status else 0

    @property
    def current_offer(self):
        return self.offers[0] if self.offers else None
        

    def return_tokens(self):
        winners = []
        for offer in self.offers:
            if self.amount > 0:
                if self.amount < offer.quantity:
                    winners.append([offer.walletBid,self.amount,offer.value])
                    self.amount = 0
                else:
                    self.amount -= offer.quantity
                    winners.append([offer.walletBid,offer.quantity,offer.value])
            else:
                return winners
    
   

# if __name__ == "__main__":
#     novoLeilao = NewAuction(wallet = "0000000", minimum_price = 10, amount = 10, duration = 100)

#     #2 tokens por 90
#     novaoferta = NewBid("0000001", 90, 2, 100)
#     # 7 tokens por 80
#     novaoferta2 = NewBid("0000002", 80, 7, 70)
#     # 5 tokens por 70
#     novaoferta3 = NewBid("0000003", 70, 5, 20)

#     novoLeilao.bid(novaoferta)
#     novoLeilao.bid(novaoferta2)
#     novoLeilao.bid(novaoferta3)
#     print(novoLeilao.offers)
    
#     novoLeilao.return_tokens()
