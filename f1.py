"""Jolpica calendar adapter. Sessions come solely from provider fields."""
from datetime import datetime
import math
from models import GrandPrix, Session, UTC
from network import get_json, DataError

URL = 'https://api.jolpi.ca/ergast/f1/{season}/?limit=100'
SESSION_FIELDS = {
    'FirstPractice': 'FP1', 'SecondPractice': 'FP2', 'ThirdPractice': 'FP3',
    'SprintQualifying': 'SPRINT QUALIFYING', 'SprintShootout': 'SPRINT SHOOTOUT',
    'Sprint': 'SPRINT', 'Qualifying': 'QUALIFYING',
}

def parse_start(data):
    if not isinstance(data, dict) or not data.get('time') or not data.get('date'):
        return None
    try:
        value = datetime.fromisoformat(data['date'] + 'T' + data['time'].replace('Z', '+00:00'))
        return value.astimezone(UTC) if value.tzinfo else None
    except (ValueError, TypeError):
        return None


def coordinate(value, bound):
    try:
        value = float(value)
        return value if math.isfinite(value) and abs(value) <= bound else None
    except (ValueError, TypeError):
        return None


def parse_calendar(data):
    try:
        raw = data['MRData']['RaceTable']['Races']
        if not isinstance(raw, list) or not raw:
            raise ValueError('Empty calendar')
        races = []
        for row in raw:
            c = row['Circuit']; loc = c.get('Location', {})
            datetime.strptime(row['date'], '%Y-%m-%d')
            sessions = [Session(name, parse_start(row[key]))
                        for key, name in SESSION_FIELDS.items() if key in row]
            sessions.append(Session('RACE', parse_start(row)))
            sessions.sort(key=lambda s: s.start or datetime.max.replace(tzinfo=UTC))
            warnings = []
            if len(sessions) < 5 or any(s.start is None for s in sessions):
                warnings.append('セッション情報が未発表または不足しています。未提供の日時は推測しません。')
            lat, lon = coordinate(loc.get('lat'), 90), coordinate(loc.get('long'), 180)
            if lat is None or lon is None:
                warnings.append('サーキット座標が不足しているため天気を取得できません。')
            races.append(GrandPrix(int(row['round']), row['raceName'], c['circuitId'],
                c['circuitName'], ', '.join(str(loc[k]) for k in ('locality', 'country') if loc.get(k)),
                lat, lon, row['date'], tuple(sessions), tuple(warnings)))
        return sorted(races, key=lambda r: (r.race_date, r.round))
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise DataError('F1 APIのカレンダー形式が不正です。後ほどREFRESHしてください。') from exc


def fetch_calendar(season=2026, transport=get_json):
    data = transport(URL.format(season=season))
    races = parse_calendar(data)
    try:
        if int(data['MRData'].get('total', len(races))) > len(races):
            raise DataError('F1 APIのカレンダーが一部しか取得できませんでした。')
    except (ValueError, TypeError) as exc:
        raise DataError('F1 APIの件数情報が不正です。') from exc
    return races
