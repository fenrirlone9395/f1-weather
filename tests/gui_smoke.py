"""Exercise real Tk widgets against deterministic service responses."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import time
import tkinter as tk
from unittest.mock import patch
from datetime import datetime, timedelta
from models import UTC, Forecast
from f1 import parse_calendar
from test_core import race, calendar
from network import DataError
from gui import WeatherApp
from weather import VARIABLES


def wait(root, app):
    deadline=time.monotonic()+5
    while app.busy and time.monotonic()<deadline:
        root.update();time.sleep(.01)
    root.update()
    assert not app.busy, 'Worker did not finish'


def run():
    a=race();b=race(True);b.update(round='2',raceName='Sprint GP', date='2026-11-01')
    b['Circuit']['circuitId']='interlagos'
    gps=parse_calendar(calendar(a,b))
    rows=[Forecast(datetime(2026,10,23,17,tzinfo=UTC)+timedelta(hours=i),
                   dict(zip(VARIABLES,[3,24.5,35,1.2,78,4.3,225]))) for i in range(100)]
    with patch('gui.fetch_calendar',return_value=gps), patch('gui.fetch_weather',return_value=('America/Chicago',rows)):
        root=tk.Tk();app=WeatherApp(root);wait(root,app)
        app.index=0;app.load(False);wait(root,app)
        assert str(app.prev['state'])=='disabled'
        assert len(app.cards.winfo_children())==5
        app.navigate(1);wait(root,app)
        assert str(app.next['state'])=='disabled'
        app.navigate(-1);wait(root,app)
        with patch('gui.fetch_weather',side_effect=DataError('Offline weather')):
            app.load(True);wait(root,app)
            assert 'Weather unavailable' in app.status['text']
        with patch('gui.fetch_calendar',side_effect=DataError('Offline calendar')):
            app.load(True);wait(root,app)
            assert 'Offline calendar' in app.status['text']
            assert len(app.races)==2
        app.load(True);wait(root,app)
        app.close()
    with patch('gui.fetch_calendar',side_effect=DataError('Offline initial')):
        root=tk.Tk();app=WeatherApp(root);wait(root,app)
        assert app.title['text']=='Calendar unavailable'
        assert str(app.refresh_button['state'])=='normal'
        app.close()
    print('PASS: Tk launch, cards, navigation boundaries, refresh, weather/calendar failures, retry, close')

if __name__=='__main__':run()
