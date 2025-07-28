import json
import requests
from .auth import EbayApi

class Search():
    def __init__(self):
        self.api = EbayApi()
        self.api.get_access_token()
    
    def search(self):
        q = 'lp'
        category_id = '176985'
        condition = 'USED'
        filter_params = 'itemLocationRegion:{NORTH_AMERICA},buyingOptions:{AUCTION}'
        sort = 'newlyListed'
        limit = 200
        url = f'{self.api.base_url}/buy/browse/v1/item_summary/search'
        
        headers = {
            'Authorization': f'Bearer {self.api.access_token}',
            'Content-Type': 'application/json'
        }
        
        params = {
            'q': q,
            'category_ids': category_id,
            'filter': filter_params,
            'sort': sort,
            'limit': limit,
            'condition': condition
        }

        response = requests.get(url, headers=headers, params=params)
        return response.json()
        
if __name__ == "__main__":
    s = Search()
    s.search()