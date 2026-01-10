import streamlit as st
import time
from datetime import datetime, timedelta, timezone
from gtfs_loader import TramScheduler

STATION_NAME = "Zikova"
REFRESH_RATE = 60
ROWS_TO_DISPLAY = 5

GMT_PLUS_1 = timezone(timedelta(hours=1))

st.set_page_config(page_title=f"Departures - {STATION_NAME}", layout="wide")

st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    h1 {text-align: center; color: #ffbd45; margin-bottom: 10px;}
    div[data-testid="stToolbar"] {visibility: hidden;}
    footer {visibility: hidden;}

    table {
        width: 100%;
        border-collapse: collapse;
        border-spacing: 0;
        margin-bottom: 0;
    }
    th {
        background-color: #262730;
        color: white;
        padding: 15px;
        text-align: center !important;
        font-size: 1.2rem;
        border-bottom: 2px solid #444;
    }
    td {
        padding: 10px;
        border-bottom: 1px solid #333;
        vertical-align: middle;
    }

    tr td:nth-child(1) {
        text-align: center;
        font-size: 2rem;
        font-weight: bold;
        color: #ffbd45;
        width: 15%;
    }

    tr td:nth-child(2) {
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        width: 20%;
    }

    tr td:nth-child(3) {
        text-align: left;
        font-size: 1.5rem;
        padding-left: 20px;
    }
    </style>
    """, unsafe_allow_html=True)


@st.cache_resource
def get_scheduler():
    return TramScheduler(data_folder='./data')


scheduler = get_scheduler()

st.title(f"{STATION_NAME}")

time_placeholder = st.empty()
table_placeholder = st.empty()

while True:
    # Get current time in UTC, then convert to GMT+1
    now = datetime.now(timezone.utc).astimezone(GMT_PLUS_1)
    current_time_str = now.strftime('%Y-%m-%d %H:%M:%S')

    time_placeholder.markdown(
        f"<h3 style='text-align: center; color: gray; margin-bottom: 20px;'>{now.strftime('%H:%M')}</h3>",
        unsafe_allow_html=True
    )

    df = scheduler.get_next_departures(STATION_NAME, current_time_str, n=ROWS_TO_DISPLAY)

    if isinstance(df, str):
        table_placeholder.error(df)
    else:
        df = df[['Tram no.', 'Time of departure', 'Direction']]
        df['Time of departure'] = df['Time of departure'].astype(str).str[:5]

        html_code = df.to_html(index=False, border=0, classes="departure_table")

        table_placeholder.markdown(html_code, unsafe_allow_html=True)

    time.sleep(REFRESH_RATE)