"""Tk frontend: all widget access stays on the main thread."""
import logging
import queue
import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from f1 import fetch_calendar
from local_data import CIRCUIT_ZONES
from models import UTC, next_gp_index
from network import DataError
from weather import fetch_weather, nearest_forecast, condition, wind_direction

BG, PANEL, TEXT, MUTED, RED = '#101217', '#1c2029', '#f4f5f7', '#a9b0bf', '#ef343e'


def number(value, suffix='', digits=0):
    return '—' if value is None else f'{value:.{digits}f}{suffix}'


class WeatherApp:
    def __init__(self, root):
        self.root = root
        self.races = []; self.index = 0; self.busy = False
        self.results = queue.Queue(); self.closed = False
        root.title('F1 Weather'); root.geometry('840x760'); root.minsize(650, 580)
        root.configure(bg=BG)
        style = ttk.Style(root); style.theme_use('clam')
        style.configure('TButton', font=('Helvetica', 11, 'bold'), padding=9,
                        background=PANEL, foreground=TEXT)
        style.map('TButton', background=[('active', '#353c4b')],
                  foreground=[('disabled', '#636978')])
        self.label(root, 'F1 WEATHER', 24, RED).pack(fill='x', anchor='w', padx=24, pady=(20, 8))
        self.title = self.label(root, 'Loading 2026 calendar…', 21)
        self.title.pack(fill='x', anchor='w', padx=24)
        self.subtitle = self.label(root, '', 12, MUTED)
        self.subtitle.pack(fill='x', anchor='w', padx=24, pady=5)
        self.meta = self.label(root, '', 10, MUTED)
        self.meta.pack(fill='x', anchor='w', padx=24, pady=(0, 10))
        body = tk.Frame(root, bg=BG); body.pack(fill='both', expand=True, padx=24)
        self.canvas = tk.Canvas(body, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(body, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y'); self.canvas.pack(side='left', fill='both', expand=True)
        self.cards = tk.Frame(self.canvas, bg=BG)
        self.window = self.canvas.create_window((0, 0), window=self.cards, anchor='nw')
        self.cards.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(self.window, width=e.width))
        self.canvas.bind('<MouseWheel>', self.scroll)
        self.cards.bind('<MouseWheel>', self.scroll)
        nav = tk.Frame(root, bg=BG); nav.pack(fill='x', padx=24, pady=(12, 6))
        self.prev = ttk.Button(nav, text='< PREVIOUS GP', command=lambda: self.navigate(-1))
        self.prev.pack(side='left')
        self.refresh_button = ttk.Button(nav, text='REFRESH', command=lambda: self.load(True))
        self.refresh_button.pack(side='left', expand=True)
        self.next = ttk.Button(nav, text='NEXT GP >', command=lambda: self.navigate(1))
        self.next.pack(side='right')
        self.progress = ttk.Progressbar(root, mode='indeterminate')
        self.progress.pack(fill='x', padx=24)
        self.status = self.label(root, '', 10, MUTED)
        self.status.pack(fill='x', padx=24, pady=6)
        self.label(root, 'Schedule: Jolpica F1  |  Weather: Open-Meteo (CC BY 4.0)  |  Unofficial app', 9, MUTED).pack(pady=(0, 12))
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.poll_id = root.after(60, self.poll)
        self.load(True)

    def label(self, parent, text, size, color=TEXT, bg=BG):
        label = tk.Label(parent, text=text, bg=bg, fg=color, anchor='w',
                         font=('Helvetica', size), justify='left', wraplength=560)
        label.bind('<Configure>', lambda event: label.config(wraplength=max(100, event.width - 4)))
        return label

    def scroll(self, event):
        if event.delta:
            self.canvas.yview_scroll(-1 if event.delta > 0 else 1, 'units')

    def set_busy(self, busy):
        self.busy = busy
        if busy: self.progress.start(12)
        else: self.progress.stop()
        self.refresh_button.config(state='disabled' if busy else 'normal')
        self.prev.config(state='disabled' if busy or not self.races or self.index == 0 else 'normal')
        self.next.config(state='disabled' if busy or not self.races or self.index >= len(self.races)-1 else 'normal')

    def navigate(self, step):
        if not self.busy and 0 <= self.index + step < len(self.races):
            self.index += step
            self.load(False)

    def load(self, refresh):
        if self.busy: return
        self.set_busy(True)
        self.status.config(text='Updating schedule and weather…' if refresh else 'Loading weather…')
        if self.races:
            self.render(self.races[self.index], [], None, 'Updating weather…')
        races, index = self.races, self.index
        selected = races[index].circuit_id if races else None
        def worker():
            try:
                new_races = fetch_calendar() if refresh else races
                new_index = next_gp_index(new_races) if selected is None else next(
                    (i for i, gp in enumerate(new_races) if gp.circuit_id == selected), next_gp_index(new_races))
                gp = new_races[new_index]; rows = []; zone = CIRCUIT_ZONES.get(gp.circuit_id)
                error = ''
                if gp.latitude is not None and gp.longitude is not None:
                    try:
                        api_zone, rows = fetch_weather(gp.latitude, gp.longitude)
                        zone = api_zone or zone
                    except DataError as exc:
                        error = str(exc)
                else:
                    error = 'サーキット座標が不足しています。'
                self.results.put(('ok', new_races, new_index, rows, zone, error))
            except Exception as exc:
                logging.exception('Calendar update failed')
                message = str(exc) if isinstance(exc, DataError) else '更新に失敗しました。REFRESHで再試行してください。'
                self.results.put(('error', message))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        if self.closed: return
        try:
            result = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            self.set_busy(False)
            if result[0] == 'error':
                self.status.config(text=result[1], fg=RED)
                if not self.races:
                    self.title.config(text='Calendar unavailable')
                else:
                    self.render(self.races[self.index], [], CIRCUIT_ZONES.get(self.races[self.index].circuit_id),
                                '更新に失敗しました。再試行してください。')
            else:
                _, self.races, self.index, rows, zone, error = result
                self.render(self.races[self.index], rows, zone, error)
                stamp = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
                self.status.config(text=('Updated: ' + stamp + (' | Weather unavailable' if error else '')),
                                   fg=RED if error else MUTED)
            self.set_busy(False)
        self.poll_id = self.root.after(80, self.poll)

    def render(self, gp, rows, zone_name, error):
        try:
            zone = ZoneInfo(zone_name) if zone_name else UTC
        except (ZoneInfoNotFoundError, ValueError):
            zone = UTC; zone_name = None
        self.title.config(text=gp.name.upper())
        dates = [s.start.astimezone(zone).date() for s in gp.sessions if s.start]
        date_text = f'{min(dates):%b %d} – {max(dates):%b %d, %Y}' if dates else gp.race_date
        self.subtitle.config(text=f'{gp.circuit}  |  {date_text}')
        coordinates = f'{gp.latitude:.4f}, {gp.longitude:.4f}' if gp.latitude is not None and gp.longitude is not None else 'Coordinates unavailable'
        basis = f'LOCAL TIME · {zone_name}' if zone_name else 'UTC · Local timezone unavailable'
        self.meta.config(text=f'{gp.location}  |  {coordinates}\n{basis}  |  Round {gp.round} / 2026')
        for child in self.cards.winfo_children(): child.destroy()
        if error or gp.warnings:
            self.label(self.cards, '\n'.join(filter(None, (error, *gp.warnings))), 11, RED).pack(fill='x', pady=(0, 8))
        for session in gp.sessions:
            card = tk.Frame(self.cards, bg=PANEL, padx=14, pady=10)
            card.pack(fill='x', pady=(0, 7))
            start = session.start.astimezone(zone) if session.start else None
            time_text = start.strftime('%a %b %d · %H:%M %Z (UTC%z)') if start else 'Start time unavailable'
            self.label(card, f'{session.name}   |   {time_text}', 12, TEXT, PANEL).pack(fill='x', anchor='w')
            forecast = nearest_forecast(rows, session.start)
            if forecast:
                v = forecast.values
                self.label(card, f"{number(v['temperature_2m'], '°C', 1)}   {condition(v['weather_code'])}   |   Rain {number(v['precipitation_probability'], '%')}", 16, TEXT, PANEL).pack(fill='x', anchor='w', pady=4)
                text = (f"Precip {number(v['precipitation'], ' mm', 1)} · Humidity {number(v['relative_humidity_2m'], '%')}"
                        f" · Wind {number(v['wind_speed_10m'], ' m/s', 1)} {wind_direction(v['wind_direction_10m'])}"
                        f"\nForecast hour: {forecast.time.astimezone(zone):%b %d %H:%M %Z}")
                self.label(card, text, 10, MUTED, PANEL).pack(fill='x', anchor='w')
            else:
                if not session.start: text = 'Session time unavailable'
                elif error: text = 'Weather unavailable'
                elif session.start < datetime.now(UTC): text = 'Past session — forecast unavailable'
                else: text = 'Forecast not available yet'
                self.label(card, text, 12, MUTED, PANEL).pack(fill='x', anchor='w', pady=5)
            for widget in (card, *card.winfo_children()): widget.bind('<MouseWheel>', self.scroll)
        self.canvas.yview_moveto(0)

    def close(self):
        self.closed = True
        self.root.after_cancel(self.poll_id)
        self.root.destroy()
