import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone
import os
import requests
from PIL import Image
from dotenv import load_dotenv
from streamlit import session_state as state

from quartz_solar_forecast.pydantic_models import PVSite

# Load environment variables
load_dotenv()

if 'enphase_access_token' not in st.session_state:
    st.session_state.enphase_access_token = None
if 'enphase_system_id' not in st.session_state:
    st.session_state.enphase_system_id = None

# Set up the base URL for the FastAPI server
FASTAPI_BASE_URL = "http://localhost:8000"

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to logo.png
logo_path = os.path.join(script_dir, "logo.png")
im = Image.open(logo_path)

st.set_page_config(
    page_title="Open Source Quartz Solar Forecast | Open Climate Fix",
    layout="wide",
    page_icon=im,
)
st.title("☀️ Open Source Quartz Solar Forecast")

def make_api_request(endpoint, method="GET", data=None):
    try:
        url = f"{FASTAPI_BASE_URL}{endpoint}"
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API request error: {e}")
        return None

# Main app logic
st.sidebar.header("PV Site Configuration")

use_defaults = st.sidebar.checkbox("Use Default Values", value=True)

if use_defaults:
    latitude = 51.75
    longitude = -1.25
    capacity_kwp = 1.25
    st.sidebar.text(f"Default Latitude: {latitude}")
    st.sidebar.text(f"Default Longitude: {longitude}")
    st.sidebar.text(f"Default Capacity (kWp): {capacity_kwp}")
else:
    latitude = st.sidebar.number_input("Latitude", min_value=-90.0, max_value=90.0, value=51.75, step=0.01)
    longitude = st.sidebar.number_input("Longitude", min_value=-180.0, max_value=180.0, value=-1.25, step=0.01)
    capacity_kwp = st.sidebar.number_input("Capacity (kWp)", min_value=0.1, value=1.25, step=0.01)

inverter_type = st.sidebar.selectbox("Select Inverter", ["No Inverter", "Enphase", "Solis", "GivEnergy", "Solarman"])

access_token = None
enphase_system_id = None
solis_data = None
givenergy_data = None
solarman_data = None

def get_enphase_auth_url():
    response = requests.get(f"{FASTAPI_BASE_URL}/solar_inverters/enphase/auth_url")
    return response.json()["auth_url"]

def get_enphase_access_token(redirect_url):
    response = requests.post(f"{FASTAPI_BASE_URL}/solar_inverters/enphase/token", json={"redirect_url": redirect_url})
    return response.json()["access_token"]

def enphase_authorization():
    if st.session_state.enphase_access_token == None:
        auth_url = get_enphase_auth_url()
        st.write("Please visit the following URL to authorize the application:")
        st.markdown(f"[Enphase Authorization URL]({auth_url})")
        st.write(
            "After authorization, you will be redirected to a URL. Please copy the entire URL and paste it below:"
        )

        redirect_url = st.text_input("Enter the redirect URL:")

        if redirect_url:
            if "?code=" not in redirect_url:
                st.error(
                    "Invalid redirect URL. Please make sure you copied the entire URL."
                )
                return None, None

            try:
                access_token = get_enphase_access_token(redirect_url)
                st.session_state.enphase_access_token = access_token
                return access_token, os.getenv("ENPHASE_SYSTEM_ID")
            except Exception as e:
                st.error(f"Error getting access token: {str(e)}")
                return None, None
    else:
        return st.session_state.enphase_access_token, os.getenv("ENPHASE_SYSTEM_ID")

    return None, None

if inverter_type == "Enphase":
    enphase_access_token, enphase_system_id = enphase_authorization()
    if enphase_access_token is None or enphase_system_id is None:
        st.warning("Enphase authorization is not complete. Please complete the authorization process.")
else:
    enphase_access_token, enphase_system_id = None, None

if st.sidebar.button("Run Forecast"):
    if inverter_type == "Enphase" and (enphase_access_token is None or enphase_system_id is None):
        st.error(
            "Enphase authorization is required. Please complete the authorization process."
        )
    else:
        # Create PVSite object with user-input or default values
        site = PVSite(
            latitude=latitude,
            longitude=longitude,
            capacity_kwp=capacity_kwp,
            inverter_type=inverter_type.lower() if inverter_type != "No Inverter" else ""
        )

        # Prepare data for API request
        data = {
            "site": site.dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "nwp_source": "icon",
            "access_token": st.session_state.enphase_access_token if inverter_type == "Enphase" else None,
            "enphase_system_id": st.session_state.enphase_system_id if inverter_type == "Enphase" else None
        }

        # Make the API request
        forecast_data = make_api_request("/forecast/", method="POST", data=data)

        if forecast_data:
            st.success("Forecast completed successfully!")

            # Display current timestamp
            st.subheader(f"Forecast generated at: {forecast_data['timestamp']}")

            # Create three columns
            col1, col2, col3 = st.columns(3)

            predictions = pd.DataFrame(forecast_data['predictions'])
            
            # Ensure 'index' column exists and is of datetime type
            if 'index' not in predictions.columns:
                predictions['index'] = pd.to_datetime(predictions.index)
            else:
                predictions['index'] = pd.to_datetime(predictions['index'])
            
            predictions.set_index('index', inplace=True)

            # Plotting logic
            if inverter_type == "No Inverter":
                fig = px.line(
                    predictions.reset_index(),
                    x="index",
                    y=["power_kw_no_live_pv"],
                    title="Forecasted Power Generation",
                    labels={
                        "power_kw_no_live_pv": "Forecast without live data",
                        "index": "Time"
                    }
                )
            else:
                fig = px.line(
                    predictions.reset_index(),
                    x="index",
                    y=["power_kw", "power_kw_no_live_pv"],
                    title="Forecasted Power Generation",
                    labels={
                        "power_kw": f"Forecast with {inverter_type} data",
                        "power_kw_no_live_pv": "Forecast without live data",
                        "index": "Time"
                    }
                )

            fig.update_layout(
                xaxis_title="Time",
                yaxis_title="Power (kW)",
                legend_title="Forecast Type",
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.01
                )
            )

            st.plotly_chart(fig, use_container_width=True)

            # Display raw data
            st.subheader("Raw Forecast Data")
            if inverter_type == "No Inverter":
                st.dataframe(predictions[['power_kw_no_live_pv']], use_container_width=True)
            else:
                st.dataframe(predictions, use_container_width=True)
        else:
            st.error("No forecast data available. Please check your inputs and try again.")

# Some information about the app
st.sidebar.info(
    """
    This dashboard runs
    [Open Climate Fix](https://openclimatefix.org/)'s
    
    [Open Source Quartz Solar Forecast](https://github.com/openclimatefix/Open-Source-Quartz-Solar-Forecast/).
    
    Click 'Run Forecast' and add the Home-Owner approved authentication URL to see the results.
    """
)

# Footer
st.markdown("---")
st.markdown(f"Created with ❤️ by [Open Climate Fix](https://openclimatefix.org/)")
