"""Small standard-library JSON transport, injectable in service tests."""
import json
from urllib.request import Request, urlopen
from urllib.error import URLError

class DataError(Exception):
    """An expected transport or provider data error safe to show in the GUI."""


def get_json(url):
    try:
        req = Request(url, headers={'User-Agent': 'F1Weather/1.0', 'Accept': 'application/json'})
        with urlopen(req, timeout=18) as response:
            data = json.load(response)
        if not isinstance(data, dict):
            raise ValueError('JSON object expected')
        return data
    except (URLError, OSError, ValueError) as exc:
        raise DataError('通信に失敗しました。接続状況・APIの稼働状況を確認してREFRESHしてください。') from exc
