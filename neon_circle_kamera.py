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


def led_garis(p1: Point, p2: Point, w: str, n: int = 35) -> str:
    return "".join(led_titik(p1[0] + (p2[0]-p1[0])*i/n, p1[1] + (p2[1]-p1[1])*i/n, w, i/n*DURASI_LED)
                   for i in range(n + 1))


def led_busur(a: float, b: float, w: str, n: int = 55, tutup: bool = False) -> str:
    out = []
    for i in range(n if tutup else n + 1):
        t = i / n
        x, y = polar(a + (b - a) * t)
        out.append(led_titik(x, y, w, t * DURASI_LED, 3.1))
    return "".join(out)


def penanda(p: Point, label: str, w: str) -> str:
    x, y = p
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="{w}" opacity=".2"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="white" stroke="{w}" stroke-width="2"/>'
            f'<text x="{x+11:.1f}" y="{y-11:.1f}" class="label" fill="#fff" font-size="17" font-weight="600">{label}</text>')


def teks(x: float, y: float, isi: str, w: str, size: int = 15, anchor: str = "start") -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{w}" font-size="{size}" font-weight="600" '
            f'text-anchor="{anchor}" class="label">{isi}</text>')


def siku_siku(p: Point, a1: Point, a2: Point, w: str, s: float = 12) -> str:
    x, y = p
    pts = [(x + a1[0]*s, y + a1[1]*s), (x + (a1[0]+a2[0])*s, y + (a1[1]+a2[1])*s), (x + a2[0]*s, y + a2[1]*s)]
    return (f'<path d="M {pts[0][0]:.1f} {pts[0][1]:.1f} L {pts[1][0]:.1f} {pts[1][1]:.1f} L {pts[2][0]:.1f} {pts[2][1]:.1f}" '
            f'fill="none" stroke="{w}" stroke-width="2.5" class="label"/>')


def bidang(d: str, w: str, op: float) -> str:
    return f'<path d="{d}" fill="{w}" fill-opacity="{op}" stroke="none"/>'


def r_titik_pusat(w): return led_titik(*O, w, 0, 6) + penanda(O, "O", w)


def r_jari_jari(w):
    a = polar(-40)
    return (led_garis(O, a, w, 45) + penanda(O, "O", w) + penanda(a, "A", w)
            + teks((CX + a[0])/2 + 12, (CY + a[1])/2 + 18, "r", w, 20))


def r_diameter(w):
    a, b = polar(180), polar(0)
    return (led_garis(a, b, w, 65) + penanda(a, "A", w) + penanda(b, "B", w) + penanda(O, "O", w)
            + teks(CX, CY + 30, "d", w, 20, "middle"))


def r_keliling(w): return led_busur(0, 360, w, 125, tutup=True)


def r_busur(w):
    a, b = polar(-140), polar(-40)
    return led_busur(-140, -40, w) + penanda(a, "A", w) + penanda(b, "B", w)


def r_tali_busur(w):
    a, b = polar(-140), polar(-40)
    return led_garis(a, b, w, 50) + penanda(a, "A", w) + penanda(b, "B", w)


def r_juring(w):
    a, b = polar(-120), polar(-30)
    lx, ly = polar(-75, R * .55)
    return (bidang(f"M {CX} {CY} L {a[0]:.1f} {a[1]:.1f} A {R} {R} 0 0 1 {b[0]:.1f} {b[1]:.1f} Z", w, .16)
            + led_garis(O, a, w, 30) + led_garis(O, b, w, 30) + led_busur(-120, -30, w)
            + penanda(O, "O", w) + teks(lx, ly, "Juring", w, 15, "middle"))


def r_tembereng(w):
    a, b = polar(-140), polar(-40)
    return (bidang(f"M {a[0]:.1f} {a[1]:.1f} A {R} {R} 0 0 1 {b[0]:.1f} {b[1]:.1f} Z", w, .2)
            + led_busur(-140, -40, w) + led_garis(a, b, w, 45) + penanda(a, "A", w) + penanda(b, "B", w)
            + teks(CX, (a[1] + CY - R)/2 + 5, "Tembereng", w, 14, "middle"))


def r_apotema(w):
    a, b = polar(-140), polar(-40)
    m = (CX, a[1])
    return (led_garis(a, b, "#4c6881", 45) + led_garis(O, m, w, 40) + penanda(O, "O", w)
            + penanda(m, "M", w) + siku_siku(m, (0, 1), (1, 0), w))


def r_garis_singgung(w):
    t = (CX + R, CY)
    return (led_garis((t[0], CY - 160), (t[0], CY + 160), w, 55) + led_garis(O, t, "#00eaff", 35)
            + penanda(O, "O", "#00eaff") + penanda(t, "T", w) + siku_siku(t, (-1, 0), (0, -1), w)
            + teks(t[0] - 10, CY - 172, "Garis Singgung", w, 14, "end"))


RENDERER: dict[str, Callable[[str], str]] = {
    "Titik Pusat": r_titik_pusat, "Jari-jari": r_jari_jari, "Diameter": r_diameter,
    "Keliling": r_keliling, "Busur": r_busur, "Tali Busur": r_tali_busur, "Juring": r_juring,
    "Tembereng": r_tembereng, "Apotema": r_apotema, "Garis Singgung": r_garis_singgung,
}

# ------------------------------------------------------ KOMPONEN HTML/JS

TEMPLATE = r"""<!DOCTYPE html><html lang="id"><head><meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800&family=Poppins:wght@400;500;600&display=swap');
*{box-sizing:border-box} html,body{margin:0;height:100%;overflow:hidden;font-family:Poppins,sans-serif;color:#eaf6ff;background:#070c18}
#root{position:relative;height:100vh;--c:#00eaff;border-radius:18px;overflow:hidden;border:1px solid #24415c;
 background:radial-gradient(ellipse at 75% 40%,#122b43,transparent 55%),linear-gradient(135deg,#070c18,#0b1425)}
video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transform:scaleX(-1);opacity:0;transition:opacity .6s}
video.on{opacity:1}
.shade{position:absolute;inset:0;background:linear-gradient(90deg,rgba(7,12,24,.35),rgba(7,12,24,0) 26%,rgba(7,12,24,0))}
.ui{position:absolute;inset:0;display:grid;grid-template-columns:250px 1fr;gap:16px;padding:14px}
.side{display:flex;flex-direction:column;gap:7px;min-height:0}
.hd{font-family:Orbitron,sans-serif;color:#79eaff;letter-spacing:2px;font-size:13px;margin:2px 0 2px}
.btn{all:unset;box-sizing:border-box;cursor:pointer;display:flex;align-items:center;min-height:46px;padding:0 14px;border-radius:12px;
 border:1px solid #24415c;background:rgba(15,31,51,.85);color:#d8edff;font-size:14px;font-weight:500;transition:.2s}
.btn:hover,.btn.hover{background:rgba(0,190,230,.18);border-color:#00eaff;color:#8af5ff;box-shadow:0 0 14px rgba(0,234,255,.4);transform:translateX(4px)}
.btn.active{background:linear-gradient(100deg,#103d59,#142b4b);border-color:#00eaff;color:#8af5ff;box-shadow:0 0 12px rgba(0,234,255,.3)}
.row{display:flex;gap:7px}.row .btn{flex:1;justify-content:center;min-height:40px;padding:0 6px;font-size:12px}
.status{font-size:11px;color:#7ea3c2;min-height:30px;line-height:1.4}
.main{display:flex;flex-direction:column;min-height:0;min-width:0}
.title{text-align:center;font-family:Orbitron,sans-serif;font-weight:800;font-size:22px;letter-spacing:2px;color:var(--c);text-shadow:0 0 12px var(--c)}
.kat{text-align:center;color:#8fb2d1;font-size:11px;letter-spacing:2px;margin-bottom:4px}
.stage{flex:1;min-height:0;display:flex;justify-content:center}
svg{height:100%;max-width:100%;border:1px solid #284965;border-radius:22px;background:rgba(8,17,31,.08);box-shadow:0 0 20px rgba(0,234,255,.12)}
.info{margin-top:10px;background:rgba(11,25,43,.62);backdrop-filter:blur(6px);border:1px solid #23435e;border-radius:14px;padding:12px 16px}
.info b{color:#70eaff;font-size:15px}.info p{margin:4px 0;color:#c3d6e8;font-size:13px;line-height:1.6}
.rumus{display:inline-block;padding:3px 12px;border:1px dashed #2f5877;border-radius:8px;color:#8af5ff;font-family:Orbitron,sans-serif;font-size:12px}
.led{opacity:0;transform-box:fill-box;transform-origin:center;animation:nyala .45s ease forwards;animation-delay:var(--delay)}
@keyframes nyala{0%{opacity:0;transform:scale(.2)}65%{opacity:1;transform:scale(1.25)}100%{opacity:1;transform:scale(1)}}
@media (prefers-reduced-motion:reduce){.led{animation:none;opacity:1}}
.label{font-family:Arial,sans-serif;filter:drop-shadow(0 0 5px var(--c))}
#ptr{position:fixed;left:0;top:0;width:56px;height:56px;margin:-28px 0 0 -28px;pointer-events:none;display:none;z-index:9}
#ptr .dot{position:absolute;left:21px;top:21px;width:14px;height:14px;border-radius:50%;background:#fff;box-shadow:0 0 14px #fff,0 0 28px var(--c)}
#ptr.pinch .dot{background:#ff54d9;box-shadow:0 0 16px #ff54d9,0 0 30px #ff54d9;transform:scale(.8)}
#ptr svg{position:absolute;inset:0;width:56px;height:56px;border:0;background:none;box-shadow:none;transform:rotate(-90deg)}
</style></head><body>
<div id="root">
 <video id="vid" playsinline muted></video><div class="shade"></div>
 <div class="ui">
  <div class="side">
   <div class="hd">✦ PILIH UNSUR</div>
   <div id="list" style="display:flex;flex-direction:column;gap:7px"></div>
   <div class="hd" style="margin-top:6px">KONTROL</div>
   <div class="row"><div class="btn" data-act="mode:dwell" id="m-dwell">✋ Tahan 1 dtk</div><div class="btn" data-act="mode:pinch" id="m-pinch">🤏 Cubit</div></div>
   <div class="btn" id="camBtn" style="justify-content:center;min-height:40px;font-size:12px">📷 Aktifkan Kamera</div>
   <div class="row"><div class="btn" data-act="cam:down">🔅 Redup</div><div class="btn" data-act="cam:up">🔆 Terang</div></div>
   <div class="btn" id="sndBtn" data-act="snd:toggle" style="justify-content:center;min-height:40px;font-size:12px">🔊 Suara: Hidup</div>
   <div class="row" id="bgmRow"><div class="btn" id="bgmBtn" data-act="bgm:toggle" style="flex:2">🎵 Lagu: Hidup</div><div class="btn" data-act="bgm:down">🔉</div><div class="btn" data-act="bgm:up">🔊</div></div>
   <div class="status" id="status">Kamera mati. Mouse tetap bisa dipakai.</div>
  </div>
  <div class="main">
   <div class="title" id="t"></div><div class="kat" id="k"></div>
   <div class="stage"><svg viewBox="0 0 600 600" role="img" aria-label="Ilustrasi unsur lingkaran">
    <defs><pattern id="g" width="30" height="30" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#31516e" opacity=".3"/></pattern></defs>
    <rect width="600" height="600" fill="url(#g)"/>
    <circle cx="300" cy="300" r="205" fill="none" stroke="#7fd6ff" stroke-width="2.5" opacity=".7"/>
    <circle cx="300" cy="300" r="210" fill="none" stroke="#00d9ff" stroke-width="1" opacity=".17"/>
    <circle cx="300" cy="300" r="3" fill="#b4d8f5"/><g id="layer"></g></svg></div>
   <div class="info"><b id="it"></b><p id="id"></p><p>🎵 Lagu: <b id="lj" style="color:var(--c)"></b></p><span class="rumus" id="ir" style="display:none"></span></div>
  </div>
 </div>
 <div id="ptr"><svg viewBox="0 0 56 56"><circle cx="28" cy="28" r="22" fill="none" stroke="rgba(255,255,255,.25)" stroke-width="4"/>
  <circle id="ring" cx="28" cy="28" r="22" fill="none" stroke="var(--c)" stroke-width="4" stroke-linecap="round" stroke-dasharray="138.2" stroke-dashoffset="138.2"/></svg><div class="dot"></div></div>
</div>
<script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469240/hands.js" crossorigin="anonymous"></script>
<script>
const DATA=__DATA__, DWELL_MS=1000, PINCH_ON=.28, PINCH_OFF=.42;
const $=id=>document.getElementById(id), root=$('root'), ptr=$('ptr'), ring=$('ring'), vid=$('vid');
let aktif=null, mode='dwell';

const bgm=new Audio(); let vol=.5, ducking=false, duckId=0, laguOn=true;
bgm.loop=true; bgm.volume=vol;
bgm.onerror = () => {
  status('GAGAL MEMUAT LAGU: ' + bgm.src);
};

bgm.oncanplay = () => {
  status('File lagu berhasil dimuat. Silakan dengarkan musiknya.');
};
function setVol(){bgm.volume=Math.min(1,Math.max(0,ducking?vol*.3:vol));}
function putar(n){
  if(!laguOn)return;
  bgm.src=DATA[n].url;
  bgm.play().catch(()=>status('Lagu belum bisa diputar. Klik sekali dengan mouse dulu.'));
}
async function tesAudio() {
  const url = DATA["Jari-jari"].url;

  try {
    const response = await fetch(url);
    status(
      "Tes audio: HTTP " + response.status +
      " | Tipe: " + response.headers.get("content-type")
    );
  } catch (e) {
    status("Tes audio gagal: " + e.message);
  }
}
function toggleLagu(){
  if (bgm.paused) {
    laguOn = true;
    $('bgmBtn').textContent = '🎵 Lagu: Hidup';
    putar(aktif);
  } else {
    laguOn = false;
    $('bgmBtn').textContent = '🎵 Lagu: Mati';
    bgm.pause();
  }
}
function ubahVol(v){vol=Math.min(1,Math.max(0,vol+(v==='up'?.1:-.1)));setVol();status('Volume musik: '+Math.round(vol*100)+'%');}
let suara=true;
function bicara(n){
  if(!suara||!('speechSynthesis' in window))return;
  const sy=speechSynthesis; sy.cancel();
  const mk=(teks,lang)=>{const u=new SpeechSynthesisUtterance(teks);u.lang=lang;u.rate=.85;
    const v=sy.getVoices().find(x=>x.lang.replace('_','-').toLowerCase().startsWith(lang.slice(0,2)));if(v)u.voice=v;return u;};
  const last=mk(DATA[n].en,'en-US'), id=++duckId;
  last.onend=last.onerror=()=>{if(id===duckId){ducking=false;setVol();}};
  ducking=true; setVol();
  sy.speak(mk(n.replace('-',' '),'id-ID')); sy.speak(last);
}
function toggleSuara(){suara=!suara;if(!suara&&'speechSynthesis' in window)speechSynthesis.cancel();
  $('sndBtn').textContent=suara?'🔊 Suara: Hidup':'🔇 Suara: Mati';}
function pilih(n,ucap=false){
  aktif=n; const d=DATA[n]; root.style.setProperty('--c',d.warna);
  $('t').textContent=n.toUpperCase(); $('k').textContent=d.en.toUpperCase()+' • '+d.kategori; $('lj').textContent=d.lagu;
  if(ucap){putar(n);bicara(n);}
  $('it').textContent='✧ Mengenal '+n; $('id').textContent=d.deskripsi;
  const r=$('ir'); r.style.display=d.rumus?'inline-block':'none'; r.textContent=d.rumus;
  $('layer').innerHTML=d.svg;
  document.querySelectorAll('[data-act^="unsur:"]').forEach(b=>b.classList.toggle('active',b.dataset.act==='unsur:'+n));
}
function setMode(m){mode=m;$('m-dwell').classList.toggle('active',m==='dwell');$('m-pinch').classList.toggle('active',m==='pinch');
  status(m==='dwell'?'Mode TAHAN: arahkan telunjuk ke tombol dan diamkan 1 detik.':'Mode CUBIT: arahkan jari ke tombol, lalu temukan ibu jari dan telunjuk.');}
let br=1.6;
function setCam(){vid.style.filter=`brightness(${br.toFixed(2)}) contrast(1.1) saturate(1.1)`;}
function ubahCam(v){br=Math.min(3,Math.max(.8,br+(v==='up'?.2:-.2)));setCam();status('Kecerahan kamera: '+Math.round(br*100)+'%');}
function aksi(a){const [j,v]=a.split(':'); if(j==='unsur')pilih(v,true); else if(j==='mode')setMode(v); else if(j==='cam')ubahCam(v); else if(j==='snd')toggleSuara(); else if(j==='bgm'){v==='toggle'?toggleLagu():ubahVol(v);}}
setCam();
function status(s){$('status').textContent=s}

Object.keys(DATA).forEach(n=>{const b=document.createElement('div');b.className='btn';b.dataset.act='unsur:'+n;b.textContent='○  '+n;$('list').appendChild(b);});
document.addEventListener('click',e=>{const t=e.target.closest('[data-act]');if(t)aksi(t.dataset.act);});
pilih('Jari-jari'); setMode('dwell');

// ---- Kamera & pelacakan tangan
let hands=null, px=-100, py=-100, cur=null, since=0, locked=false, pinching=false, running=false;
$('camBtn').addEventListener('click',startCam);

async function startCam(){
  if(running)return;
  if(typeof Hands==='undefined'){status('Library MediaPipe gagal dimuat. Periksa koneksi internet.');return;}
  try{
    status('Meminta izin kamera...');
    vid.srcObject=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1920},height:{ideal:1080},facingMode:'user'},audio:false});
    await vid.play(); vid.classList.add('on');
    hands=new Hands({locateFile:f=>'https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469240/'+f});
    hands.setOptions({maxNumHands:1,modelComplexity:1,minDetectionConfidence:.6,minTrackingConfidence:.5});
    hands.onResults(hasil); running=true; $('camBtn').textContent='📷 Kamera Aktif'; $('camBtn').classList.add('active');
    status('Mencari tangan... angkat satu tangan ke depan kamera.'); loop();
  }catch(e){status('Kamera gagal: '+(e.name==='NotAllowedError'?'izin ditolak.':e.message));}
}
async function loop(){ if(vid.readyState>=2){try{await hands.send({image:vid});}catch(e){}} requestAnimationFrame(loop); }

function toScreen(lm){ // cover + mirror
  const W=innerWidth,H=innerHeight,vw=vid.videoWidth,vh=vid.videoHeight,s=Math.max(W/vw,H/vh);
  return [W-(lm.x*vw*s-(vw*s-W)/2), lm.y*vh*s-(vh*s-H)/2];
}
const d2=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);

function hasil(r){
  const L=r.multiHandLandmarks&&r.multiHandLandmarks[0];
  if(!L){ptr.style.display='none';reset();status('Tangan tidak terdeteksi.');return;}
  const rasio=d2(L[4],L[8])/(d2(L[0],L[9])||1), pinch=pinching?rasio<PINCH_OFF:rasio<PINCH_ON;
  const [tx,ty]=mode==='pinch'?toScreen({x:(L[4].x+L[8].x)/2,y:(L[4].y+L[8].y)/2}):toScreen(L[8]);
  px+=(tx-px)*.4; py+=(ty-py)*.4;
  ptr.style.display='block'; ptr.style.transform=`translate(${px}px,${py}px)`; ptr.classList.toggle('pinch',mode==='pinch'&&pinch);
  const el=document.elementFromPoint(px,py), t=el&&el.closest('[data-act]');
  if(t!==cur){document.querySelectorAll('.hover').forEach(x=>x.classList.remove('hover'));cur=t;since=performance.now();locked=false;ring.style.strokeDashoffset=138.2;if(t)t.classList.add('hover');}
  if(mode==='dwell'&&cur&&!locked){
    const p=Math.min((performance.now()-since)/DWELL_MS,1); ring.style.strokeDashoffset=138.2*(1-p);
    if(p>=1){const a=cur.dataset.act;aksi(a);ring.style.strokeDashoffset=138.2;
      if(/^(cam|bgm):(up|down)$/.test(a))since=performance.now(); else locked=true;}
  } else if(mode==='pinch'){
    if(pinch&&!pinching&&cur)aksi(cur.dataset.act);
    ring.style.strokeDashoffset=138.2;
  }
  pinching=pinch; status('Tangan terdeteksi ✓');
}
function reset(){document.querySelectorAll('.hover').forEach(x=>x.classList.remove('hover'));cur=null;locked=false;pinching=false;ring.style.strokeDashoffset=138.2;}
</script></body></html>"""


# Tabel lagu per unsur: (judul tampil, nama file di folder ./static)
# Ubah di sini bila pasangan file-lagu perlu dikoreksi.
STATIC_DIR = Path(__file__).with_name("static")
STATIC_URL = "/app/static"          # alamat folder ./static saat enableStaticServing = true
LAGU: dict[str, tuple[str, str]] = {
    "Titik Pusat":    ("Tante", "lagu_01.mp3"),
    "Busur":          ("Please Don't Call", "lagu_02.m4a"),
    "Garis Singgung": ("About You", "lagu_03.m4a"),
    "Jari-jari":      ("Nobody Son", "lagu_04.m4a"),
    "Diameter":       ("What If I Call", "lagu_05.mp3"),
    "Tembereng":      ("Wonderwall", "lagu_06.mp3"),
    "Keliling":       ("Wish List", "lagu_07.mp3"),
    "Tali Busur":     ("The Man Who Can't Be Moved", "lagu_08.m4a"),
    "Juring":         ("Everything U Are", "lagu_09.mp3"),
    "Apotema":        ("Tarot", "lagu_10.m4a"),
}


def bangun_html() -> str:
    data = {n: {"kategori": u.kategori, "deskripsi": u.deskripsi, "warna": u.warna,
                "rumus": u.rumus, "en": EN[n], "svg": RENDERER[n](u.warna),
                "lagu": LAGU[n][0], "url": f"{STATIC_URL}/{LAGU[n][1]}"} for n, u in UNSUR.items()}
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", payload)


# ----------------------------------------------------------------- UI

st.markdown("""
<style>
.stApp{background:linear-gradient(135deg,#070c18,#0b1425 55%,#080d19);color:#eaf6ff}
header[data-testid="stHeader"]{background:transparent}
.block-container{padding-top:1.5rem;max-width:1450px}
#MainMenu,footer{visibility:hidden}
.t{font-family:Orbitron,sans-serif;text-align:center;font-size:clamp(26px,4vw,40px);font-weight:800;letter-spacing:5px;
color:#8af5ff;text-shadow:0 0 5px #00eaff,0 0 15px #00bfff,0 0 35px #008cff}
.s{text-align:center;color:#94b6d0;font-size:13px;letter-spacing:2px;margin:-4px 0 14px}
</style>
<div class="t">NEON CIRCLE</div>
<div class="s">GESTURE CONTROL • CIRCLE GEOMETRY</div>
""", unsafe_allow_html=True)

_hilang = [f for _, f in LAGU.values() if not (STATIC_DIR / f).is_file()]
if _hilang:
    st.warning(f"File lagu belum ada di folder static/: {', '.join(_hilang)}")

components.html(bangun_html(), height=800, scrolling=False)

with st.expander("ℹ️ Petunjuk penggunaan untuk guru"):
    st.markdown(
        "1. Klik **Aktifkan Kamera**, lalu pilih *Allow* saat browser meminta izin.\n"
        "2. Angkat **satu tangan** dengan telapak menghadap kamera. Titik putih di ujung telunjuk adalah pointer.\n"
        "3. **Mode Tahan:** arahkan pointer ke tombol unsur dan diamkan 1 detik sampai lingkaran terisi penuh.\n"
        "4. **Mode Cubit:** arahkan pointer ke tombol, lalu temukan ibu jari dan telunjuk (titik berubah pink).\n"
        "5. Setiap unsur yang dipilih akan disebutkan dalam bahasa Indonesia lalu bahasa Inggris "
        "(contoh: \"jari jari\" → \"radius\"). Suara bisa dimatikan lewat tombol **Suara**.\n"
        "6. **Lagu per unsur:** setiap unsur punya lagu sendiri (judulnya tampil di panel bawah) dan otomatis "
        "diputar saat dipilih. File lagu ada di folder `static/`; tombol 🎵 mematikan/menyalakan lagu. "
        "Klik sekali dengan mouse dulu agar browser mengizinkan suara.\n"
        "7. Pencahayaan sebaiknya cukup dan latar tidak terlalu ramai. Mouse tetap berfungsi sebagai cadangan."
    )
