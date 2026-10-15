"""Deterministic service tests; no live API dependency."""
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch
from f1 import parse_calendar, fetch_calendar
from models import UTC, Forecast, next_gp_index
from weather import fetch_weather, nearest_forecast, VARIABLES, wind_direction
from network import DataError, get_json
from urllib.error import URLError


def race(sprint=False):
    r = {'round':'1', 'raceName':'Test GP', 'date':'2026-10-25', 'time':'20:00:00Z',
         'Circuit':{'circuitId':'americas','circuitName':'COTA',
                    'Location':{'lat':'30.13','long':'-97.64','locality':'Austin'}},
         'FirstPractice':{'date':'2026-10-23','time':'17:30:00Z'},
         'Qualifying':{'date':'2026-10-24','time':'21:00:00Z'}}
    if sprint:
        r['SprintQualifying']={'date':'2026-10-23','time':'21:00:00Z'}
        r['Sprint']={'date':'2026-10-24','time':'17:00:00Z'}
    else:
        r['SecondPractice']={'date':'2026-10-23','time':'21:00:00Z'}
        r['ThirdPractice']={'date':'2026-10-24','time':'17:00:00Z'}
    return r


def calendar(*rows): return {'MRData':{'RaceTable':{'Races':list(rows)}}}

class CoreTests(unittest.TestCase):
    def test_normal_and_sprint_are_provider_driven(self):
        normal=parse_calendar(calendar(race()))[0]
        sprint=parse_calendar(calendar(race(True)))[0]
        self.assertEqual([s.name for s in normal.sessions], ['FP1','FP2','FP3','QUALIFYING','RACE'])
        self.assertEqual([s.name for s in sprint.sessions], ['FP1','SPRINT QUALIFYING','SPRINT','QUALIFYING','RACE'])

    def test_missing_time_and_coordinates_are_not_invented(self):
        r=race(); del r['time']; r['Circuit']['Location']['lat']='nan'
        gp=parse_calendar(calendar(r))[0]
        self.assertIsNone(gp.race_start); self.assertIsNone(gp.latitude)
        self.assertEqual(len(gp.warnings),2)

    def test_corrupt_calendar(self):
        for data in ({}, calendar(), calendar({'bad':1})):
            with self.assertRaises(DataError): parse_calendar(data)

    def test_calendar_pagination_guard(self):
        data=calendar(race());data['MRData']['total']='200'
        with self.assertRaises(DataError): fetch_calendar(transport=lambda _:data)

    def test_selection_during_weekend_and_after_season(self):
        a=race(); b=race(); b.update(round='2',date='2026-11-01')
        races=parse_calendar(calendar(a,b))
        self.assertEqual(next_gp_index(races,datetime(2026,10,24,tzinfo=UTC)),0)
        self.assertEqual(next_gp_index(races,datetime(2026,10,25,20,tzinfo=UTC)),1)
        self.assertEqual(next_gp_index(races,datetime(2027,1,1,tzinfo=UTC)),1)

    def test_dst_and_date_rollover(self):
        self.assertEqual(datetime(2026,10,25,20,tzinfo=UTC).astimezone(ZoneInfo('America/Chicago')).hour,15)
        self.assertEqual(datetime(2026,11,25,20,tzinfo=UTC).astimezone(ZoneInfo('America/Chicago')).hour,14)
        vegas=datetime(2026,11,22,4,tzinfo=UTC).astimezone(ZoneInfo('America/Los_Angeles'))
        self.assertEqual((vegas.day,vegas.hour),(21,20))

    def test_nearest_tie_boundaries_and_gaps(self):
        start=datetime(2026,10,23,17,tzinfo=UTC)
        rows=[Forecast(start),Forecast(start+timedelta(hours=1))]
        self.assertEqual(nearest_forecast(rows,start+timedelta(minutes=30)),rows[0])
        self.assertIsNone(nearest_forecast(rows,start-timedelta(seconds=1)))
        self.assertIsNone(nearest_forecast(rows,start+timedelta(days=30)))
        self.assertIsNone(nearest_forecast(rows,None))
        self.assertIsNone(nearest_forecast([rows[0],Forecast(start+timedelta(hours=3))],start+timedelta(hours=1)))

    def test_weather_unix_utc_and_nulls(self):
        data={'timezone':'America/Chicago','hourly':{'time':[1792774800]}}
        data['hourly'].update({k:[None] for k in VARIABLES})
        z, rows=fetch_weather(30,-97,transport=lambda _:data)
        self.assertEqual(rows[0].time.tzinfo,UTC)
        self.assertEqual(z,'America/Chicago')
        data['hourly']['precipitation']=[]
        with self.assertRaises(DataError): fetch_weather(30,-97,transport=lambda _:data)

    def test_bad_weather(self):
        for data in ({}, {'error':True,'reason':'bad'}):
            with self.assertRaises(DataError): fetch_weather(30,-97,transport=lambda _:data)

    def test_offline_and_bad_json(self):
        with patch('network.urlopen',side_effect=URLError('offline')):
            with self.assertRaises(DataError): get_json('https://example.invalid')
        with patch('network.json.load',side_effect=ValueError('invalid')), patch('network.urlopen'):
            with self.assertRaises(DataError): get_json('https://example.invalid')

    def test_wind(self):
        self.assertEqual(wind_direction(360),'N 360°')
        self.assertEqual(wind_direction(90),'E 90°')

if __name__ == '__main__': unittest.main()
