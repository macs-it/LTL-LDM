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

def elimina_riga(index):
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

# --- FUNZIONE LOGICA DI CALCOLO (IL "CERVELLO") ---
def calcola_posizionamento(lista_di_carico, allow_rotation, camion_w, camion_l):
    def tiers_per_item(h, sovrapponibile, max_livello_riga):
        if not sovrapponibile:
            return 1
        return min(max_livello_riga, max(1, 250 // max(1, h)))

    if not allow_rotation:
        rects = []
        for item in lista_di_carico:
            g, l, w, h, s, q, max_liv = _normalize_item(item)
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

    def build_group_rects(items):
        rect_reqs = []
        uid = 0
        for item in items:
            g, l, w, h, s, q, max_liv = _normalize_item(item)
            tiers = tiers_per_item(h, s, max_liv)
            pezzi_rimanenti = q
            for _ in range(math.ceil(q / tiers)):
                pezzi_qui = min(pezzi_rimanenti, tiers)
                label = f"{l}x{w}\nX{pezzi_qui}" if pezzi_qui > 1 else f"{l}x{w}"
                pezzi_rimanenti -= pezzi_qui
                rect_reqs.append({"w": w, "l": l, "rid": f"{g}###{label}###{uid}"})
                uid += 1
        return rect_reqs

    def candidate_orders(rect_reqs):
        base = list(rect_reqs)
        yield base
        yield sorted(base, key=lambda r: r["w"] * r["l"], reverse=True)
        yield sorted(base, key=lambda r: max(r["w"], r["l"]), reverse=True)
        yield sorted(base, key=lambda r: min(r["w"], r["l"]), reverse=True)
        yield sorted(base, key=lambda r: (r["w"] + r["l"]), reverse=True)

    def pack_in_bin(rect_reqs, bin_w, bin_l):
        """Unico packing in un solo bin: usa tutto lo spazio in larghezza e lunghezza."""
        best = None
        for ordered in candidate_orders(rect_reqs):
            p = newPacker(rotation=True, sort_algo=SORT_NONE)
            p.add_bin(bin_w, bin_l)
            for r in ordered:
                p.add_rect(r["w"], r["l"], rid=r["rid"])
            p.pack()
            placed = p.rect_list()
            if len(placed) != len(rect_reqs):
                continue
            used_length = max((y + h) for (_b, _x, y, _w, h, _rid) in placed) if placed else 0
            if best is None or used_length < best["used_length"]:
                best = {"placed": placed, "used_length": used_length}
        if best is None:
            raise ValueError(
                f"Impossibile posizionare tutti i colli nel pianale {bin_w}x{bin_l}cm "
                "(verifica dimensioni e che nessun lato superi la larghezza)."
            )
        return best["placed"], best["used_length"]

    gruppi = OrderedDict()
    for item in lista_di_carico:
        gruppi.setdefault(item[0], []).append(item)

    # Un solo packing globale: tutti i gruppi nello stesso bin, in ordine di scarico.
    # Così rectpack usa lo spazio libero a fianco del gruppo precedente.
    all_rect_reqs = []
    for _g, items in gruppi.items():
        all_rect_reqs.extend(build_group_rects(items))

    placed, max_L = pack_in_bin(all_rect_reqs, camion_w, camion_l)

    rects = []
    for (_b, x, y, w, h, rid) in placed:
        g_e, label, _uid = str(rid).split("###")
        rects.append({"x": x, "y": y, "w": w, "h": h, "rid": label, "gruppo": g_e})

    return rects, max_L

# --- FUNZIONE GENERAZIONE PDF ---
def genera_pdf_reportlab(rects, lista_carico, ingombro, camion_w, camion_l):
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

col_sx, col_dx = st.columns([1.2, 1], gap="large")

with col_sx:
    # --- SEZIONE IMPOSTAZIONI CAMION ---
    with st.expander("🚛 Dimensioni Camion", expanded=False):
        st.markdown("<small>Modifica le dimensioni utili del pianale. Default: Bilico standard (240x1360 cm).</small>", unsafe_allow_html=True)
        camion_w = st.number_input("Larghezza utile (cm)", min_value=100, max_value=300, value=240, step=5)
        camion_l = st.number_input("Lunghezza utile (cm)", min_value=200, max_value=2000, value=1360, step=10)

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
                    
                    for index, row in df.iterrows():
                        g = str(row.get('Destinazione', f'SCARICO {index+1}')).strip().upper()
                        q = int(row.get('Qta', 1))
                        l = int(row.get('L', 120))
                        w = int(row.get('W', 80))
                        h = int(row.get('H', 150))
                        
                        s_raw = str(row.get('Sovr', 'no')).strip().lower()
                        s = True if s_raw in ['si', 'sì', 'yes', 'true', '1'] else False
                        
                        max_liv_raw = row.get('Max_Liv', MAX_SOVR_LIVELLI_DEFAULT if s else 1)
                        max_liv = int(max_liv_raw) if not pd.isna(max_liv_raw) else (MAX_SOVR_LIVELLI_DEFAULT if s else 1)
                        if not s: 
                            max_liv = 1
                        
                        st.session_state.lista_di_carico.append((g, l, w, h, s, q, max_liv))
                    
                    st.success("Dati importati con successo!")
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
            st.rerun()

    allow_rotation = st.checkbox("🔄 Permetti Rotazione Libera (IA)", value=True)
    esegui = st.button("⚡ OTTIMIZZA PIANALE", type="primary", width="stretch")

with col_dx:
    st.markdown("#### 📊 Risultato")
    if esegui and st.session_state.lista_di_carico:
        
        try:
            rects_to_draw, max_L = calcola_posizionamento(st.session_state.lista_di_carico, allow_rotation, camion_w, camion_l)
        except ValueError as e:
            st.error(f"⛔ {e}")
            rects_to_draw, max_L = [], camion_l + 1

        overflow = max_L > camion_l
        ingombro_m = max_L / 100
        limite_m = camion_l / 100
        if overflow:
            card_bg = "#ffe6e6"
            card_border = "#e74c3c"
            card_text = f"⛔ Ingombro: {ingombro_m:.2f} m (Limite {limite_m:.2f} m)"
            card_sub = "Il carico supera la lunghezza utile del veicolo scelto. PDF non generato."
        else:
            card_bg = "#e8ffe6"
            card_border = "#2ecc71"
            card_text = f"✅ Ingombro Totale: {ingombro_m:.2f} m su {limite_m:.2f} m disponibili"
            card_sub = "Il carico rientra nel pianale."

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

        total_h = max(camion_l, max_L + 50) + 50
        fig_s, ax_s = plt.subplots(figsize=(1.2, 1.2 * (total_h / camion_w)))
        ax_s.set_aspect('equal')
        ax_s.set_xlim(0, camion_w); ax_s.set_ylim(total_h, -50)
        ax_s.add_patch(patches.Rectangle((0, 0), camion_w, camion_l, fill=False, edgecolor='#00386A', lw=2))
        ax_s.text(camion_w/2, -25, "CABINA", ha='center', fontweight='bold', color='#00386A', fontsize=5)
        
        gruppi_u = list(OrderedDict.fromkeys([r['gruppo'] for r in rects_to_draw]))
        mappa_c = {g: PALETTE[i % len(PALETTE)] for i, g in enumerate(gruppi_u)}
        for r in rects_to_draw:
            ax_s.add_patch(patches.Rectangle((r['x'], r['y']), r['w'], r['h'], facecolor=mappa_c[r['gruppo']], edgecolor='black', alpha=0.8, lw=0.5))
            ax_s.text(r['x']+r['w']/2, r['y']+r['h']/2, r['rid'], ha='center', va='center', fontsize=3, fontweight='bold')
        ax_s.axis('off')

        if not overflow:
            pdf_file = genera_pdf_reportlab(rects_to_draw, st.session_state.lista_di_carico, max_L, camion_w, camion_l)
            st.download_button(
                label="📄 SCARICA REPORT PDF",
                data=pdf_file,
                file_name="Report_Carico_Vicenza.pdf",
                mime="application/pdf",
                width="stretch"
            )
        
        st.markdown("---")
        _, col_m, _ = st.columns([1.5, 2, 1.5])
        with col_m:
            st.pyplot(fig_s, width="stretch")
        
    elif not st.session_state.lista_di_carico:
        st.info("💡 Aggiungi i bancali a sinistra o importa un file per visualizzare il piano di carico.")
