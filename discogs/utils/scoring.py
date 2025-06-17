import math

def calculate_score(wants, haves, price):

    if haves == 0:
        haves = 0.01

    price = float(price)
    
    ratio = wants / haves
    volume = wants + haves
    
    ratio_score = math.log(ratio + 1) * 10
    volume_score = math.log(volume) * 2
    price_score = 50 / (price + 1)
    
    return round(ratio_score + volume_score + price_score, 2)