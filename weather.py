import json

import requests
import streamlit as st

with open('setup.json', 'r') as file:
    DATA = json.load(file)
    DATA = DATA["lookup"]


@st.cache_data(ttl=1800)
def get_fast_weather(lat=DATA['pos_lat'], lon=DATA['pos_lon']):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        response = requests.get(url, timeout=5)
        data = response.json()

        return data['current_weather']['temperature'], data['current_weather']['weathercode']
    except:
        return "API error", None
