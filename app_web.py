
import io
from datetime import datetime
from collections import OrderedDict

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

# --- COSTANTI DI CONFIGURAZIONE ---
PALETTE = ['#3498db', '#e67e22', '#2ecc71', '#9b59b6', '#f1c40f', '#e74c3c', '#1abc9c', '#34495e', '#d35400', '#7f8c8d']
MAX_SOVR_LIVELLI_DEFAULT = 2

# --- CONFIGURAZIONE PAGINA WEB ---
st.set_page_config(page_title="DACHSER Packer - Vicenza", page_icon="🚛", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f4f5f7; color: #333333; }
    h1, h2, h3, h4 { color: #00386A !important; font-weight: 800; }
    .stButton > button { background-color: white !important; color: #00386A !important; border: 1px solid #00386A !important; font-weight: bold; }
    .stButton button[kind="primary"] { background-color: #FFD100 !important; color: #00386A !important; border: 2px solid #00386A !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div style="background-color:#FFD100; padding:20px; border-radius:10px; text-align:center; margin-bottom:25px; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">
        <div style="color:#00386A !important; font-size: 3.5rem; font-weight: 900; letter-spacing: 2px; margin:0; line-height: 1.2;">DACHSER</div>
        <div style="color:#00386A !important; font-size: 1.5rem; font-weight: 300; letter-spacing: 1px; margin:0; line-height: 1.2;">Intelligent Logistics</div>
        <hr style="border-top: 2px solid #00386A; width: 30%; margin: 15px auto;">
        <div style="color:#00386A !important; font-size: 1.1rem; font-weight: 400; margin:0;">Ottimizzatore Carico Pianale Multi-Drop &bull; <b style="color:#00386A !important;">Filiale di Vicenza</b></div>
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
# --- LAYOUT E INTERFACCIA UTENTE ---
# ==========================================

col_sx, col_dx = st.columns([1.2, 1], gap="large")

with col_sx:
    # --- SEZIONE IMPOSTAZIONI CAMION ---
    with st.expander("🚛 Dimensioni Camion", expanded=False):
        st.markdown(
            "<small>Modifica le dimensioni utili. Default bilico: 240 × 1360 × 250 cm. "
            "L'altezza viene usata anche per calcolare i livelli sovrapponibili.</small>",
            unsafe_allow_html=True,
        )
        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            camion_w = st.number_input(
                "Larghezza (cm)", min_value=100, max_value=300, value=240, step=5,
                key="camion_w", on_change=invalidate_result
            )
        with dc2:
            camion_l = st.number_input(
                "Lunghezza (cm)", min_value=200, max_value=3000, value=1360, step=10,
                key="camion_l", on_change=invalidate_result
            )
        with dc3:
            camion_h = st.number_input(
                "Altezza (cm)", min_value=100, max_value=400, value=250, step=5,
                key="camion_h", on_change=invalidate_result
            )

    # --- SEZIONE IMPORTAZIONE EXCEL / CSV ---
    with st.expander("📁 Importa lista da Excel o CSV"):
        st.markdown("""
        <small>Il file deve contenere le colonne: <b>Destinazione, Qta, L, W, H, Sovr</b> (opzionale: <b>Max_Liv</b>).<br><br>
        💡 <b>Sovr:</b> 'si' o '1' se è sovrapponibile, 'no' o '0' se non lo è.<br>
        💡 <b>Max_Liv:</b> Livelli massimi consentiti per l'impilaggio (se vuoto, usa il default).</small>
        """, unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Carica file", type=["csv", "xlsx"], label_visibility="collapsed")
        
        if uploaded_file is not None:
            if st.button("📥 CARICA DATI", width="stretch"):
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

                    # L'importazione sostituisce la lista corrente: premendo due volte non duplica i dati.
                    st.session_state.lista_di_carico = nuovi_dati
                    st.session_state.editing_index = None
                    st.session_state.last_result = None
                    st.session_state.val_g = get_next_scarico_name()
                    st.success(f"Importate {len(nuovi_dati)} righe. La lista precedente è stata sostituita.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore nella lettura del file: controlla che le colonne siano corrette. Dettaglio: {e}")

    st.markdown("#### 📥 Inserimento Manuale")

    if st.session_state.editing_index is not None:
        g, l, w, h, s, q, max_liv = _normalize_item(
            st.session_state.lista_di_carico[st.session_state.editing_index]
        )
        st.warning(
            f"🟡 **MODIFICA IN CORSO** — stai modificando: {g} | {q} pz | {l}×{w}×{h} cm | "
            f"Sovr: {'Sì' if s else 'No'}{f' (max {max_liv})' if s else ''}"
        )
    
    st.text_input("📍 Destinazione (Scarico)", key="val_g")
    st.caption("Ordine multi-drop: il primo scarico inserito è il primo da consegnare e viene quindi favorito verso il portellone.")
    
    c1, c2, c3, c4, c5, c6 = st.columns([1.2, 1.2, 1.2, 1.2, 0.8, 1.0])
    with c1:
        st.number_input("📦 Q.tà", min_value=1, key="val_q", step=1)
    with c2:
        st.number_input("L (cm)", min_value=1, key="val_l", step=10)
    with c3:
        st.number_input("W (cm)", min_value=1, key="val_w", step=10)
    with c4:
        st.number_input("H (cm)", min_value=1, key="val_h", step=10)
    with c5:
        st.write("")
        st.checkbox("Sovr.", key="val_s", on_change=on_sovr_change)
    with c6:
        if st.session_state.val_s:
            st.number_input("Max liv.", min_value=1, max_value=10, key="val_max_sovr", step=1, help="Livelli massimi per questa riga.")
    
    if st.session_state.editing_index is None:
        st.button("➕ AGGIUNGI", on_click=aggiungi_voce, width="stretch")
    else:
        b1, b2 = st.columns([2, 1])
        with b1:
            st.button("✅ SALVA MODIFICA", on_click=aggiungi_voce, type="primary", width="stretch")
        with b2:
            st.button("✖️ ANNULLA", on_click=annulla_modifica, width="stretch")

    if st.session_state.lista_di_carico:
        st.markdown("---")
        
        gruppi_vista = OrderedDict()
        for i, item in enumerate(st.session_state.lista_di_carico):
            gruppi_vista.setdefault(item[0], []).append((i, item))
            
        for g, items_gruppo in gruppi_vista.items():
            st.markdown(f"<h6 style='color:#00386A; margin-top: 15px; margin-bottom: 5px; font-weight:bold;'>📍 {g}</h6>", unsafe_allow_html=True)
            for i, item in items_gruppo:
                _, l, w, h, s, q, max_liv = _normalize_item(item)
                cs1, cs2, cs3 = st.columns([8, 1, 1])
                with cs1:
                    if st.session_state.editing_index == i:
                        st.warning(f"🟡 IN MODIFICA — {q} pz | {l} x {w} x {h} cm | Sovr: {'Sì' if s else 'No'}{f' (max {max_liv})' if s else ''}")
                    else:
                        st.info(f"{q} pz | {l} x {w} x {h} cm | Sovr: {'Sì' if s else 'No'}{f' (max {max_liv})' if s else ''}")
                with cs2: st.button("✏️", key=f"ed_{i}", on_click=edita_riga, args=(i,))
                with cs3: st.button("❌", key=f"del_{i}", on_click=elimina_riga, args=(i,))
        
        if len(st.session_state.lista_di_carico) > 11:
            st.warning("⚠️ Hai inserito molti lotti. La tabella nel PDF potrebbe essere tagliata.")
        if st.button("🗑️ Svuota Tutto"):
            st.session_state.lista_di_carico.clear()
            st.session_state.editing_index = None
            st.session_state.last_result = None
            st.session_state.val_g = "SCARICO 1"
            st.rerun()

    allow_rotation = st.checkbox(
        "🔄 Consenti rotazione 90° se riduce i metri lineari",
        value=True,
        key="allow_rotation",
        on_change=invalidate_result,
        help="Motore Planner beta 5: prova orientamenti a 0° e 90° e confronta anche il risultato senza rotazione. Ricerca euristica, non ottimo matematico garantito.",
    )
    esegui = st.button("⚡ OTTIMIZZA PIANALE", type="primary", width="stretch")

with col_dx:
    st.markdown("#### 📊 Risultato · motore Planner 1.0 beta 5")

    if esegui and st.session_state.lista_di_carico:
        try:
            rects_to_draw, max_L = calcola_posizionamento(
                st.session_state.lista_di_carico,
                allow_rotation,
                camion_w,
                camion_l,
                camion_h,
            )

            baseline_no_rotation = None
            if allow_rotation:
                try:
                    _baseline_rects, baseline_no_rotation = calcola_posizionamento(
                        st.session_state.lista_di_carico,
                        False,
                        camion_w,
                        camion_l,
                        camion_h,
                    )
                except ValueError:
                    # Alcuni colli possono entrare solo se ruotati.
                    baseline_no_rotation = None

            st.session_state.last_result = {
                "rects": rects_to_draw,
                "max_L": max_L,
                "camion_w": camion_w,
                "camion_l": camion_l,
                "camion_h": camion_h,
                "allow_rotation": allow_rotation,
                "baseline_no_rotation": baseline_no_rotation,
            }
        except ValueError as e:
            st.session_state.last_result = {"error": str(e)}

    result = st.session_state.last_result

    if result and "error" in result:
        st.error(f"⛔ {result['error']}")

    elif result:
        rects_to_draw = result["rects"]
        max_L = result["max_L"]
        result_camion_w = result["camion_w"]
        result_camion_l = result["camion_l"]
        result_camion_h = result["camion_h"]

        overflow = max_L > result_camion_l
        ingombro_m = max_L / 100
        limite_m = result_camion_l / 100
        eccedenza_m = max(0, max_L - result_camion_l) / 100

        if overflow:
            card_bg = "#ffe6e6"
            card_border = "#e74c3c"
            card_text = f"⛔ Servono {ingombro_m:.2f} m (limite mezzo {limite_m:.2f} m)"
            card_sub = f"Eccedenza reale stimata: {eccedenza_m:.2f} m. Il piano viene mostrato anche oltre il portellone."
        else:
            card_bg = "#e8ffe6"
            card_border = "#2ecc71"
            card_text = f"✅ Ingombro Totale: {ingombro_m:.2f} m su {limite_m:.2f} m disponibili"
            card_sub = "Il carico rientra nel pianale (stima euristica verificata)."

        st.markdown(
            f"""
            <div style="
                padding: 14px 18px;
                margin-bottom: 10px;
                border-radius: 10px;
                border: 2px solid {card_border};
                background-color: {card_bg};
            ">
                <div style="font-size: 1.6rem; font-weight: 900; color: #00386A; margin-bottom: 4px;">
                    {card_text}
                </div>
                <div style="font-size: 0.9rem; color: #333333;">
                    {card_sub}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if result.get("allow_rotation"):
            baseline_no_rotation = result.get("baseline_no_rotation")
            if baseline_no_rotation is None:
                st.caption("🔄 Rotazione necessaria: almeno un collo non è caricabile nell'orientamento originale.")
            else:
                risparmio_cm = baseline_no_rotation - max_L
                if risparmio_cm >= 1:
                    st.success(
                        f"🔄 Rotazione utile: senza rotazione {baseline_no_rotation/100:.2f} m → "
                        f"con rotazione {max_L/100:.2f} m. Risparmio: {risparmio_cm/100:.2f} m."
                    )
                else:
                    st.caption(
                        f"🔄 Rotazione consentita, ma per questo carico non riduce l'ingombro "
                        f"({baseline_no_rotation/100:.2f} m in entrambi i casi)."
                    )

        ordine_gruppi = list(
            OrderedDict.fromkeys([_normalize_item(item)[0] for item in st.session_state.lista_di_carico])
        )
        ingombro_per_gruppo = _ingombro_per_gruppo(rects_to_draw, ordine_gruppi=ordine_gruppi)
        if ingombro_per_gruppo:
            if len(ingombro_per_gruppo) > 1:
                st.markdown("**📐 Ingombro longitudinale per scarico:**")
                cols = st.columns(len(ingombro_per_gruppo))
                for idx, (g, m) in enumerate(ingombro_per_gruppo.items()):
                    with cols[idx]:
                        st.metric(g, f"{m:.2f} m")
                st.caption(
                    f"Totale mezzo: **{ingombro_m:.2f} m** · per ogni scarico vengono sommate solo le fasce "
                    "longitudinali effettivamente occupate, senza contare eventuali vuoti tra segmenti."
                )
            else:
                g, m = next(iter(ingombro_per_gruppo.items()))
                st.caption(f"📐 {g}: **{m:.2f} m** (totale mezzo: **{ingombro_m:.2f} m**)")

        total_h = max(result_camion_l, max_L) + 90
        fig_height = min(11.5, max(4.5, 1.2 * (total_h / result_camion_w)))
        fig_s, ax_s = plt.subplots(figsize=(2.2, fig_height))
        ax_s.set_aspect('equal')
        ax_s.set_xlim(0, result_camion_w)
        ax_s.set_ylim(total_h, -50)
        ax_s.add_patch(
            patches.Rectangle(
                (0, 0), result_camion_w, result_camion_l,
                fill=False, edgecolor='#00386A', lw=2
            )
        )
        ax_s.text(
            result_camion_w / 2, -25, "CABINA",
            ha='center', fontweight='bold', color='#00386A', fontsize=6
        )
        ax_s.text(
            result_camion_w / 2, result_camion_l + 22, "PORTELLONE",
            ha='center', va='center', fontweight='bold', color='#00386A', fontsize=6
        )
        if overflow:
            ax_s.axhline(result_camion_l, linestyle='--', linewidth=1)

        gruppi_u = ordine_gruppi
        mappa_c = {g: PALETTE[i % len(PALETTE)] for i, g in enumerate(gruppi_u)}
        for r in rects_to_draw:
            ax_s.add_patch(
                patches.Rectangle(
                    (r['x'], r['y']), r['w'], r['h'],
                    facecolor=mappa_c[r['gruppo']], edgecolor='black', alpha=0.8, lw=0.5
                )
            )
            ax_s.text(
                r['x'] + r['w'] / 2,
                r['y'] + r['h'] / 2,
                r['rid'],
                ha='center', va='center', fontsize=4, fontweight='bold'
            )
        ax_s.axis('off')

        if not overflow:
            pdf_file = genera_pdf_reportlab(
                rects_to_draw,
                st.session_state.lista_di_carico,
                max_L,
                result_camion_w,
                result_camion_l,
                ingombro_per_gruppo=ingombro_per_gruppo,
            )
            st.download_button(
                label="📄 SCARICA REPORT PDF",
                data=pdf_file,
                file_name="Report_Carico_Vicenza.pdf",
                mime="application/pdf",
                width="stretch",
            )
        else:
            st.caption("Il PDF operativo resta disabilitato quando il carico supera la lunghezza utile del mezzo.")

        st.markdown("---")
        _, col_m, _ = st.columns([1, 2.4, 1])
        with col_m:
            st.pyplot(fig_s, use_container_width=True)
        plt.close(fig_s)

    elif not st.session_state.lista_di_carico:
        st.info("💡 Aggiungi i bancali a sinistra o importa un file per visualizzare il piano di carico.")
    else:
        st.info("Premi **OTTIMIZZA PIANALE** per calcolare il carico.")
