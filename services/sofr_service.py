from __future__ import annotations

import csv
import io
from datetime import date, timedelta
from typing import List

import requests

SOFR_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SOFR"


def _parse_rate(raw_value: str | None) -> float | None:
    if raw_value is None:
        return None
    cleaned = raw_value.strip().replace('%', '').replace(',', '')
    if not cleaned or cleaned.lower() in {'null', 'n/a', 'nan'}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def fetch_historical_rates(start_date: date, end_date: date) -> List[dict]:
    response = requests.get(SOFR_URL, timeout=30, headers={'User-Agent': 'ARRA/1.0'})
    response.raise_for_status()

    rows: List[dict] = []
    reader = csv.DictReader(io.StringIO(response.text))
    for row in reader:
        record_date = row.get('observation_date') or row.get('DATE')
        if not record_date:
            continue
        try:
            observation_day = date.fromisoformat(record_date)
        except ValueError:
            continue
        if observation_day < start_date or observation_day > end_date:
            continue
        rate = _parse_rate(row.get('SOFR') or row.get('VALUE') or row.get('Value'))
        if rate is None:
            continue
        rows.append({
            'date': observation_day.isoformat(),
            'rate': rate,
            'source': 'New York Fed / FRED'
        })

    rows.sort(key=lambda item: item['date'])
    return rows


def fetch_latest_rate(as_of_date: date | None = None) -> dict:
    anchor_date = as_of_date or date.today()
    recent_start = max(date(2000, 1, 1), anchor_date - timedelta(days=3650))
    history = fetch_historical_rates(recent_start, anchor_date)
    if not history:
        raise ValueError('No SOFR observations were available for the requested date range.')
    return history[-1]
