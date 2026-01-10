import time
from datetime import datetime

import streamlit as st

from gtfs_loader import TramScheduler

"""
streamlit run board_web.py
"""


STATION_NAME = "Zikova"
REFRESH_RATE = 60
ROWS_TO_DISPLAY = 10

st.set_page_config(page_title=f"Departures - {STATION_NAME}", layout="wide")

st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    h1 {text-align: center; color: #ffbd45; margin-bottom: 0px;}
    .stDataFrame {font-size: 1.5rem;}
    div[data-testid="stToolbar"] {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)


@st.cache_resource
def get_scheduler():
    return TramScheduler(data_folder='./data')


scheduler = get_scheduler()

st.title(f"🚉 {STATION_NAME}")
time_placeholder = st.empty()
table_placeholder = st.empty()

while True:
    now = datetime.now()
    current_time_str = now.strftime('%Y-%m-%d %H:%M:%S')

    time_placeholder.markdown(f"<h3 style='text-align: center; color: gray;'>{now.strftime('%H:%M')}</h3>",
                              unsafe_allow_html=True)

    df = scheduler.get_next_departures(STATION_NAME, current_time_str, n=ROWS_TO_DISPLAY)

    if isinstance(df, str):
        table_placeholder.error(df)
    else:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=35 * (ROWS_TO_DISPLAY + 1)
        )

    time.sleep(REFRESH_RATE)
