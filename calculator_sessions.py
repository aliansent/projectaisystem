import json
from route_mount import *
class calculate_session_amount():
    def __init__(self,price_session,price_per_token_gpt):
        self.session_pricing_usd=price_session
        self.Price_per_token_gpt= price_per_token_gpt
        self.sesion_pricing= price_session
    
    def real_amount_session(self,):
        return self.sesion_pricing

    def pricing_img_gen_in_tokens(self,):
        return float(0.040)
    
    def pricing_per_tokenGPT(self,):
        return self.Price_per_token_gpt

