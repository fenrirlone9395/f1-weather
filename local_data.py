"""IANA zones only. No locally invented calendar or session times.

Jolpica has no timezone field. Keep this metadata separate from API parsing.
Unknown circuits are resolved with Open-Meteo timezone=auto where possible.
"""
CIRCUIT_ZONES = {
    'albert_park': 'Australia/Melbourne', 'shanghai': 'Asia/Shanghai',
    'suzuka': 'Asia/Tokyo', 'bahrain': 'Asia/Bahrain', 'jeddah': 'Asia/Riyadh',
    'miami': 'America/New_York', 'villeneuve': 'America/Toronto',
    'monaco': 'Europe/Monaco', 'catalunya': 'Europe/Madrid',
    'madring': 'Europe/Madrid', 'red_bull_ring': 'Europe/Vienna',
    'silverstone': 'Europe/London', 'spa': 'Europe/Brussels',
    'hungaroring': 'Europe/Budapest', 'zandvoort': 'Europe/Amsterdam',
    'monza': 'Europe/Rome', 'baku': 'Asia/Baku', 'sepang': 'Asia/Kuala_Lumpur',
    'marina_bay': 'Asia/Singapore', 'americas': 'America/Chicago',
    'rodriguez': 'America/Mexico_City', 'interlagos': 'America/Sao_Paulo',
    'vegas': 'America/Los_Angeles', 'losail': 'Asia/Qatar',
    'yas_marina': 'Asia/Dubai', 'imola': 'Europe/Rome',
}
