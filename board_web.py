import json
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from gtfs_loader import TramScheduler
from weather import get_fast_weather

with open('setup.json', 'r') as file:
    DATA = json.load(file)
    DATA = DATA["lookup"]

STATION_NAME = DATA['station']
REFRESH_RATE = 60
ROWS_TO_DISPLAY = DATA['number_of_connections']

raw_group_option = DATA.get('group_by_route', False)
GROUP_BY_ROUTE = True if (raw_group_option is True or raw_group_option == 1) else False

GMT_PLUS_1 = timezone(timedelta(hours=1))

weather_code_map = {
    0: "Clear sky ☀️",
    1: "Mainly clear 🌤️",
    2: "Partly cloudy ⛅ ",
    3: "Overcast ☁️",
    45: "Fog 🌫️",
    48: "Depositing rime fog 🌫️",
    51: "Drizzle: Light 🌧️",
    53: "Drizzle: Moderate 🌧️",
    55: "Drizzle: Dense 🌧️",
    56: "Freezing Drizzle: Light 🌨️",
    57: "Freezing Drizzle: Dense 🌨️",
    61: "Rain: Slight 🌧️",
    63: "Rain: Moderate 🌧️",
    65: "Rain: Heavy 🌧️",
    66: "Freezing Rain: Light 🌨️",
    67: "Freezing Rain: Heavy 🌨️",
    71: "Snow fall: Slight ❄️",
    73: "Snow fall: Moderate ❄️",
    75: "Snow fall: Heavy ❄️",
    77: "Snow grains ❄️",
    80: "Rain showers: Slight 🌦️",
    81: "Rain showers: Moderate 🌦️",
    82: "Rain showers: Violent 🌦️",
    85: "Snow showers: Slight 🌨️",
    86: "Snow showers: Heavy 🌨️",
    95: "Thunderstorm: Slight or moderate ⛈️",
    96: "Thunderstorm with slight hail ⛈️",
    99: "Thunderstorm with heavy hai ⛈️l"
}


def get_weather_desc(code):
    return weather_code_map.get(code, "Unknown weather status")


st.set_page_config(page_title=f"Departures - {STATION_NAME}", layout="wide")

st.markdown("""
    <style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
.title-container {
        text-align: center;
        margin-bottom: 25px;
        border-bottom: 2px solid #444;
        padding-bottom: 15px;
    }
    
    .station-name {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #ffbd45;
        font-size: 3rem; /* Bigger size */
        font-weight: 800;
        text-transform: uppercase; /* Force uppercase like real signs */
        letter-spacing: 2px;
        margin-top: 25px;
    }
    
    .station-icon {
        font-size: 3rem;
        margin-right: 15px;
        vertical-align: middle;
    }
    div[data-testid="stToolbar"] {visibility: hidden;}
    footer {visibility: hidden;}

    /* GRID CONTAINER SETUP */
    .grid-container {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr; /* Exact 2 columns */
        gap: 15px; /* Space between cards */
    }

    /* Mobile responsiveness: 1 column on small screens */
    @media (max-width: 800px) {
        .grid-container {
            grid-template-columns: 1fr; 
        }
    }

    /* Card Styling */
    .tram-card {
        background-color: #262730;
        border: 1px solid #444;
        border-radius: 12px;
        padding: 15px;
        /* Remove bottom margin because 'gap' handles spacing in grid now */
        margin-bottom: 0; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        height: 100%; /* Ensures cards in the same row are equal height */
    }

    .tram-header {
        display: flex;
        align-items: center;
        border-bottom: 1px solid #444;
        padding-bottom: 10px;
        margin-bottom: 10px;
    }

    .tram-badge {
        background-color: #ffbd45;
        color: #000;
        font-size: 2rem;
        font-weight: 800;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        margin-right: 15px;
        flex-shrink: 0;
    }

    .tram-title {
        color: #ffbd45;
        font-size: 1.5rem;
        font-weight: bold;
    }

    /* Direction Rows inside the card */
    .direction-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid #333;
    }
    .direction-row:last-child {
        border-bottom: none;
    }

    .dir-name {
        font-size: 1.2rem;
        color: white;
        font-weight: 500;
    }

    .dir-time {
        text-align: right;
    }

    .time-main {
        font-size: 1.2rem;
        font-weight: bold;
        color: white;
    }

    .time-delay {
        font-size: 0.9rem;
        color: #4CAF50;
        margin-left: 8px;
    }
    </style>
    """, unsafe_allow_html=True)


@st.cache_resource
def get_scheduler():
    return TramScheduler(data_folder='./data')


def calculate_delay_info(input_str):
    try:
        main_part, duration_part = input_str.split(' (')
    except ValueError:
        return input_str, ""

    short_timestamp = main_part[:5]
    clean_duration = duration_part.replace(')', '').replace(' ', '')

    if ',' in clean_duration:
        return short_timestamp, ""

    try:
        h, m, s = clean_duration.split(':')
        total_minutes = (int(h) * 60) + int(m)
        if total_minutes == 0:
            return short_timestamp, ""
        return short_timestamp, f"(+{total_minutes} min)"
    except ValueError:
        return short_timestamp, ""


scheduler = get_scheduler()

col_left, col_mid, col_right = st.columns([2, 6, 2])

with col_left:
    st.write("")

with col_mid:
    title_placeholder = st.empty()
    time_placeholder = st.empty()

with col_right:
    weather_placeholder = st.empty()

list_placeholder = st.empty()

temp, w_code = None, None
weather_timestamp_stamp = datetime.now()


def isInvalidStamp(stamp):
    now_stamp = datetime.now()
    diff_minutes = (now_stamp - stamp).total_seconds() / 60
    return diff_minutes > 30


# TODO refresh exactly on the minute?
while True:
    now = datetime.now(timezone.utc).astimezone(GMT_PLUS_1)
    current_time_str = now.strftime('%Y-%m-%d %H:%M:%S')

    # Checks weather once every 30 minutes
    if (temp is None and w_code is None) or isInvalidStamp(weather_timestamp_stamp):

        weather_timestamp_stamp = datetime.now()
        temp, w_code = get_fast_weather()

    time_placeholder.markdown(
        f"<h3 style='text-align: center; font-style: italic; color: gray; margin-bottom: 20px;'>Currrent time: {now.strftime('%H:%M')}</h3>",
        unsafe_allow_html=True
    )

    weather_html = f"""
        <div style="text-align: right; padding-right: 10px; margin-top: 25px;">
            <div style="color: gray; font-size: 1.1rem; font-style: italic;">Current temperature: {temp} °C</div>
            <div style="color: white; font-size: 1.1rem; font-style: italic;">{get_weather_desc(w_code)} </div>
        </div>
        """

    weather_placeholder.markdown(weather_html, unsafe_allow_html=True)

    df, name = scheduler.get_next_departures(
        STATION_NAME,
        current_time_str,
        n=ROWS_TO_DISPLAY,
        distinct=GROUP_BY_ROUTE
    )
    title_html = f"""
        <div class="title-container">
            <div class="station-name">
                {name}
            </div>
        </div>
        """
    title_placeholder.markdown(title_html, unsafe_allow_html=True)

    if isinstance(df, str):
        list_placeholder.error(df)
    else:
        html_buffer = ""

        if GROUP_BY_ROUTE:
            df['sort_key'] = pd.to_numeric(df['Tram no.'], errors='coerce').fillna(999)
            df = df.sort_values('sort_key')

            grouped = df.groupby('Tram no.', sort=False)

            html_buffer += '<div class="grid-container">'

            for tram_no, group in grouped:
                html_buffer += f'<div class="tram-card">'
                html_buffer += (f'<div class="tram-header"><div class="tram-badge">{tram_no}</div><div '
                                f'class="tram-title">Departures</div></div>')

                for idx, row in group.iterrows():
                    direction = row['Direction']
                    raw_time = row['Time of departure']
                    d_time, d_delay = calculate_delay_info(raw_time)

                    html_buffer += (f'<div class="direction-row"><div class="dir-name">{direction}</div><div '
                                    f'class="dir-time"><span class="time-main">{d_time}</span><span '
                                    f'class="time-delay">{d_delay}</span></div></div>')

                html_buffer += "</div>"

            html_buffer += '</div>'

        else:
            html_buffer = '<div class="tram-card-container">'
            for idx, row in df.iterrows():
                tram_no = row['Tram no.']
                direction = row['Direction']
                raw_time = row['Time of departure']
                d_time, d_delay = calculate_delay_info(raw_time)

                html_buffer += (f'<div class="tram-card" style="display:flex; align-items:center; '
                                f'justify-content:space-between;"><div style="display:flex; align-items:center;"><div '
                                f'class="tram-badge" style="width:50px; height:50px; font-size:1.5rem; '
                                f'margin-bottom:0; margin-right:15px;">{tram_no}</div><div class="dir-name">'
                                f'{direction}</div></div><div class="dir-time"><span class="time-main">'
                                f'{d_time}</span><span class="time-delay">{d_delay}</span></div></div>')
            html_buffer += '</div>'

        list_placeholder.markdown(html_buffer, unsafe_allow_html=True)

    time.sleep(REFRESH_RATE)
