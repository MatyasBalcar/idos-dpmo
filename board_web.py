import json
import time
from datetime import datetime, timedelta, timezone
import pandas as pd
import streamlit as st

from gtfs_loader import TramScheduler

# --- Setup ---
with open('setup.json', 'r') as file:
    DATA = json.load(file)
    DATA = DATA["lookup"]

STATION_NAME = DATA['station']
REFRESH_RATE = 60
ROWS_TO_DISPLAY = DATA['number_of_connections']

raw_group_option = DATA.get('group_by_route', False)
GROUP_BY_ROUTE = True if (raw_group_option is True or raw_group_option == 1) else False

GMT_PLUS_1 = timezone(timedelta(hours=1))

st.set_page_config(page_title=f"Departures - {STATION_NAME}", layout="wide")

# --- CSS Styles ---
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

title_placeholder = st.empty()
time_placeholder = st.empty()
list_placeholder = st.empty()

while True:
    now = datetime.now(timezone.utc).astimezone(GMT_PLUS_1)
    current_time_str = now.strftime('%Y-%m-%d %H:%M:%S')

    time_placeholder.markdown(
        f"<h3 style='text-align: center; font-style: italic; color: gray; margin-bottom: 20px;'>Currrent time: {now.strftime('%H:%M')}</h3>",
        unsafe_allow_html=True
    )

    df, name = scheduler.get_next_departures(
        STATION_NAME,
        current_time_str,
        n=ROWS_TO_DISPLAY,
        distinct=GROUP_BY_ROUTE
    )
    title_html = f"""
        <div class="title-container">
            <div class="station-name">
                <span class="station-icon"></span> {name}
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
                html_buffer += f'<div class="tram-header"><div class="tram-badge">{tram_no}</div><div class="tram-title">Departures</div></div>'

                for idx, row in group.iterrows():
                    direction = row['Direction']
                    raw_time = row['Time of departure']
                    d_time, d_delay = calculate_delay_info(raw_time)

                    html_buffer += f'<div class="direction-row"><div class="dir-name">{direction}</div><div class="dir-time"><span class="time-main">{d_time}</span><span class="time-delay">{d_delay}</span></div></div>'

                html_buffer += "</div>"

            html_buffer += '</div>'

        else:
            html_buffer = '<div class="tram-card-container">'
            for idx, row in df.iterrows():
                tram_no = row['Tram no.']
                direction = row['Direction']
                raw_time = row['Time of departure']
                d_time, d_delay = calculate_delay_info(raw_time)

                html_buffer += f'<div class="tram-card" style="display:flex; align-items:center; justify-content:space-between;"><div style="display:flex; align-items:center;"><div class="tram-badge" style="width:50px; height:50px; font-size:1.5rem; margin-bottom:0; margin-right:15px;">{tram_no}</div><div class="dir-name">{direction}</div></div><div class="dir-time"><span class="time-main">{d_time}</span><span class="time-delay">{d_delay}</span></div></div>'
            html_buffer += '</div>'

        list_placeholder.markdown(html_buffer, unsafe_allow_html=True)

    time.sleep(REFRESH_RATE)