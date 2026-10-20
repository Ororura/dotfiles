#!/usr/bin/python3
"""Saint Petersburg weather for Waybar, with a shared cache across outputs."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import fcntl
import html
import json
import math
import os
import time
import urllib.parse
import urllib.request

CITY = 'Санкт-Петербург'
TZ = ZoneInfo('Europe/Moscow')
URL = 'https://api.open-meteo.com/v1/forecast?' + urllib.parse.urlencode({
    'latitude': 59.9386, 'longitude': 30.3141,
    'current': 'temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,is_day,wind_speed_10m',
    'wind_speed_unit': 'ms', 'timezone': 'Europe/Moscow', 'forecast_days': 1})
TTL = 600
MAX_AGE = 10800


def conditions(code, day):
    if code == 0: return ('󰖙' if day else '󰖔', 'Ясно')
    if code in (1, 2): return ('󰖕', 'Малооблачно' if code == 1 else 'Переменная облачность')
    if code == 3: return ('󰖐', 'Пасмурно')
    if code in (45, 48): return ('󰖑', 'Туман')
    if code in (51, 53, 55): return ('󰖗', 'Морось')
    if code in (56, 57, 66, 67): return ('󰖘', 'Переохлаждённые осадки')
    if code in (61, 63, 65): return ('󰖗', 'Дождь')
    if code in (71, 73, 75, 77): return ('󰖖', 'Снег')
    if code in (80, 81, 82): return ('󰖗', 'Ливневый дождь')
    if code in (85, 86): return ('󰖖', 'Снегопад')
    if code in (95, 96, 99): return ('󰖓', 'Гроза')
    return ('󰖐', 'Состояние погоды недоступно')


def valid(data):
    value = data['current']['temperature_2m']
    if not isinstance(value, (int, float)) or not math.isfinite(value) or not -100 <= value <= 70:
        raise ValueError('Invalid weather temperature')
    return data


def cached_weather(refresh=False):
    directory = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home()/'.cache'))) / 'waybar'
    directory.mkdir(parents=True, exist_ok=True)
    cache = directory / 'weather-spb.json'
    with (directory / 'weather-spb.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            state = json.loads(cache.read_text())
            valid(state['data']) if state.get('data') else None
        except (OSError, ValueError, KeyError, TypeError):
            state = {}
        now = time.time()
        fresh = state.get('data') and 0 <= now - state.get('fetched_at', 0) < TTL
        retry = now - state.get('attempted_at', 0) >= 60
        if refresh or (not fresh and retry):
            state['attempted_at'] = now
            try:
                request = urllib.request.Request(URL, headers={'User-Agent': 'Waybar-weather/1.0'})
                with urllib.request.urlopen(request, timeout=6) as response:
                    data = valid(json.load(response))
                state.update(data=data, fetched_at=now, failed=False)
            except Exception:
                # Keep the last successful reading, never invent a temperature.
                state['failed'] = True
            temporary = cache.with_suffix('.tmp')
            temporary.write_text(json.dumps(state, ensure_ascii=False))
            temporary.chmod(0o600)
            temporary.replace(cache)
        return state


def number(value, suffix, signed=False):
    if not isinstance(value, (int, float)) or not math.isfinite(value): return '—'
    return (f'{value:+.0f}' if signed else f'{value:.0f}') + suffix


def payload(state, now=None):
    now = time.time() if now is None else now
    data = state.get('data')
    age = max(0, now - state.get('fetched_at', 0))
    if not data or age > MAX_AGE:
        return {'text': '󰖐 —°C', 'class': 'offline',
                'tooltip': f'<b>{CITY}</b>\nПогода временно недоступна.\nНажмите для повторного запроса.\nИсточник: Open-Meteo'}
    current = data['current']
    icon, description = conditions(current.get('weather_code'), current.get('is_day', 1))
    tooltip = f'<b>{CITY}</b> · {html.escape(description)}\n'
    tooltip += 'Температура: ' + number(current.get('temperature_2m'), '°C', True) + '\n'
    tooltip += 'Ощущается: ' + number(current.get('apparent_temperature'), '°C', True) + '\n'
    tooltip += 'Влажность: ' + number(current.get('relative_humidity_2m'), '%') + '\n'
    wind = current.get('wind_speed_10m')
    tooltip += 'Ветер: ' + (f'{wind:.1f} м/с' if isinstance(wind, (int, float)) else '—') + '\n'
    tooltip += 'Данные на ' + html.escape(current.get('time', '').replace('T', ' ')) + ' · МСК\n'
    stale = age > 1800 or state.get('failed', False)
    if stale: tooltip += f'Сохранённые данные · загружены {datetime.fromtimestamp(state["fetched_at"], TZ):%H:%M}\n'
    tooltip += 'Обновление каждые 10 минут · нажмите, чтобы обновить\nИсточник: Open-Meteo'
    return {'text': icon + ' ' + number(current.get('temperature_2m'), '°C', True),
            'tooltip': tooltip, 'class': 'stale' if stale else 'normal'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    state = cached_weather(args.refresh)
    if not args.refresh:
        print(json.dumps(payload(state), ensure_ascii=False))


if __name__ == '__main__':
    main()
