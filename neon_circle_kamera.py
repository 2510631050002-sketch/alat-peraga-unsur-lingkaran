"""NEON CIRCLE - versi kontrol gerakan jari (webcam + MediaPipe Hands).

Jalankan:  streamlit run neon_circle_kamera.py
Buka lewat http://localhost:8501 (atau HTTPS) agar browser mengizinkan kamera.
Pelacakan tangan berjalan 100% di browser; video tidak dikirim ke server.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from dataclasses import dataclass
from typing import Callable

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="NEON CIRCLE | Kontrol Jari", page_icon="⭕",
                   layout="wide", initial_sidebar_state="collapsed")

CX, CY, R = 300, 300, 205
DURASI_LED = 1.6
Point = tuple[float, float]
O: Point = (CX, CY)

# ---------------------------------------------------------------- DATA


@dataclass(frozen=True)
class Unsur:
    kategori: str
    deskripsi: str
    warna: str
    rumus: str = ""


UNSUR: dict[str, Unsur] = {
    "Titik Pusat": Unsur("TITIK", "Titik yang terletak tepat di tengah lingkaran. Titik pusat menjadi acuan untuk menentukan jarak ke seluruh titik pada keliling lingkaran.", "#ffe66d"),
    "Jari-jari": Unsur("GARIS", "Garis yang menghubungkan titik pusat dengan satu titik pada keliling lingkaran. Panjang semua jari-jari dalam satu lingkaran sama.", "#00eaff", "r = ½ × d"),
    "Diameter": Unsur("GARIS", "Tali busur terpanjang: garis lurus yang menghubungkan dua titik pada keliling dan melewati titik pusat. Panjangnya dua kali jari-jari.", "#ff54d9", "d = 2 × r"),
    "Keliling": Unsur("GARIS LENGKUNG", "Panjang seluruh garis lengkung yang membatasi bagian luar lingkaran.", "#00eaff", "K = 2πr = πd"),
    "Busur": Unsur("GARIS LENGKUNG", "Bagian dari garis lengkung keliling lingkaran yang menghubungkan dua titik pada lingkaran.", "#ffe66d", "panjang busur = (θ/360°) × 2πr"),
    "Tali Busur": Unsur("GARIS", "Garis lurus yang menghubungkan dua titik pada keliling lingkaran.", "#ff54d9"),
    "Juring": Unsur("DAERAH", "Daerah dalam lingkaran yang dibatasi oleh dua jari-jari dan satu busur.", "#00eaff", "luas juring = (θ/360°) × πr²"),
    "Tembereng": Unsur("DAERAH", "Daerah dalam lingkaran yang dibatasi oleh sebuah tali busur dan busur lingkaran.", "#ff54d9"),
    "Apotema": Unsur("GARIS", "Garis terpendek dari titik pusat menuju tali busur, tegak lurus terhadap tali busur.", "#8cffb0", "a = √(r² − (½·tali busur)²)"),
    "Garis Singgung": Unsur("GARIS", "Garis yang menyentuh lingkaran tepat pada satu titik, tegak lurus terhadap jari-jari menuju titik singgung.", "#ffe66d"),
}

EN: dict[str, str] = {
    "Titik Pusat": "Center point", "Jari-jari": "Radius", "Diameter": "Diameter",
    "Keliling": "Circumference", "Busur": "Arc", "Tali Busur": "Chord", "Juring": "Sector",
    "Tembereng": "Segment", "Apotema": "Apothem", "Garis Singgung": "Tangent line",
}

# ------------------------------------------------------- GEOMETRI & LED


def polar(sudut: float, radius: float = R) -> Point:
    rad = math.radians(sudut)
    return CX + radius * math.cos(rad), CY + radius * math.sin(rad)


def led_titik(x: float, y: float, w: str, delay: float = 0.0, s: float = 3.5) -> str:
    return (f'<g class="led" style="--delay:{delay:.3f}s">'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{s*3:.1f}" fill="{w}" opacity=".18"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{s*1.7:.1f}" fill="{w}" opacity=".42"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{s:.1f}" fill="{w}" stroke="white" stroke-width=".55"/></g>')


def led_garis(p1
