#!/usr/bin/env python3
"""Run from a macOS terminal: python3 app.py."""
import sys


def main():
    try:
        import tkinter as tk
        from gui import WeatherApp
    except ImportError as exc:
        print(f'Tkinterを読み込めません: {exc}\nREADMEのmacOS向けPython/Tkの導入手順を確認してください。', file=sys.stderr)
        return 1
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f'GUIを起動できません: {exc}\nmacOSのデスクトップ上のターミナルから起動してください。', file=sys.stderr)
        return 1
    WeatherApp(root)
    root.mainloop()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
