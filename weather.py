from functools import lru_cache

import python_weather
import json
import asyncio

with open('setup.json', 'r') as file:
    DATA = json.load(file)
    DATA = DATA["lookup"]


async def getWeather():
    async with python_weather.Client(unit=python_weather.IMPERIAL) as client:
        return await client.get(DATA['location'])