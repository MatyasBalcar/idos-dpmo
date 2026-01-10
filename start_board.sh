pip3 install streamlit

streamlit run board_web.py --server.headless true &

sleep 5

/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --app=http://localhost:8501 --start-fullscreen