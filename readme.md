# Where to find
"production" version of this is running on [here](https://matyas-dpmo.streamlit.app)
# How to run
- localy in a browser
```
streamlit run board_web.py
```
- or run this to compile (this works on macos, working on linux and windows feature)
```
chmod +x start_board.sh
```
- and then to run
```
./start_board.sh
```

# Setup.json
looks like this
```aiignore
{
  "lookup": {
    "station": "Zikova",
    "number_of_connections": 5,
    "group_by_routes": 0
  }
}
```
where station is a fulltext search of station and number_of_connections is an integer of how many connection you want to display

# Disclaimer
* This uses publicly available timetables sourced from [here](https://www.dpmo.cz/informace-pro-cestujici/jizdni-rady/jizdni-rady-gtfs/), doesn't include any delays, because it's base purely on timetables, live data isn't availible
* This also need's internet to run in order to get current time, other than that it could run offline.

