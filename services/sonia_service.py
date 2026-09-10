from __future__ import annotations

import csv
import io
from datetime import date, timedelta
from typing import List

import requests

SONIA_URLS = [
    "https://fred.stlouisfed.org/graph/fredgraph.csv?id=IUDSOIA"]

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


def _try_candidate_urls(start_date: date, end_date: date) -> List[dict]:
    for url_template in SONIA_URLS:
        url = url_template.format(start=start_date.isoformat(), end=end_date.isoformat())
        try:
            response = requests.get(url, timeout=30, headers={'User-Agent': 'ARRA/1.0'})
            if response.status_code >= 400:
                continue
            text = response.text.strip()
            if not text or '\n' not in text:
                continue
            rows = list(csv.DictReader(io.StringIO(text)))
            data = []
            for row in rows:
                record_date = row.get('observation_date') or row.get('date') or row.get('Date')
                if not record_date:
                    continue
                try:
                    observation_day = date.fromisoformat(record_date)
                except ValueError:
                    continue
                if observation_day < start_date or observation_day > end_date:
                    continue
                rate = _parse_rate(row.get('IUDSOIA') or row.get('SONIA') or row.get('Value'))
                if rate is None:
                    continue
                data.append({'date': observation_day.isoformat(), 'rate': rate, 'source': 'Bank of England'})
            if data:
                data.sort(key=lambda item: item['date'])
                return data
        except requests.RequestException:
            continue
    return []


def fetch_historical_rates(start_date: date, end_date: date) -> List[dict]:
    records = _try_candidate_urls(start_date, end_date)
    if not records:
        raise ValueError('SONIA data could not be retrieved from the official Bank of England source for the requested period.')
    return records


def fetch_latest_rate(as_of_date: date | None = None) -> dict:
    anchor_date = as_of_date or date.today()
    recent_start = max(date(2000, 1, 1), anchor_date - timedelta(days=3650))
    history = fetch_historical_rates(recent_start, anchor_date)
    if not history:
        raise ValueError('No SONIA observations were available for the requested date range.')
    return history[-1]
