"""Open-Meteo adapter. Unix timestamps avoid DST/UTC-offset ambiguity."""
from datetime import datetime
from urllib.parse import urlencode
import math
from models import Forecast, UTC
from network import get_json, DataError

VARIABLES = ('weather_code', 'temperature_2m', 'precipitation_probability',
             'precipitation', 'relative_humidity_2m', 'wind_speed_10m', 'wind_direction_10m')


def fetch_weather(lat, lon, transport=get_json):
    params = dict(latitude=lat, longitude=lon, hourly=','.join(VARIABLES),
                  forecast_days=16, timezone='auto', timeformat='unixtime', wind_speed_unit='ms')
    data = transport('https://api.open-meteo.com/v1/forecast?' + urlencode(params))
    try:
        if data.get('error'):
            raise ValueError(data.get('reason'))
        hourly = data['hourly']; times = hourly['time']
        if not isinstance(times, list) or not times:
            raise ValueError('Empty hourly response')
        for key in VARIABLES:
            if not isinstance(hourly.get(key), list) or len(hourly[key]) != len(times):
                raise ValueError('Invalid hourly array: ' + key)
            if any(v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))
                                     or not math.isfinite(v)) for v in hourly[key]):
                raise ValueError('Invalid hourly value')
        rows = [Forecast(datetime.fromtimestamp(t, UTC), {k: hourly[k][i] for k in VARIABLES})
                for i, t in enumerate(times)]
        return data['timezone'], sorted(rows, key=lambda f: f.time)
    except (KeyError, TypeError, ValueError, OverflowError, OSError) as exc:
        raise DataError('天気APIの応答形式が不正です。後ほどREFRESHしてください。') from exc


def nearest_forecast(rows, start):
    if not start or not rows or start < rows[0].time or start > rows[-1].time:
        return None
    candidate = min(rows, key=lambda f: (abs((f.time - start).total_seconds()), f.time))
    return candidate if abs((candidate.time - start).total_seconds()) <= 1800 else None


def condition(code):
    if code is None: return 'Weather unavailable'
    if code == 0: return 'Clear'
    if code in (1, 2): return 'Partly cloudy'
    if code == 3: return 'Overcast'
    if code in (45, 48): return 'Fog'
    if code in (51, 53, 55): return 'Drizzle'
    if code in (56, 57, 66, 67): return 'Freezing rain / drizzle'
    if code in (61, 63, 65): return 'Rain'
    if code in (71, 73, 75, 77, 85, 86): return 'Snow'
    if code in (80, 81, 82): return 'Rain showers'
    if code in (95, 96, 99): return 'Thunderstorm'
    return f'WMO {code}'


def wind_direction(degrees):
    if degrees is None: return '—'
    points = ('N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
              'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW')
    return f'{points[int((degrees % 360) / 22.5 + .5) % 16]} {degrees:.0f}°'
