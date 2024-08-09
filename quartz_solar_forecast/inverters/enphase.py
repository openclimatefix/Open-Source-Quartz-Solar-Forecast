import http.client
import os
import pandas as pd
import json
import base64
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

from urllib.parse import urlencode

def get_enphase_auth_url():
    """
    Generate the authorization URL for the Enphase API.

    :param None
    :return: Authentication URL
    """
    client_id = os.getenv('ENPHASE_CLIENT_ID')

    redirect_uri = (
        "https://api.enphaseenergy.com/oauth/redirect_uri"  # Or your own redirect URI
    )
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
    }
    auth_url = f"https://api.enphaseenergy.com/oauth/authorize?{urlencode(params)}"
    return auth_url


def get_enphase_authorization_code(auth_url):
    """
    Open the authorization URL in a browser and retrieve the authorization code from the redirect URI.

    :param auth_url: Authentication URL to get the code
    :return: The one time code for access to a system
    """
    # Open the authorization URL in a browser
    print(f"Please visit the following URL and authorize the application: {auth_url}")
    print(
        "After authorization, you will be redirected to a URL with the authorization code."
    )
    print("Please copy and paste the full redirect URL here:")
    redirect_url = input()
    # Extract the authorization code from the redirect URL
    code = redirect_url.split("?code=")[1]
    return code


def get_enphase_access_token():
    """
    Obtain an access token for the Enphase API using the Authorization Code Grant flow.
    :param None
    :return: Access Token
    """
        
    client_id = os.getenv('ENPHASE_CLIENT_ID')
    client_secret = os.getenv('ENPHASE_CLIENT_SECRET')

    auth_url = get_enphase_auth_url()
    auth_code = get_enphase_authorization_code(auth_url)

    # Combine the client ID and secret with a colon separator
    credentials = f"{client_id}:{client_secret}"

    # Encode the credentials as bytes
    credentials_bytes = credentials.encode("utf-8")

    # Base64 encode the bytes
    encoded_credentials = base64.b64encode(credentials_bytes)

    # Convert the encoded bytes to a string
    encoded_credentials_str = encoded_credentials.decode("utf-8")

    conn = http.client.HTTPSConnection("api.enphaseenergy.com")
    payload = ""
    headers = {
        "Authorization": f"Basic {encoded_credentials_str}"
    }
    conn.request(
        "POST",
        f"/oauth/token?grant_type=authorization_code&redirect_uri=https://api.enphaseenergy.com/oauth/redirect_uri&code={auth_code}",
        payload,
        headers,
    )
    res = conn.getresponse()
    data = res.read()

    # Decode the data read from the response
    decoded_data = data.decode("utf-8")

    # Convert the decoded data into JSON format
    data_json = json.loads(decoded_data)
    access_token = data_json["access_token"]

    return access_token


def process_enphase_data(data_json: dict, start_at: int) -> pd.DataFrame:
    """
    Process the JSON data from Enphase API and convert it to a DataFrame.
    
    :param data_json: JSON data from Enphase API
    :param start_at: Start timestamp for filtering data
    :return: DataFrame with processed data
    """
    # Initialize an empty list to store the data
    data_list = []

    # Loop through the intervals and collect the data for the last week
    for interval in data_json['intervals']:
        end_at = interval['end_at']
        if end_at >= start_at:
            # Convert to UTC
            timestamp = datetime.fromtimestamp(end_at, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

            # Append the data to the list
            data_list.append({"timestamp": timestamp, "power_kw": interval['powr']/1000})

    # Convert the list to a DataFrame
    live_generation_kw = pd.DataFrame(data_list)

    # Convert to datetime
    live_generation_kw["timestamp"] = pd.to_datetime(live_generation_kw["timestamp"])

    return live_generation_kw

def get_enphase_data(enphase_system_id: str) -> pd.DataFrame:
    """ 
    Get live PV generation data from Enphase API v4
    :param enphase_system_id: System ID for Enphase API
    :return: Live PV generation in Watt-hours, assumes to be a floating-point number
    """
    api_key = os.getenv('ENPHASE_API_KEY')
    access_token = get_enphase_access_token()

    # Set the start time to 1 week from now
    start_at = int((datetime.now() - timedelta(weeks=1)).timestamp())

    # Set the granularity to week
    granularity = "week"

    conn = http.client.HTTPSConnection("api.enphaseenergy.com")
    headers = {
        "Authorization": f"Bearer {str(access_token)}",
        "key": str(api_key)
    }

    # Add the system_id and duration parameters to the URL
    url = f"/api/v4/systems/{enphase_system_id}/telemetry/production_micro?start_at={start_at}&granularity={granularity}"
    conn.request("GET", url, headers=headers)

    res = conn.getresponse()
    data = res.read()

    # Decode the data read from the response
    decoded_data = data.decode("utf-8")

    # Convert the decoded data into JSON format
    data_json = json.loads(decoded_data)

    # Process the data using the new function
    live_generation_kw = process_enphase_data(data_json, start_at)

    return live_generation_kw