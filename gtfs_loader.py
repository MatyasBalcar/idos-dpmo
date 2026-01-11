import sys
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import pandas as pd

GMT_PLUS_1 = timezone(timedelta(hours=1))


class TramScheduler:
    def __init__(self, data_folder='.'):
        dtype_cfg = {'stop_id': str, 'route_id': str, 'trip_id': str, 'service_id': str}

        self.stops = pd.read_csv(f"{data_folder}/stops.txt", dtype=dtype_cfg)
        self.routes = pd.read_csv(f"{data_folder}/routes.txt", dtype=dtype_cfg)
        self.trips = pd.read_csv(f"{data_folder}/trips.txt", dtype=dtype_cfg)
        self.stop_times = pd.read_csv(f"{data_folder}/stop_times.txt", dtype=dtype_cfg)
        self.calendar = pd.read_csv(f"{data_folder}/calendar.txt",
                                    dtype={'service_id': str, 'start_date': int, 'end_date': int})
        self.calendar_dates = pd.read_csv(f"{data_folder}/calendar_dates.txt",
                                          dtype={'service_id': str, 'date': int})

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

    def _fetch_departures(self, stop_ids, service_ids, start_time_str, limit=None):
        valid_trips = self.trips_enriched[self.trips_enriched['service_id'].isin(service_ids)]

        # temp solution for 3 and 5 exclude depo run
        # mask = ~(
        #          (valid_trips['trip_headsign'] == 'Hlavní nádraží'))

        # -----------------------------------------------------------------

        valid_trip_ids = valid_trips['trip_id']

        departures = self.stop_times[
            (self.stop_times['stop_id'].isin(stop_ids)) &
            (self.stop_times['trip_id'].isin(valid_trip_ids)) &
            (self.stop_times['departure_time'] >= start_time_str)
            ].copy()

        if departures.empty:
            return pd.DataFrame()

        departures = departures.sort_values('departure_time')

        if limit:
            departures = departures.head(limit)

        result = departures.merge(valid_trips, on='trip_id', how='left')

        current_time_obj = datetime.now(timezone.utc).astimezone(GMT_PLUS_1)

        def format_time_with_delta(dep_time_str):
            try:
                dep_dt_base = datetime.strptime(dep_time_str, '%H:%M:%S')
                dep_hm = datetime.strptime(dep_dt_base.strftime('%H:%M'), '%H:%M')
                now_hm = datetime.strptime(current_time_obj.strftime('%H:%M'), '%H:%M')
                delta = dep_hm - now_hm
                return f"{dep_time_str} ( {str(delta)} )"
            except Exception:
                return dep_time_str

        result["departure_time"] = result["departure_time"].apply(format_time_with_delta)
        return result

    @lru_cache(maxsize=128)
    def get_next_departures(self, station_name, query_datetime_str, n=5, distinct=False):
        try:
            query_dt = datetime.strptime(query_datetime_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return "Error: Date format must be YYYY-MM-DD HH:MM:SS", None

        query_time_str = query_dt.strftime('%H:%M:%S')

        matching_stops = self.stops[self.stops['stop_name'].str.contains(station_name, case=False, na=False)]
        if matching_stops.empty:
            return f"Error: No station found matching '{station_name}'", None

        str_name = matching_stops['stop_name'].iloc[0]

        target_stop_ids = matching_stops['stop_id'].tolist()

        active_services_today = self._get_active_services(query_dt)

        fetch_limit = None if distinct else n

        df_today = self._fetch_departures(target_stop_ids, active_services_today, query_time_str, limit=fetch_limit)
        if distinct and not df_today.empty:
            df_today = df_today.drop_duplicates(subset=['route_short_name', 'trip_headsign'], keep='first')

        results_collected = len(df_today)

        results_needed = n - results_collected

        df_tomorrow = pd.DataFrame()

        if results_needed > 0:
            tomorrow_dt = query_dt + timedelta(days=1)
            active_services_tomorrow = self._get_active_services(tomorrow_dt)

            df_tomorrow = self._fetch_departures(target_stop_ids, active_services_tomorrow, "00:00:00",
                                                 limit=None if distinct else results_needed)

            if distinct and not df_tomorrow.empty:
                df_tomorrow = df_tomorrow.drop_duplicates(subset=['route_short_name', 'trip_headsign'], keep='first')
        combined_df = pd.concat([df_today, df_tomorrow], ignore_index=True)

        if distinct and not combined_df.empty:
            combined_df = combined_df.drop_duplicates(subset=['route_short_name', 'trip_headsign'], keep='first')

        if combined_df.empty:
            return "No departures found.", str_name

        condition = (
                (combined_df['trip_headsign'] == 'Hlavní nádraží') &
                (combined_df['route_short_name'].astype(str).isin(['3', '5']))
        )

        combined_df = combined_df[~condition]

        if not distinct:
            combined_df = combined_df.head(n)

        output = combined_df[['departure_time', 'route_short_name', 'trip_headsign']]

        output = output.rename(columns={
            'departure_time': 'Time of departure',
            'route_short_name': 'Tram no.',
            'trip_headsign': 'Direction'
        })

        return output, str_name


if __name__ == "__main__":
    scheduler = TramScheduler(data_folder='./data')
    deps, name = scheduler.get_next_departures("Zikova", "2026-01-12 00:00:00", n=10, distinct=True)
