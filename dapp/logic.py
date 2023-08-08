
class NewBid():
    def __init__(self, walletBid, value: float, quantity: int, time_stamp: int) -> None:
        self.value = value
        self.quantity = quantity
        self.time_stamp = time_stamp
        self.walletBid = walletBid
        self.price_per_unit = value / quantity
    
    def __repr__(self) -> str:
        return f"walletBID: {self.walletBid}, value: {self.value}, quantity: {self.quantity}, time_stamp: {self.time_stamp}"

class NewAuction():
    def __init__(self, wallet, amount: int, minimum_price: float, duration: int) -> None:
        self.amount = amount
        self.minimum_price = minimum_price
        self.duration = duration
        self.wallet = wallet
        self.status = True
        self.offers = []    

    def __repr__(self) -> str:
        return f"wallet: {self.wallet}, amount: {self.amount}, prince: {self.minimum_price}, duration: {self.duration}"

    def bid(self, offer: NewBid) -> None:

        if offer.value <= 0 or offer.quantity <= 0:
            print("Oferta inválida")
            return
        
        self.time_stamp = offer.time_stamp
        self.price_per_unit = offer.price_per_unit

        self.status_auction()
        if self.verify_offer():
            self.offers.append(offer)
            self.offers.sort(key=lambda x: x.price_per_unit, reverse=True)
        else:
            print("Oferta não aceita")

    def status_auction(self) -> bool:
        self.status = self.time_stamp <= self.duration  
        self.return_tokens() if self.status == False else None
            
    def verify_offer(self):
        return self.price_per_unit >= self.minimum_price
        
    @property
    def remaining_time(self):
        return self.duration - self.time_stamp if self.status else 0

    @property
    def current_offer(self):
        return self.offers[0] if self.offers else None
        
    def return_tokens(self):
        for offer in self.offers:
            if self.amount > 0:
                if self.amount < offer.quantity:
                    print(f"{offer.walletBid} recebeu {self.amount} tokens")
                    self.amount = 0
                else:
                    self.amount -= offer.quantity
                    print(f"{offer.walletBid} recebeu {offer.quantity} tokens")
            else:
                print("Não há mais tokens para serem distribuidos")
                break
    
   

if __name__ == "__main__":
    novoLeilao = NewAuction(wallet = "0000000", minimum_price = 10, amount = 10, duration = 100)

    #2 tokens por 90
    novaoferta = NewBid("0000001", 90, 2, 100)
    # 7 tokens por 80
    novaoferta2 = NewBid("0000002", 80, 7, 70)
    # 5 tokens por 70
    novaoferta3 = NewBid("0000003", 70, 5, 20)

    novoLeilao.bid(novaoferta)
    novoLeilao.bid(novaoferta2)
    novoLeilao.bid(novaoferta3)
    print(novoLeilao.offers)
    
    novoLeilao.return_tokens()
