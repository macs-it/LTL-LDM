"""DACHSER Packer Vicenza – Modern UI.

Versione Streamlit con motore Planner 1.0 beta 5 e PDF invariati.
Le modifiche rispetto alla precedente versione riguardano esclusivamente
l'interfaccia e la visualizzazione a schermo del pianale.
"""
import io
from datetime import datetime
from collections import OrderedDict
from html import escape as html_escape

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- LIBRERIE REPORTLAB ---
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import ImageReader

# --- COSTANTI DI CONFIGURAZIONE (INVARIATE) ---
PALETTE = ['#3498db', '#e67e22', '#2ecc71', '#9b59b6', '#f1c40f', '#e74c3c', '#1abc9c', '#34495e', '#d35400', '#7f8c8d']
MAX_SOVR_LIVELLI_DEFAULT = 2

st.set_page_config(page_title="DACHSER Packer - Vicenza", page_icon="🚛", layout="wide", initial_sidebar_state="collapsed")

# --- DESIGN SYSTEM: SOLO CSS / PRESENTAZIONE ---
st.markdown("""
<style>
:root { --navy:#002855; --navy2:#073965; --yellow:#ffd100; --ink:#12253d; --muted:#66778c; --line:#dce5ef; --canvas:#f3f6fa; }
.stApp, [data-testid="stAppViewContainer"] { background:var(--canvas); color:var(--ink); }
[data-testid="stHeader"] { background:transparent; }
.block-container { max-width:1600px; padding-top:1.55rem; padding-bottom:3.8rem; }
#MainMenu { visibility:hidden; }
h1,h2,h3,h4,h5 { color:var(--ink); }
p { line-height:1.42; }
.packer-hero { background:linear-gradient(118deg,#002855 0%,#073965 73%,#0a4773 100%); color:white; border-radius:17px; padding:18px 23px; display:flex; align-items:center; justify-content:space-between; gap:16px; box-shadow:0 9px 22px rgba(0,40,85,.12); border-bottom:4px solid var(--yellow); margin-bottom:18px; }
.packer-brand { font-size:26px; font-weight:900; color:var(--yellow); letter-spacing:.045em; line-height:1; }
.packer-subtitle { color:#c5d7ea; font-size:11px; letter-spacing:.12em; font-weight:700; text-transform:uppercase; margin-top:8px; }
.packer-hero-right { text-align:right; }
.packer-app { font-size:18px; font-weight:850; color:#fff; letter-spacing:.015em; }
.packer-version { font-size:11px; color:#c5d7ea; margin-top:4px; }
.section-label { color:#66809a; font-size:10px; letter-spacing:.14em; font-weight:850; margin-bottom:3px; text-transform:uppercase; }
.section-title { color:#002855; font-size:19px; font-weight:850; letter-spacing:-.025em; line-height:1.26; margin-bottom:11px; }
.panel-intro { color:#60758b; font-size:12px; margin-bottom:7px; }
[data-testid="stVerticalBlockBorderWrapper"] { background:#fff; border-color:var(--line) !important; border-radius:14px !important; box-shadow:0 2px 11px rgba(1,30,60,.035); }
[data-testid="stExpander"] { border:1px solid var(--line); border-radius:12px; background:#fff; box-shadow:0 2px 11px rgba(1,30,60,.025); }
[data-testid="stExpander"] summary { font-weight:750; color:#002855; }
[data-testid="stWidgetLabel"] p { font-weight:650; color:#36506b; font-size:12px; }
[data-baseweb="input"] { border-radius:9px; }
.stButton > button { border-radius:9px; font-weight:760; border:1px solid #cfdce9; background:#fff; color:var(--navy); min-height:39px; transition:background .12s, border-color .12s; }
.stButton > button:hover { border-color:var(--navy); color:var(--navy); background:#edf4fa; }
.stButton > button[kind="primary"] { background:var(--navy); color:#fff; border:1px solid var(--navy); font-weight:850; }
.stButton > button[kind="primary"]:hover { background:#064073; color:#fff; }
.stDownloadButton > button { border-radius:9px; font-weight:850; color:#002855; background:var(--yellow); border:1px solid #edc300; min-height:40px; }
.stDownloadButton > button:hover { color:#002855; background:#ffdb39; border-color:#e5ba00; }
[data-testid="stAlert"] { border-radius:10px; padding:10px 13px; }
.packer-kpi { background:#f4f8fc; border:1px solid #e0eaf3; border-radius:11px; padding:15px 17px; }
.packer-kpi.warning { background:#fff4f1; border-color:#fac8bf; }
.packer-kpi.good { background:#eaf8ef; border-color:#bbdfc8; }
.packer-kpi-title { font-size:10px; font-weight:850; text-transform:uppercase; letter-spacing:.12em; color:#5c738b; }
.packer-kpi-number { font-size:38px; line-height:1.05; letter-spacing:-.05em; font-weight:900; color:#002855; margin:6px 0 4px; font-variant-numeric:tabular-nums; }
.packer-kpi-note { color:#50657c; font-size:12px; }
.packer-status { font-size:12px; font-weight:750; margin:10px 0 6px; color:#167247; }
.packer-status.warn { color:#c03d2c; }
.packer-track { height:10px; border-radius:50px; background:#e6edf4; overflow:hidden; width:100%; }
.packer-track-fill { height:100%; background:#19875b; border-radius:50px; }
.packer-track-fill.warn { background:#db5b4d; }
.packer-track-annotation { margin-top:5px; color:#718397; display:flex; justify-content:space-between; font-size:10px; font-weight:700; }
.packer-pill-set { display:flex; flex-wrap:wrap; gap:7px; padding:4px 0; }
.packer-pill { display:inline-flex; align-items:center; gap:7px; padding:7px 10px; border:1px solid #e0e8f1; background:#f5f8fc; border-radius:9px; font-size:11px; color:#456079; }
.packer-pill b { color:#002855; font-variant-numeric:tabular-nums; }
.packer-dot { display:inline-block; flex:0 0 auto; width:9px; height:9px; border-radius:3px; }
.packer-smallhead { font-size:11px; color:#577089; font-weight:850; letter-spacing:.06em; text-transform:uppercase; margin:10px 0 5px; }
.packer-count { display:inline-block; border-radius:40px; padding:3px 8px; background:#e7f0fa; color:#002855; font-size:11px; font-weight:850; }
.packer-row { color:#385069; font-size:12px; line-height:1.6; padding:4px 0; }
.packer-row b { color:#002855; }
.packer-empty { padding:28px 15px; background:linear-gradient(135deg,#f5f9fe,#eaf2fa); border:1px dashed #c3d5e6; border-radius:12px; text-align:center; color:#48627b; }
.packer-empty b { display:block; font-size:14px; margin-bottom:6px; color:#002855; }
.packer-help { font-size:11px; color:#70849a; padding-top:3px; }
@media (max-width:820px) { .block-container { padding-top:.8rem; } .packer-hero { padding:15px 16px; } .packer-brand { font-size:22px; } .packer-app { font-size:13px; } .packer-subtitle,.packer-version { font-size:9px; } .packer-kpi-number { font-size:32px; } }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="packer-hero">
  <div><div class="packer-brand">DACHSER</div><div class="packer-subtitle">VICENZA / DISTRIBUTION</div></div>
  <div class="packer-hero-right"><div class="packer-app">Packer · Ottimizzazione pianale</div><div class="packer-version">Multi-drop · Motore Planner 1.0 beta 5</div></div>
</div>
""", unsafe_allow_html=True)

# --- GESTIONE STATO ---
if 'lista_di_carico' not in st.session_state:
    st.session_state.lista_di_carico = []
if 'editing_index' not in st.session_state:
    st.session_state.editing_index = None
if 'last_result' not in st.session_state:
    st.session_state.last_result = None

def invalidate_result():
    """Annulla l'ultimo piano quando cambiano dati o parametri di calcolo."""
    st.session_state.last_result = None

def get_next_scarico_name():
    if not st.session_state.lista_di_carico:
        return "SCARICO 1"
    return f"SCARICO {len(OrderedDict.fromkeys([item[0] for item in st.session_state.lista_di_carico])) + 1}"

# Inizializzazione pulita di tutte le variabili collegate ai campi
if 'val_g' not in st.session_state:
    st.session_state.val_g = get_next_scarico_name()
for val, default in [('val_q', 1), ('val_l', 120), ('val_w', 80), ('val_h', 150), ('val_s', False), ('val_max_sovr', MAX_SOVR_LIVELLI_DEFAULT)]:
    if val not in st.session_state:
        st.session_state[val] = default

def _normalize_item(item):
    """
    Ritorna sempre una tupla a 7 elementi:
    (g, l, w, h, s, q, max_livelli)
    """
    if len(item) == 6:
        g, l, w, h, s, q = item
        max_liv = MAX_SOVR_LIVELLI_DEFAULT if s else 1
    else:
        g, l, w, h, s, q, max_liv = item
    return g, l, w, h, s, q, max_liv

# --- CALLBACK PER LA CASELLA SOVRAPPONIBILE ---
def on_sovr_change():
    """Viene eseguita nell'istante in cui si clicca la spunta Sovr."""
    if st.session_state.val_s:
        st.session_state.val_max_sovr = MAX_SOVR_LIVELLI_DEFAULT

# --- FUNZIONI LISTA INTERFACCIA ---
def aggiungi_voce():
    invalidate_result()
    voce = (
        st.session_state.val_g.upper(),
        st.session_state.val_l,
        st.session_state.val_w,
        st.session_state.val_h,
        st.session_state.val_s,
        st.session_state.val_q,
        st.session_state.val_max_sovr if st.session_state.val_s else 1,
    )
    if st.session_state.editing_index is None:
        st.session_state.lista_di_carico.append(voce)
    else:
        st.session_state.lista_di_carico[st.session_state.editing_index] = voce
        st.session_state.editing_index = None

    st.session_state.val_q = 1
    st.session_state.val_l = 120
    st.session_state.val_w = 80
    st.session_state.val_h = 150
    st.session_state.val_s = False
    st.session_state.val_max_sovr = MAX_SOVR_LIVELLI_DEFAULT

def elimina_riga(index):
    invalidate_result()
    st.session_state.lista_di_carico.pop(index)
    if st.session_state.editing_index == index:
        st.session_state.editing_index = None
    elif st.session_state.editing_index is not None and index < st.session_state.editing_index:
        st.session_state.editing_index -= 1

def edita_riga(index):
    g, l, w, h, s, q, max_liv = _normalize_item(st.session_state.lista_di_carico[index])
    st.session_state.editing_index = index
    st.session_state.val_g = g
    st.session_state.val_l = l
    st.session_state.val_w = w
    st.session_state.val_h = h
    st.session_state.val_s = s
    st.session_state.val_q = q
    st.session_state.val_max_sovr = max_liv

def annulla_modifica():
    st.session_state.editing_index = None
    st.session_state.val_q = 1
    st.session_state.val_l = 120
    st.session_state.val_w = 80
    st.session_state.val_h = 150
    st.session_state.val_s = False
    st.session_state.val_max_sovr = MAX_SOVR_LIVELLI_DEFAULT

# --- MOTORE DI CALCOLO: PORTING DAL PLANNER 1.0 BETA 5 NON SSCC ---
# Il Planner 1.0 beta 5 NON SSCC usa MaxRects/frontier, ordinamenti multipli,
# beam search e pairing di due livelli. Porting in Python senza dipendenze JS.
# Per Max_Liv > 2, conserviamo la formazione di pile omogenee della Packer v4.
# Il risultato è una stima euristica geometrica, non un ottimo globale provato.

CONFIGS = [(0, 0), (0, 2), (0, 3), (1, 1), (1, 4), (0, 5),
           (1, 2), (2, 6), (3, 7), (4, 2), (5, 1), (6, 0)]


def _hash(uid, seed):
    x = ((uid & 0xffffffff) ^ (((seed + 1) * 2654435761) & 0xffffffff)) & 0xffffffff
    x = (((x ^ (x >> 16)) * 2246822507) & 0xffffffff)
    return (x ^ (x >> 13)) & 0xffffffff


def _orientation(p, rotate):
    l, w = p['length_mm'], p['width_mm']
    return [(l, w, False)] + ([(w, l, True)] if rotate and l != w else [])


def _fit(base, top, rotate):
    return next(((l,w,r) for l,w,r in _orientation(top,rotate)
                 if l <= base['length_mm'] and w <= base['width_mm']), None)


def _area(p):
    return p['length_mm'] * p['width_mm']


def _end(p):
    return p['x'] + p['length_mm']


def _used(placements):
    return max((_end(p) for p in placements), default=0)


def _prune(rects):
    unique = {(r['x'],r['y'],r['w'],r['h']):r for r in rects if r['w']>0 and r['h']>0}
    vals = list(unique.values())
    return [a for i,a in enumerate(vals) if not any(
        i!=j and a['x']>=b['x'] and a['y']>=b['y'] and
        a['x']+a['w']<=b['x']+b['w'] and a['y']+a['h']<=b['y']+b['h']
        for j,b in enumerate(vals))]


def _split(f,u):
    if u['x']>=f['x']+f['w'] or u['x']+u['w']<=f['x'] or u['y']>=f['y']+f['h'] or u['y']+u['h']<=f['y']:
        return [f]
    out=[]
    if u['x']>f['x']: out.append(dict(x=f['x'],y=f['y'],w=u['x']-f['x'],h=f['h']))
    if u['x']+u['w']<f['x']+f['w']: out.append(dict(x=u['x']+u['w'],y=f['y'],w=f['x']+f['w']-u['x']-u['w'],h=f['h']))
    if u['y']>f['y']: out.append(dict(x=f['x'],y=f['y'],w=f['w'],h=u['y']-f['y']))
    if u['y']+u['h']<f['y']+f['h']: out.append(dict(x=f['x'],y=u['y']+u['h'],w=f['w'],h=f['y']+f['h']-u['y']-u['h']))
    return out


def _profile(ps,W):
    ys=sorted({0,W,*[coord for p in ps for coord in (p['y'],p['y']+p['width_mm'])]})
    out=[]
    for y,z in zip(ys,ys[1:]):
        height=z-y
        x=max((_end(p) for p in ps if p['y']<z and p['y']+p['width_mm']>y),default=0)
        if out and out[-1]['x']==x: out[-1]['h']+=height
        else: out.append(dict(y=y,h=height,x=x))
    return out


def _frontier(ps,L,W):
    bands=_profile(ps,W);out=[]
    for i in range(len(bands)):
        x=0;h=0
        for b in bands[i:]:
            x=max(x,b['x']);h+=b['h']
            if x<L:out.append(dict(x=x,y=bands[i]['y'],w=L-x,h=h))
    return _prune(out)


def _order(items,mode,W,rotate):
    def min_x(p):return min(l for l,w,_ in _orientation(p,rotate) if w<=W)
    if mode==0:return sorted(items,key=lambda p:(-max(p['length_mm'],p['width_mm']),-_area(p),p['uid']))
    if mode==1:return sorted(items,key=lambda p:(-_area(p),-min(p['length_mm'],p['width_mm']),p['uid']))
    if mode==2:return sorted(items,key=lambda p:(-min_x(p),-_area(p),p['uid']))
    if mode==3:return sorted(items,key=lambda p:p['uid'])
    return sorted(items,key=lambda p:(_hash(p['uid'],mode),p['uid']))


def _placement(p,x,y,l,w,rot):
    return dict(uid=p['uid'],document=p['document'],pallet_id=p['pallet_id'],
                priority=p['priority'],layer=1,x=x,y=y,length_mm=l,width_mm=w,
                height_mm=p['height_mm'],weight_kg=p['weight_kg'],rotated=rot)


def _place_group(items,prior,inp,config):
    workL=max(inp['L'],_used(prior)+sum(max(p['length_mm'],p['width_mm']) for p in items))
    out=list(prior);free=_frontier(prior,workL,inp['W']);mx=_used(prior)
    for p in _order(items,config[0],inp['W'],inp['rotation']):
        best=None
        for f in free:
            for l,w,rot in _orientation(p,inp['rotation']):
                if l>f['w'] or w>f['h']:continue
                sh=min(f['w']-l,f['h']-w);lo=max(f['w']-l,f['h']-w)
                waste=f['w']*f['h']-l*w;new_end=max(mx,f['x']+l)
                mode=config[1]
                if mode==0: score=(f['x'],sh,lo,waste,f['y'])
                elif mode==1: score=(new_end,f['x'],f['y'],waste)
                elif mode==2: score=(f['x'],w,f['y'],new_end,waste)
                elif mode==3: score=(f['x'],l,f['y'],new_end,waste)
                elif mode==4: score=(f['x'],waste,sh,f['y'])
                elif mode==5: score=(sh,f['x'],waste,f['y'])
                elif mode==6: score=(f['x'],f['h']%w,f['y'],new_end)
                else: score=(f['x'],int(rot),f['y'],new_end)
                if best is None or score<best[0]:best=(score,f,l,w,rot)
        if best is None:
            opts=sorted(((l,w,r) for l,w,r in _orientation(p,inp['rotation']) if w<=inp['W']),key=lambda o:o[0])
            if not opts:raise ValueError('Collo non rappresentabile nel pianale')
            l,w,rot=opts[0];f={'x':mx,'y':0}
        else:_,f,l,w,rot=best
        u=dict(x=f['x'],y=f['y'],w=l,h=w)
        out.append(_placement(p,u['x'],u['y'],l,w,rot));mx=max(mx,u['x']+l)
        free=_prune([s for cell in free for s in _split(cell,u)])
    return out


def _keep_states(states,W,count):
    unique={}
    for ps in states:
        key=tuple((b['y'],b['h'],b['x']) for b in _profile(ps,W))
        unique.setdefault(key,ps)
    return sorted(unique.values(),key=lambda ps:(_used(ps),sum(b['h']*b['x'] for b in _profile(ps,W))))[:count]


def _pairing_plans(items,inp):
    plans=[[]];seen={()}
    if not inp['stacking']:return plans
    def can_base(p):return p['stack_flag']=='S'
    edges=[(b,t) for b in items if can_base(b) for t in items
           if b['uid']!=t['uid'] and b['priority']==t['priority']
           and not t.get('locked_stack') and b['height_mm']+t['height_mm']<=inp['H']
           and _fit(b,t,inp['rotation'])]
    def add(pairs):
        key=tuple(sorted((b['uid'],t['uid']) for b,t in pairs))
        if key not in seen:seen.add(key);plans.append(pairs)
    modes=6 if len(items)>120 else 10
    for mode in range(modes):
        def score(edge):
            b,t=edge;waste=_area(b)-_area(t);same=int(b['document']!=t['document']);scarce=int(can_base(t))
            if mode==0:return (-_area(t),waste,same,b['uid'],t['uid'])
            if mode==1:return (scarce,-_area(t),waste,same,b['uid'],t['uid'])
            if mode==2:return (same,-_area(t),waste,b['uid'],t['uid'])
            if mode==3:return (waste,-_area(t),b['uid'],t['uid'])
            if mode==4:return (-min(t['length_mm'],t['width_mm']),scarce,waste,b['uid'],t['uid'])
            return (-_area(t)*(0.6+0.8*_hash(b['uid']*1009+t['uid'],mode)/4294967296),waste,b['uid'],t['uid'])
        locked=set();pairs=[]
        for b,t in sorted(edges,key=score):
            if b['uid'] in locked or t['uid'] in locked:continue
            pairs.append((b,t));locked.update((b['uid'],t['uid']))
        add(pairs)
    if len(items)<=7 and edges:
        def visit(rest,pairs):
            if len(plans)>=100:return
            if not rest:add(pairs);return
            a=rest[0];tail=rest[1:]
            for j,z in enumerate(tail):
                for b,t in ((a,z),(z,a)):
                    if not can_base(b) or b['priority']!=t['priority'] or t.get('locked_stack') or b['height_mm']+t['height_mm']>inp['H'] or not _fit(b,t,inp['rotation']):continue
                    visit([v for k,v in enumerate(tail) if k!=j],pairs+[(b,t)])
            visit(tail,pairs)
        visit(items,[])
    else:
        for p in plans[1:4].copy():
            for i in range(min(len(p),4)):add([v for j,v in enumerate(p) if i!=j])
    return plans


def _floor_search(items,pairs,inp):
    tops={t['uid'] for b,t in pairs};floor=[p for p in items if p['uid'] not in tops]
    priorities=sorted({p['priority'] for p in floor},reverse=True)
    states=[[]];large=len(items)>120
    for priority in priorities:
        group=[p for p in floor if p['priority']==priority]
        next_states=[_place_group(group,prior,inp,config)
                     for prior in states for config in CONFIGS[:8 if large else 12]]
        states=_keep_states(next_states,inp['W'],3 if large else 6)
    return states[0]


def _assemble(inp,ps,pairs,original):
    placements=list(ps);by_uid={p['uid']:p for p in ps}
    for b,t in pairs:
        base=by_uid.get(b['uid']);o=base and _fit(base,t,inp['rotation'])
        if not o:raise ValueError('Coppia sovrapposta senza base orientata compatibile')
        l,w,rot=o
        v=_placement(t,base['x']+(base['length_mm']-l)//2,base['y']+(base['width_mm']-w)//2,l,w,rot)
        v.update(layer=2,base_uid=b['uid']);placements.append(v)
    placements.sort(key=lambda p:(p['layer'],p['x'],p['y'],p['uid']))
    length=_used(ps)
    return dict(placements=placements,length=length,layer1=len(ps),layer2=len(pairs),search_candidates=0)


def _validate(inp,result,source):
    ps=result['placements'];floor=[p for p in ps if p['layer']==1]
    if len(ps)!=len(source) or len({p['uid'] for p in ps})!=len(source):raise ValueError('Inventario pallet incoerente')
    orig={p['uid']:p for p in source};bases={p['uid']:p for p in floor};used_bases=set()
    for p in ps:
        s=orig[p['uid']]
        if p['x']<0 or p['y']<0 or p['y']+p['width_mm']>inp['W'] or p['height_mm']!=s['height_mm']:
            raise ValueError('Collo fuori limite o dimensioni non coerenti')
        if (p['length_mm'],p['width_mm'],p['rotated']) not in _orientation(s,inp['rotation']):
            raise ValueError('Rotazione non consentita')
        if p['layer']==2:
            b=bases.get(p.get('base_uid'))
            if not inp['stacking'] or b is None or b['uid'] in used_bases:
                raise ValueError('Base impilamento non valida')
            used_bases.add(b['uid'])
            if p['priority']!=b['priority'] or p['x']<b['x'] or p['y']<b['y'] or _end(p)>_end(b) or p['y']+p['width_mm']>b['y']+b['width_mm'] or p['height_mm']+b['height_mm']>inp['H']:
                raise ValueError('Coppia impilamento non valida')
            if orig[b['uid']]['stack_flag']!='S' or s.get('locked_stack'):
                raise ValueError('Impilamento non autorizzato')
    for i,a in enumerate(floor):
        for b in floor[i+1:]:
            lateral=a['y']<b['y']+b['width_mm'] and a['y']+a['width_mm']>b['y']
            if lateral and a['x']<_end(b) and _end(a)>b['x']:
                raise ValueError('Colli a pavimento intersecati')
            if lateral and ((a['priority']>b['priority'] and _end(a)>b['x']) or (b['priority']>a['priority'] and _end(b)>a['x'])):
                raise ValueError('Ordine degli scarichi non rispettato')
    if result['length']!=_used(floor):raise ValueError('Metri lineari incoerenti')


def solve_beta5(inp):
    """Ricerca beta 5: coppie, MaxRects frontier, ordinamenti, beam search, verifica geometrica."""
    W,H=inp['W'],inp['H']
    for p in inp['items']:
        if p['height_mm']>H:raise ValueError(f"Altezza collo {p['height_mm']/10:g} cm superiore al camion ({H/10:g} cm)")
        if not any(w<=W for l,w,r in _orientation(p,inp['rotation'])):
            raise ValueError(f"Il collo {p['label']} di '{p['document']}' supera la larghezza utile ({W/10:g} cm)")
    items=sorted(inp['items'],key=lambda p:(-p['priority'],p['uid']))
    plans=_pairing_plans(items,inp)
    # Incumbent veloce, come nell'originale beta 5.
    floor=[]
    for priority in sorted({p['priority'] for p in items},reverse=True):
        group=[p for p in items if p['priority']==priority]
        floor=_keep_states([_place_group(group,floor,inp,c) for c in CONFIGS[:3]],W,1)[0]
    best=_assemble(inp,floor,[],items);_validate(inp,best,items)
    attempts=0
    for pairs in plans:
        try:
            floor=_floor_search(items,pairs,inp)
            candidate=_assemble(inp,floor,pairs,items)
            _validate(inp,candidate,items)
        except ValueError:
            continue
        attempts+=1
        if (candidate['length'],-candidate['layer2']) < (best['length'],-best['layer2']):
            best=candidate
    best['search_candidates']=attempts
    _validate(inp,best,items)
    return best


def build_packing_input(lista_di_carico,camion_w,camion_l,camion_h,rotation,normalize_item):
    groups=list(OrderedDict.fromkeys(normalize_item(it)[0] for it in lista_di_carico))
    items=[];uid=0
    for row,item in enumerate(lista_di_carico):
        g,l,w,h,s,q,maxlev=normalize_item(item)
        if min(l,w,h,q,maxlev)<=0:raise ValueError(f'Valori non validi alla riga {row+1}')
        if not s: maxlev=1
        if h>camion_h:raise ValueError(f'Altezza {h} cm superiore all’altezza utile ({camion_h} cm)')
        tiers=min(maxlev,camion_h//h) if s else 1
        # Oltre i 2 livelli (non previsti dal motore JS), si formano le pile omogenee della v4.
        # Con max 2 si passa ogni pallet al pairing originale beta 5.
        chunks=[]
        if tiers>2:
            remaining=q
            while remaining:
                n=min(tiers,remaining);chunks.append(n);remaining-=n
        else:chunks=[1]*q
        for n in chunks:
            label=f'{l}x{w}'+(f'\nX{n}' if n>1 else '')
            items.append(dict(uid=uid,document=g,pallet_id=f'{row+1}-{uid+1}',priority=groups.index(g)+1,
                              length_mm=l*10,width_mm=w*10,height_mm=h*n*10,weight_kg=0,
                              stack_flag='S' if s and tiers==2 else 'N',locked_stack=n>1,
                              physical_count=n,label=label,original_dimensions=f'{l}x{w}'))
            uid+=1
    return dict(items=items,markers={},L=camion_l*10,W=camion_w*10,H=camion_h*10,
                rotation=rotation,stacking=True)


def layout_from_result(result,inp):
    source={p['uid']:p for p in inp['items']}
    tops={p['base_uid']:p for p in result['placements'] if p['layer']==2}
    rects=[]
    for p in result['placements']:
        if p['layer']!=1:continue
        s=source[p['uid']];top=tops.get(p['uid'])
        if top:
            t=source[top['uid']]
            label=(f"{s['original_dimensions']}\nX2" if s['original_dimensions']==t['original_dimensions']
                   else f"{s['original_dimensions']}\n+ {t['original_dimensions']}")
        else:label=s['label']
        rects.append(dict(x=p['y']//10,y=p['x']//10,w=p['width_mm']//10,h=p['length_mm']//10,
                          rid=label,gruppo=s['document'],rotated=p['rotated']))
    return rects,result['length']//10


def calcola_posizionamento(lista_di_carico, allow_rotation, camion_w, camion_l, camion_h):
    inp=build_packing_input(lista_di_carico,camion_w,camion_l,camion_h,allow_rotation,_normalize_item)
    candidate=solve_beta5(inp)
    rects,length=layout_from_result(candidate,inp)
    if allow_rotation:
        reference=dict(inp,rotation=False)
        try:
            baseline=solve_beta5(reference)
            b_rects,b_length=layout_from_result(baseline,reference)
            if b_length<=length:return b_rects,b_length
        except ValueError:
            pass
    return rects,length


def _ingombro_per_gruppo(rects, ordine_gruppi=None):
    """
    Somma le fasce longitudinali effettivamente occupate da ciascun gruppo.
    Eventuali vuoti tra due segmenti dello stesso scarico non vengono conteggiati.
    """
    intervalli = OrderedDict()
    for r in rects:
        intervalli.setdefault(r["gruppo"], []).append((r["y"], r["y"] + r["h"]))

    valori = {}
    for g, ints in intervalli.items():
        merged = []
        for start, end in sorted(ints, key=lambda it: it[0]):
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        valori[g] = sum(end - start for start, end in merged) / 100.0

    if ordine_gruppi is None:
        ordine_gruppi = list(intervalli.keys())
    return OrderedDict((g, valori[g]) for g in ordine_gruppi if g in valori)

# --- FUNZIONE GENERAZIONE PDF ---
def genera_pdf_reportlab(rects, lista_carico, ingombro, camion_w, camion_l, ingombro_per_gruppo=None):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    
    c.setFillColorRGB(0, 0.22, 0.41) 
    c.rect(0, height - 85, width, 85, fill=1)
    c.setFillColor(colors.yellow); c.setFont("Helvetica-Bold", 26)
    c.drawString(45, height - 45, "DACHSER")
    c.setFillColor(colors.white); c.setFont("Helvetica", 13)
    c.drawString(45, height - 70, "REPORT DI CARICO - Filiale di Vicenza")
    
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold", 10)
    c.drawString(400, height - 110, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    c.drawString(400, height - 125, f"Ingombro Totale: {ingombro/100:.2f} m (su {camion_l/100:.2f} m)")
    if ingombro_per_gruppo and len(ingombro_per_gruppo) > 1:
        per_scarico = " | ".join(f"{g}: {m:.2f} m" for g, m in ingombro_per_gruppo.items())
        c.setFont("Helvetica", 8)
        c.drawString(45, height - 140, f"Ingombro longitudinale per scarico: {per_scarico}")

    fig_pdf, ax_pdf = plt.subplots(figsize=(10, 4))
    ax_pdf.set_aspect('equal')
    ax_pdf.set_xlim(-50, max(1400, camion_l + 50)); ax_pdf.set_ylim(-20, max(260, camion_w + 20))
    ax_pdf.add_patch(patches.Rectangle((0, 0), camion_l, camion_w, fill=False, edgecolor='#00386A', lw=2))
    ax_pdf.text(-30, camion_w/2, "CABINA", ha='center', va='center', fontweight='bold', color='#00386A', rotation=90)
    
    gruppi_u = list(OrderedDict.fromkeys([_normalize_item(item)[0] for item in lista_carico]))
    mappa_c = {g: PALETTE[i % len(PALETTE)] for i, g in enumerate(gruppi_u)}
    
    for r in rects:
        ax_pdf.add_patch(
            patches.Rectangle((r['y'], r['x']), r['h'], r['w'], facecolor=mappa_c[r['gruppo']], edgecolor='black', alpha=0.85, lw=0.7)
        )
        ax_pdf.text(r['y'] + r['h'] / 2, r['x'] + r['w'] / 2, r['rid'].replace('\n', ' '), ha='center', va='center', fontsize=7, fontweight='bold')
    
    ax_pdf.axis('off')
    img_buffer = io.BytesIO()
    fig_pdf.savefig(img_buffer, format='png', bbox_inches='tight', dpi=180)
    plt.close(fig_pdf)
    img_buffer.seek(0)
    c.drawImage(ImageReader(img_buffer), 30, 400, width=535, preserveAspectRatio=True)

    if gruppi_u:
        legend_x = width - 180
        legend_y = height - 150
        row_h = 12
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.black)
        c.drawString(legend_x, legend_y + 10, "Legenda scarichi:")
        for idx, g in enumerate(gruppi_u):
            y = legend_y - (idx + 1) * row_h
            col = colors.HexColor(mappa_c[g])
            c.setFillColor(col)
            c.rect(legend_x, y, 10, 10, fill=1, stroke=0)
            c.setFillColor(colors.black)
            c.drawString(legend_x + 16, y + 1, str(g))

    c.setFont("Helvetica-Bold", 13)
    c.drawString(45, 360, "ELENCO MERCI CARICATE:")
    table_data = [["Destinazione", "Dim. (cm)", "Q.tà", "Sovr."]]
    for item in lista_carico:
        g, l, w, h, s, q, max_liv = _normalize_item(item)
        sovr_str = "Sì" if s else "No"
        if s:
            sovr_str += f" (max {max_liv})"
        table_data.append([g, f"{l}x{w}x{h}", str(q), sovr_str])
    
    t = Table(table_data, colWidths=[190, 120, 60, 70])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#00386A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.yellow),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.7, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    t.wrapOn(c, width, height)
    t.drawOn(c, 45, 340 - (len(table_data) * 20))

    c.showPage(); c.save(); buf.seek(0)
    return buf

# ==========================================
# --- NUOVO LAYOUT STREAMLIT: PRESENTAZIONE ---
# ==========================================

def _it_m(value):
    return f"{value:.2f}".replace('.', ',')


def _section(kicker, heading, description=None):
    st.markdown(
        f'<div class="section-label">{html_escape(kicker)}</div>'
        f'<div class="section-title">{html_escape(heading)}</div>'
        + (f'<div class="panel-intro">{html_escape(description)}</div>' if description else ''),
        unsafe_allow_html=True,
    )


def _draw_load_plan(rects, truck_w, truck_l, needed_l, groups):
    """Solo disegno: mantiene intatte le coordinate del motore beta 5.

    Coordinate interne: r['y'] = lunghezza / r['x'] = larghezza;
    nella vista orizzontale la cabina e' a sinistra, il portellone a destra.
    """
    limit = max(truck_l, needed_l)
    fig, ax = plt.subplots(figsize=(14.5, 3.65), dpi=145)
    fig.patch.set_facecolor('#ffffff')
    ax.set_facecolor('#ffffff')
    ax.add_patch(patches.Rectangle((0, 0), truck_l, truck_w,
                                   facecolor='#f7fafe', edgecolor='#002855', lw=2.2, zorder=1))
    if needed_l > truck_l:
        ax.axvspan(truck_l, needed_l, facecolor='#fff0ed', alpha=.9, zorder=0)
        ax.axvline(truck_l, color='#ce4834', lw=1.8, linestyle=(0, (4, 3)), zorder=5)
    colors_by_group = {group: PALETTE[i % len(PALETTE)] for i, group in enumerate(groups)}
    for r in rects:
        patch = patches.Rectangle((r['y'], r['x']), r['h'], r['w'],
                                  facecolor=colors_by_group.get(r['gruppo'], PALETTE[0]),
                                  edgecolor='white', linewidth=1.2, alpha=.94, zorder=3)
        ax.add_patch(patch)
        label = r['rid'].replace('x', '×')
        if r['h'] >= 55 and r['w'] >= 42:
            fontsize = 7.5 if r['h'] >= 95 and r['w'] >= 70 else 6.2
            annotation = ax.text(r['y'] + r['h']/2, r['x'] + r['w']/2, label,
                                 ha='center', va='center', fontsize=fontsize,
                                 fontweight='bold', color='#071e32', zorder=4,
                                 linespacing=1.2)
            annotation.set_clip_path(patch)
    # Cabina: rappresentazione indicativa esterna al pianale (non merce).
    ax.add_patch(patches.FancyBboxPatch((-66, truck_w*.22), 55, truck_w*.56,
                                         boxstyle='round,pad=0.02,rounding_size=8',
                                         facecolor='#002855', edgecolor='#002855', lw=1.0, zorder=2))
    ax.text(-39, truck_w/2, 'CABINA', color='white', fontsize=7,
            fontweight='bold', ha='center', va='center', rotation=90, zorder=3)
    ax.text(truck_l, -22, 'PORTELLONE', color='#002855', fontsize=8,
            fontweight='bold', ha='center', va='center')
    ax.set_xlim(-78, limit + max(55, limit*.045))
    ax.set_ylim(truck_w + 37, -42)
    # La geometria rimane in scala: eventuale spazio bianco serve a non deformare i pallet.
    ax.set_aspect('equal', adjustable='box')
    ax.set_yticks([])
    ax.spines[['left', 'right', 'top']].set_visible(False)
    ax.spines['bottom'].set_color('#d0deea')
    ticks = list(range(0, limit+1, 200))
    # Evita che etichette vicine (es. 13,6 m e 14 m) si sovrappongano.
    ticks = sorted({x for x in ticks if abs(x-truck_l) >= 100} | {truck_l})
    ax.set_xticks(ticks)
    ax.set_xticklabels([f'{x/100:g} m' for x in ticks], fontsize=8, color='#6a8195')
    ax.tick_params(axis='x', length=3, color='#bed0df', pad=6)
    fig.subplots_adjust(left=.01, right=.99, top=.96, bottom=.14)
    return fig


# 1 / Impostazioni rapide, senza alterare i widget e i loro callback.
opt_a, opt_b = st.columns(2, gap='medium')
with opt_a:
    with st.expander('▦  Dimensioni del camion', expanded=False):
        st.caption('Dimensioni utili · bilico predefinito: 240 × 1360 × 250 cm. L’altezza determina anche i livelli sovrapponibili.')
        dc1, dc2, dc3 = st.columns(3, gap='small')
        with dc1:
            camion_w = st.number_input('Larghezza (cm)', min_value=100, max_value=300, value=240, step=5,
                                       key='camion_w', on_change=invalidate_result)
        with dc2:
            camion_l = st.number_input('Lunghezza (cm)', min_value=200, max_value=3000, value=1360, step=10,
                                       key='camion_l', on_change=invalidate_result)
        with dc3:
            camion_h = st.number_input('Altezza (cm)', min_value=100, max_value=400, value=250, step=5,
                                       key='camion_h', on_change=invalidate_result)
with opt_b:
    with st.expander('↥  Importa elenco Excel / CSV', expanded=False):
        st.caption('Colonne richieste: Destinazione, Qta, L, W, H, Sovr · opzionale: Max_Liv. Sovr = si/1 oppure no/0.')
        uploaded_file = st.file_uploader('Carica file', type=['csv', 'xlsx'], label_visibility='collapsed')
        if uploaded_file is not None:
            if st.button('CARICA DATI', width='stretch'):
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df = pd.read_csv(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)
                    nuovi_dati = []
                    for index, row in df.iterrows():
                        g = str(row.get('Destinazione', f'SCARICO {index+1}')).strip().upper()
                        q = int(row.get('Qta', 1))
                        l = int(row.get('L', 120))
                        w = int(row.get('W', 80))
                        h = int(row.get('H', 150))
                        s_raw = str(row.get('Sovr', 'no')).strip().lower()
                        s = s_raw in ['si', 'sì', 'yes', 'true', '1']
                        max_liv_raw = row.get('Max_Liv', MAX_SOVR_LIVELLI_DEFAULT if s else 1)
                        max_liv = int(max_liv_raw) if not pd.isna(max_liv_raw) else (MAX_SOVR_LIVELLI_DEFAULT if s else 1)
                        if not s:
                            max_liv = 1
                        nuovi_dati.append((g, l, w, h, s, q, max_liv))
                    st.session_state.lista_di_carico = nuovi_dati
                    st.session_state.editing_index = None
                    st.session_state.last_result = None
                    st.session_state.val_g = get_next_scarico_name()
                    st.success(f'Importate {len(nuovi_dati)} righe. La lista precedente è stata sostituita.')
                    st.rerun()
                except Exception as e:
                    st.error(f'Errore nella lettura del file: controlla che le colonne siano corrette. Dettaglio: {e}')

# 2 / Inserimento, inventario vicino al form e dashboard affiancati.
col_form, col_result = st.columns([1, 1.25], gap='medium')
with col_form:
    with st.container(border=True):
        _section('01 / Merce', 'Inserimento colli', 'Aggiungi una tipologia di collo per volta, assegnandola allo scarico desiderato.')
        if st.session_state.editing_index is not None:
            g,l,w,h,s,q,max_liv = _normalize_item(st.session_state.lista_di_carico[st.session_state.editing_index])
            st.warning(f'MODIFICA IN CORSO · {g} · {q} pz · {l}×{w}×{h} cm · Sovr: {"Sì" if s else "No"}' + (f' (max {max_liv})' if s else ''))
        st.text_input('Destinazione / scarico', key='val_g')
        st.markdown('<div class="packer-help">Il primo scarico è il primo da consegnare: merce favorita verso il portellone.</div>', unsafe_allow_html=True)
        st.number_input('Quantità pallet', min_value=1, key='val_q', step=1)
        st.markdown('<div class="packer-smallhead">Dimensioni colli (cm)</div>', unsafe_allow_html=True)
        v2,v3,v4 = st.columns(3, gap='small')
        with v2:
            st.number_input('L (cm)', min_value=1, key='val_l', step=10)
        with v3:
            st.number_input('W (cm)', min_value=1, key='val_w', step=10)
        with v4:
            st.number_input('H (cm)', min_value=1, key='val_h', step=10)
        v_s, v_levels = st.columns([1,1], gap='small')
        with v_s:
            st.checkbox('Sovrapponibile', key='val_s', on_change=on_sovr_change)
        with v_levels:
            if st.session_state.val_s:
                st.number_input('Max livelli', min_value=1, max_value=10, key='val_max_sovr', step=1,
                                help='Livelli massimi per questa riga.')
        if st.session_state.editing_index is None:
            st.button('＋  AGGIUNGI COLLI', on_click=aggiungi_voce, type='primary', width='stretch')
        else:
            b1,b2=st.columns([2,1],gap='small')
            with b1:
                st.button('SALVA MODIFICA', on_click=aggiungi_voce, type='primary', width='stretch')
            with b2:
                st.button('ANNULLA', on_click=annulla_modifica, width='stretch')

    with st.container(border=True):
        total_rows = len(st.session_state.lista_di_carico)
        _section('02 / Inventario', f'Colli inseriti · {total_rows} righe',
                 'Subito sotto l’inserimento: modifica o elimina i pallet senza scorrere a fondo pagina.')
        if st.session_state.lista_di_carico:
            gruppi_vista = OrderedDict()
            for i,item in enumerate(st.session_state.lista_di_carico):
                gruppi_vista.setdefault(item[0], []).append((i,item))
            for idx,(g,items_gruppo) in enumerate(gruppi_vista.items()):
                with st.expander(f'{g}   ·   {sum(_normalize_item(item)[5] for _,item in items_gruppo)} colli   ·   {len(items_gruppo)} righe', expanded=True):
                    for i,item in items_gruppo:
                        _,l,w,h,s,q,max_liv = _normalize_item(item)
                        col_desc,col_edit,col_del = st.columns([6,1,1], gap='small', vertical_alignment='center')
                        with col_desc:
                            suffix = f'Sovr. · max {max_liv} livelli' if s else 'Non sovrapponibile'
                            selected = ' · IN MODIFICA' if st.session_state.editing_index == i else ''
                            st.markdown(f'<div class="packer-row"><b>{q} pz</b> · {l} × {w} × {h} cm · '
                                        f'{html_escape(suffix)}{selected}</div>', unsafe_allow_html=True)
                        with col_edit:
                            st.button('✎', key=f'ed_{i}', on_click=edita_riga, args=(i,), width='stretch', help='Modifica questa riga')
                        with col_del:
                            st.button('×', key=f'del_{i}', on_click=elimina_riga, args=(i,), width='stretch', help='Elimina questa riga')
            if len(st.session_state.lista_di_carico) > 11:
                st.warning('Hai inserito molti lotti. La tabella nel PDF potrebbe essere tagliata.')
            st.markdown('---')
            _,clear_col = st.columns([4,1])
            with clear_col:
                if st.button('SVUOTA TUTTO', width='stretch'):
                    st.session_state.lista_di_carico.clear()
                    st.session_state.editing_index = None
                    st.session_state.last_result = None
                    st.session_state.val_g = 'SCARICO 1'
                    st.rerun()
        else:
            st.caption('Nessun collo inserito. Usa il modulo in alto o importa un file Excel / CSV.')

    with st.container(border=True):
        _section('03 / Elaborazione', 'Ottimizzazione')
        allow_rotation = st.checkbox(
            'Consenti rotazione 90° se riduce i metri lineari', value=True,
            key='allow_rotation', on_change=invalidate_result,
            help='Motore Planner beta 5: prova orientamenti a 0° e 90° e confronta anche il risultato senza rotazione. Ricerca euristica, non ottimo matematico garantito.',
        )
        esegui = st.button('OTTIMIZZA PIANALE  →', type='primary', width='stretch')
        st.caption(f'{len(st.session_state.lista_di_carico)} righe inserite · '
                   f'{sum(_normalize_item(i)[5] for i in st.session_state.lista_di_carico)} colli · '
                   f'{len(OrderedDict.fromkeys(_normalize_item(i)[0] for i in st.session_state.lista_di_carico))} scarichi')

# Calcolo invariato rispetto alla beta 5 (compreso confronto rotazione).
if esegui and st.session_state.lista_di_carico:
    try:
        rects_to_draw, max_L = calcola_posizionamento(
            st.session_state.lista_di_carico, allow_rotation, camion_w, camion_l, camion_h,
        )
        baseline_no_rotation = None
        if allow_rotation:
            try:
                _baseline_rects, baseline_no_rotation = calcola_posizionamento(
                    st.session_state.lista_di_carico, False, camion_w, camion_l, camion_h,
                )
            except ValueError:
                baseline_no_rotation = None
        st.session_state.last_result = {
            'rects': rects_to_draw, 'max_L': max_L, 'camion_w': camion_w,
            'camion_l': camion_l, 'camion_h': camion_h,
            'allow_rotation': allow_rotation, 'baseline_no_rotation': baseline_no_rotation,
        }
    except ValueError as e:
        st.session_state.last_result = {'error': str(e)}

result = st.session_state.last_result
ordine_gruppi = list(OrderedDict.fromkeys(_normalize_item(item)[0] for item in st.session_state.lista_di_carico))
group_colors = {g: PALETTE[i % len(PALETTE)] for i,g in enumerate(ordine_gruppi)}

with col_result:
    with st.container(border=True):
        _section('04 / Risultati', 'Riepilogo del carico', 'Ingombri e disponibilità del pianale, calcolati dal motore Planner beta 5.')
        if result and 'error' in result:
            st.error(f"⛔ {result['error']}")
        elif result:
            rects_to_draw = result['rects']
            max_L = result['max_L']
            result_camion_w = result['camion_w']
            result_camion_l = result['camion_l']
            overflow = max_L > result_camion_l
            ingombro_m = max_L / 100
            limite_m = result_camion_l / 100
            eccedenza_m = max(0, max_L - result_camion_l)/100
            percent = 100 * max_L/result_camion_l
            state = 'warning' if overflow else 'good'
            st.markdown(
                f'<div class="packer-kpi {state}">'
                '<div class="packer-kpi-title">Ingombro totale stimato</div>'
                f'<div class="packer-kpi-number">{_it_m(ingombro_m)} <span style="font-size:17px;letter-spacing:0">m</span></div>'
                f'<div class="packer-kpi-note">Disponibili: {_it_m(limite_m)} m · '
                f'{"Eccedenza: +" + _it_m(eccedenza_m) + " m" if overflow else "Residuo: " + _it_m((result_camion_l-max_L)/100) + " m"}'
                '</div></div>'
                f'<div class="packer-status {"warn" if overflow else ""}">'
                f'{"● Il carico supera il pianale" if overflow else "● Il carico rientra nel pianale"}</div>'
                '<div class="packer-track">'
                f'<div class="packer-track-fill {"warn" if overflow else ""}" style="width:{min(100,percent):.2f}%"></div></div>'
                f'<div class="packer-track-annotation"><span>{percent:.0f}% utilizzato</span>'
                f'<span>{_it_m(limite_m)} m disponibili</span></div>',
                unsafe_allow_html=True,
            )
            if overflow:
                st.caption(f'Il piano mostra anche i colli oltre il portellone: eccedenza reale stimata di {_it_m(eccedenza_m)} m.')
            if result.get('allow_rotation'):
                baseline_no_rotation = result.get('baseline_no_rotation')
                if baseline_no_rotation is None:
                    st.caption('Rotazione necessaria: almeno un collo non entra nell’orientamento originale.')
                else:
                    risparmio_cm = baseline_no_rotation - max_L
                    if risparmio_cm >= 1:
                        st.success(f'Rotazione utile · senza: {_it_m(baseline_no_rotation/100)} m → '
                                   f'con: {_it_m(max_L/100)} m · risparmio {_it_m(risparmio_cm/100)} m.')
                    else:
                        st.caption(f'Rotazione consentita, ma non riduce l’ingombro ({_it_m(baseline_no_rotation/100)} m).')
            ingombro_per_gruppo = _ingombro_per_gruppo(rects_to_draw, ordine_gruppi=ordine_gruppi)
            if ingombro_per_gruppo:
                st.markdown('<div class="packer-smallhead">Ingombro longitudinale per scarico</div>', unsafe_allow_html=True)
                pills = ''.join(
                    '<span class="packer-pill">'
                    f'<span class="packer-dot" style="background:{group_colors.get(g, PALETTE[0])}"></span>'
                    f'{html_escape(str(g))}<b>{_it_m(m)} m</b></span>'
                    for g,m in ingombro_per_gruppo.items()
                )
                st.markdown(f'<div class="packer-pill-set">{pills}</div>', unsafe_allow_html=True)
                st.caption('Per ogni scarico si sommano le fasce longitudinali occupate, senza includere i vuoti tra segmenti.')
            if not overflow:
                pdf_file = genera_pdf_reportlab(
                    rects_to_draw, st.session_state.lista_di_carico, max_L,
                    result_camion_w, result_camion_l, ingombro_per_gruppo=ingombro_per_gruppo,
                )
                st.download_button('↓  SCARICA REPORT PDF', data=pdf_file,
                                   file_name='Report_Carico_Vicenza.pdf', mime='application/pdf', width='stretch')
            else:
                st.caption('PDF operativo disabilitato: la lunghezza utile del mezzo è stata superata.')
        else:
            st.markdown('<div class="packer-empty"><b>Nessun piano calcolato</b>'
                        'Aggiungi i colli e premi OTTIMIZZA PIANALE per visualizzare ingombri, rotazione e scarichi.'
                        '</div>', unsafe_allow_html=True)

# 5 / Pianale orizzontale a tutta larghezza, nessuna modifica al risultato numerico.
with st.container(border=True):
    _section('05 / Visualizzazione', 'Piano di carico', 'Vista dall’alto · cabina a sinistra, portellone a destra · geometria in scala.')
    if result and 'error' not in result:
        fig = _draw_load_plan(result['rects'], result['camion_w'], result['camion_l'], result['max_L'], ordine_gruppi)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
        if ordine_gruppi:
            legend = ''.join(
                '<span class="packer-pill">'
                f'<span class="packer-dot" style="background:{group_colors[g]}"></span>'
                f'{html_escape(str(g))}</span>'
                for g in ordine_gruppi
            )
            st.markdown(f'<div class="packer-pill-set">{legend}</div>', unsafe_allow_html=True)
        st.markdown('<div class="packer-help">Le etichette dei colli molto piccoli possono essere omesse nella vista: misure e quantità restano nell’elenco e nel PDF.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="packer-empty"><b>Il disegno del pianale apparirà qui</b>'
                    'La visualizzazione si aggiorna dopo il calcolo e segnala graficamente eventuali eccedenze.'
                    '</div>', unsafe_allow_html=True)

