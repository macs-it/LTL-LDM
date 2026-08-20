import io
import math
from datetime import datetime
from collections import OrderedDict

import streamlit as st
import pandas as pd
from rectpack import newPacker, SORT_NONE
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
:root {
  --d-blue: #00386A;
  --d-blue-2: #005B94;
  --d-yellow: #FFD100;
  --bg: #F3F5F7;
  --card: #FFFFFF;
  --line: #DDE3E8;
  --text: #1F2937;
  --muted: #6B7280;
}
.stApp { background: var(--bg); color: var(--text); }
.block-container { max-width: 1500px; padding-top: 1.2rem; padding-bottom: 2rem; }
h1, h2, h3, h4, h5, h6 { color: var(--d-blue) !important; }
.topbar { display:flex; justify-content:space-between; align-items:center; background:var(--d-blue); padding:18px 24px; border-radius:14px; margin-bottom:16px; box-shadow:0 6px 20px rgba(0,56,106,.12); }
.brand { color:var(--d-yellow); font-size:2.3rem; line-height:1; font-weight:900; letter-spacing:1px; }
.brand-sub { color:#fff; font-size:.82rem; font-weight:700; letter-spacing:1.5px; margin-top:7px; opacity:.95; }
.module-block { text-align:right; }
.module-label { color:#fff; font-size:1.2rem; font-weight:800; letter-spacing:1.3px; }
.module-sub { color:#DCE8F0; font-size:.8rem; margin-top:4px; }
.section-spacer { height:10px; }
.status-card { display:flex; justify-content:space-between; align-items:center; padding:18px 20px; border-radius:12px; border:1px solid var(--line); margin-bottom:12px; }
.status-card.success { background:#F0FAF2; border-left:5px solid #2E7D32; }
.status-card.danger { background:#FFF2F2; border-left:5px solid #C62828; }
.status-kicker { font-size:.68rem; text-transform:uppercase; letter-spacing:1.3px; color:var(--muted); font-weight:800; }
.status-title { font-size:1.4rem; font-weight:900; color:var(--d-blue); margin-top:2px; }
.status-sub { font-size:.82rem; color:var(--muted); margin-top:2px; }
.status-value { font-size:2.15rem; font-weight:900; color:var(--d-blue); }
.status-value span { font-size:.9rem; font-weight:700; }
.stop-title { display:flex; align-items:center; gap:8px; font-size:1rem; color:var(--d-blue); }
.stop-dot, .legend-dot { display:inline-block; width:10px; height:10px; border-radius:50%; }
.legend-item { display:inline-flex; align-items:center; gap:5px; margin-right:14px; font-size:.8rem; color:#374151; }
.empty-result { min-height:420px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; background:#fff; border:1px dashed #C7D0D8; border-radius:14px; padding:42px; }
.empty-icon { width:58px; height:58px; border-radius:50%; background:#FFF7C7; display:flex; align-items:center; justify-content:center; color:var(--d-blue); font-size:28px; font-weight:900; margin-bottom:14px; }
.empty-title { color:var(--d-blue); font-size:1.25rem; font-weight:800; }
.empty-sub { color:var(--muted); max-width:420px; margin-top:6px; font-size:.9rem; line-height:1.5; }
.stButton > button { border-radius:9px !important; min-height:40px; font-weight:750 !important; border:1px solid #C9D2DA !important; }
.stButton button[kind="primary"] { background:var(--d-yellow) !important; color:var(--d-blue) !important; border:1px solid #E3B900 !important; }
[data-testid="stMetricValue"] { color:var(--d-blue); }
[data-testid="stMetricLabel"] { color:#66727D; }
</style>
""", unsafe_allow_html=True)



# --- GESTIONE STATO ---
if 'lista_di_carico' not in st.session_state:
    st.session_state.lista_di_carico = []
if 'editing_index' not in st.session_state:
    st.session_state.editing_index = None
if 'last_result' not in st.session_state:
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
    st.session_state.last_result = None

def elimina_riga(index):
    st.session_state.lista_di_carico.pop(index)
    st.session_state.last_result = None
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

# --- FUNZIONE LOGICA DI CALCOLO (IL "CERVELLO") ---
def calcola_posizionamento(lista_di_carico, allow_rotation, camion_w, camion_l):
    def tiers_per_item(h, sovrapponibile, max_livello_riga):
        if not sovrapponibile:
            return 1
        return min(max_livello_riga, max(1, 250 // max(1, h)))

    # Caso speciale: rotazione libera + un solo tipo di pallet (stesso gruppo e stesse misure).
    if allow_rotation and lista_di_carico:
        normalized = [_normalize_item(item) for item in lista_di_carico]
        keys = {(g, l, w, h, s, max_liv) for (g, l, w, h, s, q, max_liv) in normalized}
        if len(keys) == 1:
            g, l, w, h, s, max_liv = next(iter(keys))
            total_q = sum(q for (_g, _l, _w, _h, _s, q, _max_liv) in normalized)
            
            # --- BUG FIX: calcoliamo quanti livelli fare e quante "impronte a terra" ci servono ---
            tiers = tiers_per_item(h, s, max_liv)
            footprints_needed = math.ceil(total_q / tiers)

            best = None
            for pallet_w, pallet_l in [(w, l), (l, w)]:
                if pallet_w > camion_w:
                    continue
                per_row = camion_w // pallet_w
                if per_row <= 0:
                    continue
                # Dividiamo le impronte a terra per i bancali per fila
                rows = math.ceil(footprints_needed / per_row)
                used_L = rows * pallet_l
                if best is None or used_L < best["used_L"]:
                    best = {
                        "pallet_w": pallet_w,
                        "pallet_l": pallet_l,
                        "per_row": per_row,
                        "rows": rows,
                        "used_L": used_L,
                    }

            if best is not None:
                rects = []
                remaining = total_q
                for row in range(best["rows"]):
                    for col in range(best["per_row"]):
                        if remaining <= 0:
                            break
                        x = col * best["pallet_w"]
                        y = row * best["pallet_l"]
                        
                        # --- BUG FIX: calcoliamo quanti pezzi impilare su questa singola cella ---
                        pezzi_qui = min(remaining, tiers)
                        label = f"{l}x{w}\nX{pezzi_qui}" if pezzi_qui > 1 else f"{l}x{w}"
                        
                        rects.append(
                            {
                                "x": x,
                                "y": y,
                                "w": best["pallet_w"],
                                "h": best["pallet_l"],
                                "rid": label,
                                "gruppo": g,
                            }
                        )
                        remaining -= pezzi_qui
                    if remaining <= 0:
                        break

                return rects, best["used_L"]

    if not allow_rotation:
        rects = []
        for item in lista_di_carico:
            g, l, w, h, s, q, max_liv = _normalize_item(item)
            if w > camion_w:
                raise ValueError(
                    f"Impossibile posizionare il collo {l}x{w} cm di '{g}' senza rotazione: "
                    f"larghezza collo ({w} cm) superiore alla larghezza utile ({camion_w} cm)."
                )
            tiers = tiers_per_item(h, s, max_liv)
            pezzi_rimanenti = q

            for _ in range(math.ceil(q / tiers)):
                pezzi_qui = min(pezzi_rimanenti, tiers)
                pezzi_rimanenti -= pezzi_qui

                label = f"{l}x{w}\nX{pezzi_qui}" if pezzi_qui > 1 else f"{l}x{w}"

                best_y = float("inf")
                best_x = 0
                xs = sorted(list(set([0] + [r["x"] + r["w"] for r in rects if r["x"] + r["w"] + w <= camion_w])))
                for x in xs:
                    max_y = 0
                    for r in rects:
                        if x < r["x"] + r["w"] and x + w > r["x"]:
                            max_y = max(max_y, r["y"] + r["h"])
                    if max_y < best_y:
                        best_y, best_x = max_y, x

                rects.append({"x": best_x, "y": best_y, "w": w, "h": l, "rid": label, "gruppo": g})

        max_L = max([r["y"] + r["h"] for r in rects]) if rects else 0
        return rects, max_L

    def build_group_rects(items, group_idx, rid_start):
        rect_reqs = []
        next_rid = rid_start
        for item in items:
            g, l, w, h, s, q, max_liv = _normalize_item(item)
            tiers = tiers_per_item(h, s, max_liv)
            pezzi_rimanenti = q
            for _ in range(math.ceil(q / tiers)):
                pezzi_qui = min(pezzi_rimanenti, tiers)
                label = f"{l}x{w}\nX{pezzi_qui}" if pezzi_qui > 1 else f"{l}x{w}"
                pezzi_rimanenti -= pezzi_qui
                rect_reqs.append(
                    {
                        "w": w,
                        "l": l,
                        "rid": next_rid,
                        "gruppo": g,
                        "group_idx": group_idx,
                        "label": label,
                    }
                )
                next_rid += 1
        return rect_reqs, next_rid

    def candidate_orders(grouped_rect_reqs):
        def concat(groups):
            merged = []
            for group in groups:
                merged.extend(group)
            return merged

        base = [list(group) for group in grouped_rect_reqs]
        yield concat(base)

        keys = [
            lambda r: r["w"] * r["l"],
            lambda r: max(r["w"], r["l"]),
            lambda r: min(r["w"], r["l"]),
            lambda r: (r["w"] + r["l"]),
        ]
        for key in keys:
            yield concat([sorted(list(group), key=key, reverse=True) for group in grouped_rect_reqs])

    def score_layout(placed, meta_by_rid):
        if not placed:
            return 0, 0

        used_length = max((y + h) for (_b, _x, y, _w, h, _rid) in placed)
        group_stats = OrderedDict()
        for (_b, _x, y, _w, h, rid) in placed:
            meta = meta_by_rid[rid]
            idx = meta["group_idx"]
            if idx not in group_stats:
                group_stats[idx] = {"min_y": y, "max_y_end": y + h, "intervals": [(y, y + h)]}
            else:
                group_stats[idx]["min_y"] = min(group_stats[idx]["min_y"], y)
                group_stats[idx]["max_y_end"] = max(group_stats[idx]["max_y_end"], y + h)
                group_stats[idx]["intervals"].append((y, y + h))

        overlap_cm = 0
        inversion_cm = 0
        max_prev_end = -1
        max_prev_start = -1
        for idx in sorted(group_stats.keys()):
            current_min = group_stats[idx]["min_y"]
            current_max = group_stats[idx]["max_y_end"]
            if max_prev_end >= 0:
                overlap_cm += max(0, max_prev_end - current_min)
                inversion_cm += max(0, max_prev_start - current_min)
            max_prev_end = max(max_prev_end, current_max)
            max_prev_start = max(max_prev_start, current_min)

        extra_segments = 0
        for stats in group_stats.values():
            intervals = sorted(stats["intervals"], key=lambda it: it[0])
            if not intervals:
                continue
            segments = 1
            current_end = intervals[0][1]
            for start, end in intervals[1:]:
                if start <= current_end:
                    current_end = max(current_end, end)
                else:
                    segments += 1
                    current_end = end
            extra_segments += max(0, segments - 1)

        score = used_length + (overlap_cm * 1000) + (inversion_cm * 1200) + (extra_segments * 250)
        return score, used_length

    def pack_in_bin(grouped_rect_reqs, bin_w, bin_l):
        best = None
        meta_by_rid = {r["rid"]: r for group in grouped_rect_reqs for r in group}
        for ordered in candidate_orders(grouped_rect_reqs):
            p = newPacker(rotation=True, sort_algo=SORT_NONE)
            p.add_bin(bin_w, bin_l)
            for r in ordered:
                p.add_rect(r["w"], r["l"], rid=r["rid"])
            p.pack()
            placed = p.rect_list()
            if len(placed) != len(meta_by_rid):
                continue
            score, used_length = score_layout(placed, meta_by_rid)
            if best is None or score < best["score"] or (score == best["score"] and used_length < best["used_length"]):
                best = {"placed": placed, "used_length": used_length, "score": score}
        if best is None:
            raise ValueError(
                f"Impossibile posizionare tutti i colli nel pianale {bin_w}x{bin_l}cm "
                "(verifica dimensioni e che nessun lato superi la larghezza)."
            )
        return best["placed"], best["used_length"], meta_by_rid

    gruppi = OrderedDict()
    for item in lista_di_carico:
        g, *_rest = _normalize_item(item)
        gruppi.setdefault(g, []).append(item)

    grouped_rect_reqs = []
    next_rid = 0
    for group_idx, (_g, items) in enumerate(gruppi.items()):
        rects_group, next_rid = build_group_rects(items, group_idx, next_rid)
        grouped_rect_reqs.append(rects_group)

    placed, max_L, meta_by_rid = pack_in_bin(grouped_rect_reqs, camion_w, camion_l)

    rects = []
    for (_b, x, y, w, h, rid) in placed:
        meta = meta_by_rid[rid]
        rects.append({"x": x, "y": y, "w": w, "h": h, "rid": meta["label"], "gruppo": meta["gruppo"]})

    return rects, max_L

def _ingombro_per_gruppo(rects):
    out = OrderedDict()
    for r in rects:
        g = r["gruppo"]
        if g not in out:
            out[g] = {"min_y": r["y"], "max_y_end": r["y"] + r["h"]}
        else:
            out[g]["min_y"] = min(out[g]["min_y"], r["y"])
            out[g]["max_y_end"] = max(out[g]["max_y_end"], r["y"] + r["h"])
    return OrderedDict((g, (d["max_y_end"] - d["min_y"]) / 100.0) for g, d in out.items())

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
        c.drawString(45, height - 140, f"Metri lineari per scarico: {per_scarico}")

    fig_pdf, ax_pdf = plt.subplots(figsize=(10, 4))
    ax_pdf.set_aspect('equal')
    ax_pdf.set_xlim(-50, max(1400, camion_l + 50)); ax_pdf.set_ylim(-20, max(260, camion_w + 20))
    ax_pdf.add_patch(patches.Rectangle((0, 0), camion_l, camion_w, fill=False, edgecolor='#00386A', lw=2))
    ax_pdf.text(-30, camion_w/2, "CABINA", ha='center', va='center', fontweight='bold', color='#00386A', rotation=90)
    
    gruppi_u = list(OrderedDict.fromkeys([r['gruppo'] for r in rects]))
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

st.markdown("""
<div class="topbar">
  <div class="brand-block">
    <div class="brand">DACHSER</div>
    <div class="brand-sub">VICENZA · DISTRIBUTION</div>
  </div>
  <div class="module-block">
    <div class="module-label">LOAD PLANNER</div>
    <div class="module-sub">Pianificazione carico multi-drop</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---- CONFIGURAZIONE ----
with st.container(border=True):
    st.markdown("#### 🚛 Configurazione veicolo")
    cfg1, cfg2, cfg3, cfg4 = st.columns([1.25, 1.25, 1.5, 1.5])
    with cfg1:
        camion_w = st.number_input("Larghezza utile", min_value=100, max_value=300, value=240, step=5, format="%d cm")
    with cfg2:
        camion_l = st.number_input("Lunghezza utile", min_value=200, max_value=2000, value=1360, step=10, format="%d cm")
    with cfg3:
        vehicle_type = st.selectbox("Tipo veicolo", ["Bilico standard", "Motrice", "Personalizzato"], index=0)
    with cfg4:
        allow_rotation = st.toggle("Ottimizzazione automatica", value=True, help="Consente la rotazione automatica dei colli per cercare un piano migliore.")

# ---- KPI INPUT ----
total_rows = len(st.session_state.lista_di_carico)
total_qty = sum(_normalize_item(i)[5] for i in st.session_state.lista_di_carico)
total_groups = len(OrderedDict.fromkeys([_normalize_item(i)[0] for i in st.session_state.lista_di_carico]))

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Scarichi", total_groups)
with k2:
    st.metric("Pallet / colli", total_qty)
with k3:
    st.metric("Righe carico", total_rows)
with k4:
    st.metric("Pianale", f"{camion_l/100:.2f} × {camion_w/100:.2f} m")

st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)

col_input, col_result = st.columns([0.92, 1.55], gap="large")

# ==========================================
# COLONNA INPUT
# ==========================================
with col_input:
    st.markdown("### 📦 Composizione carico")

    with st.container(border=True):
        st.markdown("**Importazione rapida**")
        uploaded_file = st.file_uploader("Excel / CSV", type=["csv", "xlsx"], label_visibility="collapsed")
        st.caption("Colonne previste: Destinazione, Qta, L, W, H, Sovr · Max_Liv opzionale")
        if uploaded_file is not None:
            if st.button("IMPORTA DATI", width="stretch"):
                try:
                    if uploaded_file.name.lower().endswith('.csv'):
                        df = pd.read_csv(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)

                    imported = 0
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
                        st.session_state.lista_di_carico.append((g, l, w, h, s, q, max_liv))
                        imported += 1
                    st.session_state.last_result = None
                    st.success(f"Importate {imported} righe con successo.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Impossibile importare il file: {e}")

    with st.container(border=True):
        st.markdown("**Aggiungi merce**")
        if st.session_state.editing_index is not None:
            g, l, w, h, s, q, max_liv = _normalize_item(st.session_state.lista_di_carico[st.session_state.editing_index])
            st.info(f"Modifica: **{g}** · {q} pz · {l}×{w}×{h} cm")

        st.text_input("Destinazione / scarico", key="val_g", placeholder="Es. PADOVA")
        f1, f2 = st.columns(2)
        with f1:
            st.number_input("Quantità", min_value=1, key="val_q", step=1)
            st.number_input("Lunghezza (cm)", min_value=1, key="val_l", step=10)
        with f2:
            st.number_input("Larghezza (cm)", min_value=1, key="val_w", step=10)
            st.number_input("Altezza (cm)", min_value=1, key="val_h", step=10)

        s1, s2 = st.columns([1.25, 1])
        with s1:
            st.checkbox("Sovrapponibile", key="val_s", on_change=on_sovr_change)
        with s2:
            if st.session_state.val_s:
                st.number_input("Max livelli", min_value=1, max_value=10, key="val_max_sovr", step=1)

        if st.session_state.editing_index is None:
            st.button("＋ AGGIUNGI CARICO", on_click=aggiungi_voce, type="primary", width="stretch")
        else:
            b1, b2 = st.columns([2, 1])
            with b1:
                st.button("SALVA MODIFICA", on_click=aggiungi_voce, type="primary", width="stretch")
            with b2:
                st.button("ANNULLA", on_click=annulla_modifica, width="stretch")

    if st.session_state.lista_di_carico:
        st.markdown("#### Sequenza scarichi")
        gruppi_vista = OrderedDict()
        for i, item in enumerate(st.session_state.lista_di_carico):
            gruppi_vista.setdefault(item[0], []).append((i, item))

        palette_ui = ['#FFD100', '#005B94', '#6C63FF', '#2E7D32', '#D97706', '#7C3AED', '#0F766E', '#B91C1C']
        for gi, (g, items_gruppo) in enumerate(gruppi_vista.items(), start=1):
            qty_group = sum(_normalize_item(item)[5] for _, item in items_gruppo)
            color = palette_ui[(gi - 1) % len(palette_ui)]
            with st.container(border=True):
                hcol, stat = st.columns([2.2, 1])
                with hcol:
                    st.markdown(f"<div class='stop-title'><span class='stop-dot' style='background:{color}'></span><b>{g}</b></div>", unsafe_allow_html=True)
                    st.caption(f"{len(items_gruppo)} righe · {qty_group} unità")
                with stat:
                    st.caption(f"STOP {gi}")
                for i, item in items_gruppo:
                    _, l, w, h, s, q, max_liv = _normalize_item(item)
                    r1, r2, r3 = st.columns([7.2, 1, 1])
                    with r1:
                        badge = f"Sovr. max {max_liv}" if s else "Non sovr."
                        st.caption(f"{q} × {l}×{w}×{h} cm · {badge}")
                    with r2:
                        st.button("✎", key=f"ed_{i}", on_click=edita_riga, args=(i,))
                    with r3:
                        st.button("×", key=f"del_{i}", on_click=elimina_riga, args=(i,))

        cclear, copt = st.columns([1, 1.5])
        with cclear:
            if st.button("SVUOTA CARICO", width="stretch"):
                st.session_state.lista_di_carico.clear()
                st.session_state.editing_index = None
                st.session_state.last_result = None
                st.rerun()
        with copt:
            esegui = st.button("⚡ OTTIMIZZA PIANALE", type="primary", width="stretch")
    else:
        st.info("Aggiungi la merce oppure importa un file Excel/CSV per costruire il piano di carico.")
        esegui = st.button("⚡ OTTIMIZZA PIANALE", type="primary", width="stretch", disabled=True)

# ==========================================
# COLONNA RISULTATO
# ==========================================
with col_result:
    st.markdown("### 📊 Piano di carico")

    if esegui and st.session_state.lista_di_carico:
        try:
            rects_to_draw, max_L = calcola_posizionamento(
                st.session_state.lista_di_carico, allow_rotation, camion_w, camion_l
            )
            st.session_state.last_result = {
                "rects": rects_to_draw,
                "max_L": max_L,
                "camion_w": camion_w,
                "camion_l": camion_l,
                "allow_rotation": allow_rotation,
            }
        except ValueError as e:
            st.session_state.last_result = None
            st.error(f"⛔ {e}")

    result = st.session_state.last_result
    if result and (
        result["camion_w"] != camion_w
        or result["camion_l"] != camion_l
        or result.get("allow_rotation", True) != allow_rotation
    ):
        result = None

    if result:
        rects_to_draw = result["rects"]
        max_L = result["max_L"]
        result_camion_w = result["camion_w"]
        result_camion_l = result["camion_l"]
        overflow = max_L > result_camion_l
        ingombro_m = max_L / 100
        limite_m = result_camion_l / 100
        utilization = min(100, (max_L / result_camion_l) * 100) if result_camion_l else 0
        margin = max(0, result_camion_l - max_L) / 100
        ingombro_per_gruppo = _ingombro_per_gruppo(rects_to_draw)

        status_cls = "danger" if overflow else "success"
        status_title = "CARICO FUORI SAGOMA" if overflow else "CARICO OTTIMIZZATO"
        status_sub = (
            f"Il piano supera la lunghezza utile di {margin:.2f} m."
            if overflow else
            f"Spazio residuo disponibile: {margin:.2f} m."
        )
        st.markdown(f"""
        <div class="status-card {status_cls}">
            <div>
                <div class="status-kicker">ESITO ELABORAZIONE</div>
                <div class="status-title">{status_title}</div>
                <div class="status-sub">{status_sub}</div>
            </div>
            <div class="status-value">{ingombro_m:.2f}<span> m</span></div>
        </div>
        """, unsafe_allow_html=True)

        mk1, mk2, mk3, mk4 = st.columns(4)
        with mk1:
            st.metric("Metri lineari", f"{ingombro_m:.2f} m", f"{margin:.2f} m liberi" if not overflow else "oltre limite")
        with mk2:
            st.metric("Utilizzo pianale", f"{utilization:.0f}%")
        with mk3:
            st.metric("Unità", total_qty)
        with mk4:
            st.metric("Scarichi", total_groups)

        if ingombro_per_gruppo:
            st.markdown("#### Metri lineari per scarico")
            gcols = st.columns(min(4, len(ingombro_per_gruppo)))
            for idx, (g, m) in enumerate(ingombro_per_gruppo.items()):
                with gcols[idx % len(gcols)]:
                    st.metric(g, f"{m:.2f} m")

        # Piano di carico
        with st.container(border=True):
            st.markdown("**Vista pianale · cabina in basso**")
            total_h = max(result_camion_l, max_L + 50) + 50
            fig_s, ax_s = plt.subplots(figsize=(6.2, max(7.0, 6.2 * (total_h / max(1, result_camion_w)))))
            ax_s.set_aspect('equal')
            ax_s.set_xlim(-18, result_camion_w + 18)
            ax_s.set_ylim(result_camion_l + 25, -35)
            ax_s.add_patch(patches.Rectangle((0, 0), result_camion_w, result_camion_l, fill=False, edgecolor='#00386A', lw=2.2))
            ax_s.text(result_camion_w/2, -17, "CABINA", ha='center', va='center', fontweight='bold', color='#00386A', fontsize=9)
            ax_s.text(result_camion_w + 8, result_camion_l/2, f"{result_camion_l/100:.2f} m", rotation=90, va='center', ha='center', fontsize=7, color='#6b7280')

            gruppi_u = list(OrderedDict.fromkeys([r['gruppo'] for r in rects_to_draw]))
            mappa_c = {g: PALETTE[i % len(PALETTE)] for i, g in enumerate(gruppi_u)}
            for r in rects_to_draw:
                ax_s.add_patch(patches.Rectangle((r['x'], r['y']), r['w'], r['h'], facecolor=mappa_c[r['gruppo']], edgecolor='white', alpha=0.88, lw=1.0))
                ax_s.text(r['x']+r['w']/2, r['y']+r['h']/2, r['rid'], ha='center', va='center', fontsize=6.2, fontweight='bold', color='#111827')

            # tacche metriche ogni metro
            for m in range(1, int(math.ceil(result_camion_l / 100))):
                y = m * 100
                ax_s.plot([-5, 0], [y, y], color='#9ca3af', lw=0.6)
                ax_s.text(-7, y, f"{m}m", fontsize=5.5, color='#6b7280', va='center', ha='right')
            ax_s.axis('off')
            st.pyplot(fig_s, use_container_width=True)
            plt.close(fig_s)

        leg1, leg2 = st.columns([2, 1])
        with leg1:
            st.markdown("**Legenda scarichi**")
            legend_html = " ".join([
                f"<span class='legend-item'><span class='legend-dot' style='background:{mappa_c[g]}'></span>{g}</span>"
                for g in gruppi_u
            ])
            st.markdown(legend_html, unsafe_allow_html=True)
        with leg2:
            st.caption(f"Veicolo: {vehicle_type} · {result_camion_l/100:.2f} × {result_camion_w/100:.2f} m")

        if not overflow:
            pdf_file = genera_pdf_reportlab(
                rects_to_draw, st.session_state.lista_di_carico, max_L, result_camion_w, result_camion_l,
                ingombro_per_gruppo=ingombro_per_gruppo
            )
            st.download_button(
                label="⬇ SCARICA REPORT PDF",
                data=pdf_file,
                file_name="Report_Carico_Dachser_Vicenza.pdf",
                mime="application/pdf",
                width="stretch"
            )
    elif st.session_state.lista_di_carico:
        st.markdown("""
        <div class="empty-result">
            <div class="empty-icon">↗</div>
            <div class="empty-title">Pronto per l'ottimizzazione</div>
            <div class="empty-sub">Inserisci o importa il carico, poi avvia l'ottimizzazione per generare il piano di carico.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="empty-result">
            <div class="empty-icon">＋</div>
            <div class="empty-title">Nessun carico inserito</div>
            <div class="empty-sub">Aggiungi la merce nella sezione a sinistra per iniziare.</div>
        </div>
        """, unsafe_allow_html=True)

