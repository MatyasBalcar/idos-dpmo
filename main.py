import sys
from datetime import datetime
from functools import lru_cache

import pandas as pd


class TramScheduler:
    def __init__(self, data_folder='.'):

        dtype_cfg = {'stop_id': str, 'route_id': str, 'trip_id': str, 'service_id': str}

        self.stops = pd.read_csv(f"{data_folder}/stops.txt", dtype=dtype_cfg)
        self.routes = pd.read_csv(f"{data_folder}/routes.txt", dtype=dtype_cfg)
        self.trips = pd.read_csv(f"{data_folder}/trips.txt", dtype=dtype_cfg)
        self.stop_times = pd.read_csv(f"{data_folder}/stop_times.txt", dtype=dtype_cfg)
        self.calendar = pd.read_csv(f"{data_folder}/calendar.txt",
                                    dtype={'service_id': str, 'start_date': int, 'end_date': int})
        self.calendar_dates = pd.read_csv(f"{data_folder}/calendar_dates.txt", dtype={'service_id': str, 'date': int})

        self.trips_enriched = self.trips.merge(
            self.routes[['route_id', 'route_short_name']],
            on='route_id',
            how='left'
        )

    def _get_active_services(self, query_date):

        date_int = int(query_date.strftime('%Y%m%d'))
        day_name = query_date.strftime('%A').lower()

        active_cal = self.calendar[
            (self.calendar['start_date'] <= date_int) &
            (self.calendar['end_date'] >= date_int)
            ]
        if day_name in active_cal.columns:
            active_cal = active_cal[active_cal[day_name] == 1]

        base_services = set(active_cal['service_id'])

        exceptions = self.calendar_dates[self.calendar_dates['date'] == date_int]

        added_services = set(exceptions[exceptions['exception_type'] == 1]['service_id'])
        removed_services = set(exceptions[exceptions['exception_type'] == 2]['service_id'])

        final_services = (base_services - removed_services) | added_services
        return final_services

    @lru_cache(maxsize=128)
    def get_next_departures(self, station_name, query_datetime_str, n=5):  # 5 defaultne

        query_dt = datetime.strptime(query_datetime_str, '%Y-%m-%d %H:%M:%S')
        query_time_str = query_dt.strftime('%H:%M:%S')

        matching_stops = self.stops[self.stops['stop_name'].str.contains(station_name, case=False, na=False)]
        if matching_stops.empty:
            return f"Error: No station found matching '{station_name}'"
        target_stop_ids = matching_stops['stop_id'].tolist()

        active_services = self._get_active_services(query_dt)
        if not active_services:
            return "No active services found for this date."

        valid_trips = self.trips_enriched[self.trips_enriched['service_id'].isin(active_services)]
        valid_trip_ids = valid_trips['trip_id']

        potential_departures = self.stop_times[
            (self.stop_times['stop_id'].isin(target_stop_ids)) &
            (self.stop_times['trip_id'].isin(valid_trip_ids)) &
            (self.stop_times['departure_time'] >= query_time_str)
            ].copy()

        if potential_departures.empty:
            return "No departures found after this time today."

        potential_departures = potential_departures.sort_values('departure_time').head(n)

        result = potential_departures.merge(valid_trips, on='trip_id', how='left')

        output = result[['departure_time', 'route_short_name', 'trip_headsign']]

        output = output.rename(columns={
            'departure_time': 'Time of departure',
            'route_short_name': 'Tram no.',
            'trip_headsign': 'Direction'
        })
        return output


if __name__ == "__main__":
    scheduler = TramScheduler(data_folder='./data')

    if len(sys.argv) == 3:
        station = sys.argv[1]
        date = sys.argv[2]
        number_of_connection = int(sys.argv[3])
    else:
        station = input("Station name: ")
        date = input("Date: ")
        number_of_connection = int(input("Number of connections: "))

    deps = scheduler.get_next_departures(station, date, n=number_of_connection)
    print(deps)
