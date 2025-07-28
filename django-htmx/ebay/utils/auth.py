import os
import base64
import dotenv
import requests

dotenv.load_dotenv()


class EbayApi:
    def __init__(self):
        self.app_id = os.getenv('EBAY_APP_ID')
        self.cert_id = os.getenv('EBAY_CERT_ID')
        self.access_token = None
        self.base_url = "https://api.ebay.com"

    def get_access_token(self):
        auth_url = "https://api.ebay.com/identity/v1/oauth2/token"
        print(f"App ID: {self.app_id}")
        print(f"Cert ID: {self.cert_id}")
        print(f"Encoded credentials: {self.encode_creds()}")
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {self.encode_creds()}'
        }
        
        data = {
            'grant_type': 'client_credentials',
            'scope': 'https://api.ebay.com/oauth/api_scope'
        }
        
        response = requests.post(auth_url, headers=headers, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            return self.access_token
        else:
            raise Exception(f"Failed to get token: {response.text}")
        
    def encode_creds(self):
        creds = f"{self.app_id}:{self.cert_id}"
        return base64.b64encode(creds.encode()).decode()
    

if __name__ == "__main__":
    api = EbayApi()
    print(dir(api))

    
        
