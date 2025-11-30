import base64
import os
import datetime
import requests
from requests.auth import HTTPBasicAuth
from django.conf import settings

# --- 1. CONFIGURATION ---
def get_config(key, default=None):
    return os.environ.get(key, getattr(settings, key, default))

MPESA_CONSUMER_KEY = get_config('MPESA_CONSUMER_KEY')
MPESA_CONSUMER_SECRET = get_config('MPESA_CONSUMER_SECRET')
MPESA_PASSKEY = get_config('MPESA_PASSKEY')
MPESA_SHORTCODE = get_config('MPESA_SHORTCODE', '174379') 
BASE_APP_URL = get_config('APP_URL') 
MPESA_API_URL = "https://sandbox.safaricom.co.ke" 

# --- 2. HELPER FUNCTIONS ---
def format_timestamp():
    return datetime.datetime.now().strftime('%Y%m%d%H%M%S')

def generate_stk_password(timestamp):
    data_to_encode = str(MPESA_SHORTCODE) + MPESA_PASSKEY + timestamp
    encoded_string = base64.b64encode(data_to_encode.encode('utf-8'))
    return encoded_string.decode('utf-8')

def generate_access_token():
    try:
        # 1. Clean the keys (Remove accidental spaces/newlines from Render)
        consumer_key = str(MPESA_CONSUMER_KEY).strip()
        consumer_secret = str(MPESA_CONSUMER_SECRET).strip()
        
        api_url = f"{MPESA_API_URL}/oauth/v1/generate?grant_type=client_credentials"
        
        # 2. Make the request using the CLEANED keys
        response = requests.get(
            api_url, 
            auth=HTTPBasicAuth(consumer_key, consumer_secret)
        )
        
        # Check for errors
        response.raise_for_status() 
        token_data = response.json()
        return token_data.get('access_token')
        
    except Exception as e:
        # Print the detailed response text if available (helps debugging)
        if 'response' in locals():
            print(f"Safaricom Response Body: {response.text}")
            
        print(f"Error generating Access Token: {e}")
        return None

# --- 3. INITIATE STK PUSH ---
def initiate_stk_push(phone_number, amount, order_id):
    access_token = generate_access_token()
    if not access_token:
        return {'ResponseCode': '1', 'CustomerMessage': 'Failed to authenticate with M-PESA.'}

    timestamp = format_timestamp()
    password = generate_stk_password(timestamp)
    
    # Format Phone Number
    phone_number = str(phone_number).strip()
    if phone_number.startswith('0'):
        phone_number = '254' + phone_number[1:]
    elif phone_number.startswith('+254'):
        phone_number = phone_number[1:]
    
    # This must match  urls.py structure
    callback_url = f"{BASE_APP_URL}/mpesa/callback/"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount), 
        "PartyA": phone_number,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": callback_url,
        "AccountReference": str(order_id),
        "TransactionDesc": f"Payment for Order #{order_id}"
    }

    try:
        api_url = f"{MPESA_API_URL}/mpesa/stkpush/v1/processrequest"
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"STK Push Error: {e}")
        return {'ResponseCode': '1', 'CustomerMessage': 'STK Push Connection Failed'}