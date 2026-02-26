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
CAMION_W = 240
CAMION_L = 1360
PALETTE = ['#3498db', '#e67e22', '#2ecc71', '#9b59b6', '#f1c40f', '#e74c3c', '#1abc9c', '#34495e', '#d35400', '#7f8c8d']

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

if 'val_g' not in st.session_state: st.session_state.val_g = "SCARICO 1"
for val, default in [('val_q', 1), ('val_l', 120), ('val_w', 80), ('val_h', 150), ('val_s', False)]:
    if val not in st.session_state: st.session_state[val] = default

# --- FUNZIONI LISTA INTERFACCIA ---
def aggiungi_voce():
    st.session_state.lista_di_carico.append((st.session_state.val_g.upper(), st.session_state.val_l, st.session_state.val_w, st.session_state.val_h, st.session_state.val_s, st.session_state.val_q))

def elimina_riga(index):
    st.session_state.lista_di_carico.pop(index)

def edita_riga(index):
    g, l, w, h, s, q = st.session_state.lista_di_carico.pop(index)
    st.session_state.val_g = g
    st.session_state.val_l = l
    st.session_state.val_w = w
    st.session_state.val_h = h
    st.session_state.val_s = s
    st.session_state.val_q = q

# --- FUNZIONE LOGICA DI CALCOLO ---
def calcola_posizionamento(lista_di_carico, allow_rotation):
    rects = []
    
    gruppi_ordinati = OrderedDict()
    for item in lista_di_carico:
        g = item[0]
        if g not in gruppi_ordinati: gruppi_ordinati[g] = []
        gruppi_ordinati[g].append(item)
        
    lista_raggruppata = []
    for g in gruppi_ordinati:
        lista_raggruppata.extend(gruppi_ordinati[g])

    if not allow_rotation:
        for g, l, w, h, s, q in lista_raggruppata:
            tiers = max(1, 250 // h) if s else 1
            pezzi_rimanenti = q
            for _ in range(math.ceil(q / tiers)):
                pezzi_qui = min(pezzi_rimanenti, tiers)
                label = f"{l}x{w}\n(x{pezzi_qui})" if pezzi_qui > 1 else f"{l}x{w}"
                pezzi_rimanenti -= pezzi_qui
                
                best_y = float('inf'); best_x = 0
                xs = sorted(list(set([0] + [r['x'] + r['w'] for r in rects if r['x'] + r['w'] + w <= CAMION_W])))
                for x in xs:
                    max_y = 0
                    for r in rects:
                        if x < r['x'] + r['w'] and x + w > r['x']: max_y = max(max_y, r['y'] + r['h'])
                    if max_y < best_y: best_y, best_x = max_y, x
                rects.append({'x': best_x, 'y': best_y, 'w': w, 'h': l, 'rid': label, 'gruppo': g})
    else:
        p = newPacker(rotation=True, sort_algo=SORT_NONE)
        p.add_bin(CAMION_W, 10000)
        for g, l, w, h, s, q in lista_raggruppata:
            tiers = max(1, 250 // h) if s else 1
            pezzi_rimanenti = q
            for _ in range(math.ceil(q / tiers)):
                pezzi_qui = min(pezzi_rimanenti, tiers)
                label = f"{l}x{w}\n(x{pezzi_qui})" if pezzi_qui > 1 else f"{l}x{w}"
                pezzi_rimanenti -= pezzi_qui
                p.add_rect(w, l, rid=f"{g}###{label}")
        p.pack()
        for b in p:
            for r in b:
                g_e, l_e = str(r.rid).split("###")
                rects.append({'x': r.x, 'y': r.y, 'w': r.width, 'h': r.height, 'rid': l_e, 'gruppo': g_e})

    max_L = max([r['y'] + r['h'] for r in rects]) if rects else 0
    return rects, max_L

# --- FUNZIONE GENERAZIONE PDF ---
def genera_pdf_reportlab(rects, lista_carico, ingombro):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    
    c.setFillColorRGB(0, 0.22, 0.41) 
    c.rect(0, height - 85, width, 85, fill=1)
    c.setFillColor(colors.yellow); c.setFont("Helvetica-Bold", 26)
    c.drawString(45, height - 45, "DACHSER")
    c.setFillColor(colors.white); c.setFont("Helvetica", 12)
    c.drawString(45, height - 70, "REPORT DI CARICO - Filiale di Vicenza")
    
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold", 10)
    c.drawString(400, height - 110, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    c.drawString(400, height - 125, f"Ingombro Totale: {ingombro/100:.2f} m")

    fig_pdf, ax_pdf = plt.subplots(figsize=(10, 4)) 
    ax_pdf.set_aspect('equal')
    ax_pdf.set_xlim(-50, 1400); ax_pdf.set_ylim(-20, 260)
    ax_pdf.add_patch(patches.Rectangle((0, 0), CAMION_L, CAMION_W, fill=False, edgecolor='#00386A', lw=2))
    ax_pdf.text(-30, 120, "CABINA", ha='center', va='center', fontweight='bold', color='#00386A', rotation=90)
    
    gruppi_u = list(OrderedDict.fromkeys([r['gruppo'] for r in rects]))
    mappa_c = {g: PALETTE[i % len(PALETTE)] for i, g in enumerate(gruppi_u)}
    
    for r in rects:
        ax_pdf.add_patch(patches.Rectangle((r['y'], r['x']), r['h'], r['w'], facecolor=mappa_c[r['gruppo']], edgecolor='black', alpha=0.9, lw=0.7))
        ax_pdf.text(r['y']+r['h']/2, r['x']+r['w']/2, r['rid'].replace('\n',' '), ha='center', va='center', fontsize=6, fontweight='bold')
    
    ax_pdf.axis('off')
    img_buffer = io.BytesIO()
    fig_pdf.savefig(img_buffer, format='png', bbox_inches='tight', dpi=180)
    plt.close(fig_pdf)
    img_buffer.seek(0)
    c.drawImage(ImageReader(img_buffer), 30, 400, width=535, preserveAspectRatio=True)

    c.setFont("Helvetica-Bold", 13)
    c.drawString(45, 360, "ELENCO MERCI CARICATE:")
    table_data = [["Destinazione", "Dim. (cm)", "Q.tà", "Sovr."]]
    for g, l, w, h, s, q in lista_carico: table_data.append([g, f"{l}x{w}x{h}", str(q), "Sì" if s else "No"])
    
    t = Table(table_data, colWidths=[180, 110, 60, 60])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#00386A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.yellow),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.7, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
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
    # --- SEZIONE IMPORTAZIONE EXCEL / CSV ---
    with st.expander("📁 Importa lista da Excel o CSV"):
        st.markdown("""
        <small>Il file deve contenere le colonne: <b>Destinazione, Qta, L, W, H, Sovr</b><br><br>
        💡 <b>Sovr:</b> Indica se il bancale è sovrapponibile (regge altra merce sopra).<br>
        <i>Scrivere 'si' o '1' se lo è, altrimenti 'no' o '0'.</i></small>
        """, unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Carica file", type=["csv", "xlsx"], label_visibility="collapsed")
        
        if uploaded_file is not None:
            if st.button("📥 CARICA DATI", use_container_width=True):
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
                        
                        st.session_state.lista_di_carico.append((g, l, w, h, s, q))
                    
                    st.success("Dati importati con successo!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore nella lettura del file: controlla che le colonne siano corrette. Dettaglio: {e}")

    st.markdown("#### 📥 Inserimento Manuale")
    
    st.text_input("📍 Destinazione (Scarico)", key="val_g")
    
    c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1.2, 1.2, 0.8])
    with c1: st.number_input("📦 Q.tà", min_value=1, key="val_q", step=1)
    with c2: st.number_input("L (cm)", min_value=1, key="val_l", step=10)
    with c3: st.number_input("W (cm)", min_value=1, key="val_w", step=10)
    with c4: st.number_input("H (cm)", min_value=1, key="val_h", step=10)
    with c5: 
        st.write("")
        st.checkbox("Sovr.", key="val_s")
    
    st.button("➕ AGGIUNGI", on_click=aggiungi_voce, use_container_width=True)

    if st.session_state.lista_di_carico:
        st.markdown("---")
        
        gruppi_vista = OrderedDict()
        for i, item in enumerate(st.session_state.lista_di_carico):
            gruppi_vista.setdefault(item[0], []).append((i, item))
            
        for g, items_gruppo in gruppi_vista.items():
            st.markdown(f"<h6 style='color:#00386A; margin-top: 15px; margin-bottom: 5px; font-weight:bold;'>📍 {g}</h6>", unsafe_allow_html=True)
            for i, item in items_gruppo:
                _, l, w, h, s, q = item
                cs1, cs2, cs3 = st.columns([8, 1, 1])
                with cs1: st.info(f"{q} pz | {l} x {w} x {h} cm | Sovr: {'Sì' if s else 'No'}")
                with cs2: st.button("✏️", key=f"ed_{i}", on_click=edita_riga, args=(i,))
                with cs3: st.button("❌", key=f"del_{i}", on_click=elimina_riga, args=(i,))
        
        if len(st.session_state.lista_di_carico) > 11:
            st.warning("⚠️ Hai inserito molti lotti. La tabella nel PDF potrebbe essere tagliata.")
            
        if st.button("🗑️ Svuota Tutto"): 
            st.session_state.lista_di_carico.clear()
            st.session_state.val_g = "SCARICO 1"
            st.rerun()

    allow_rotation = st.checkbox("🔄 Permetti Rotazione Libera (IA)", value=False)
    esegui = st.button("⚡ OTTIMIZZA PIANALE", type="primary", use_container_width=True)

with col_dx:
    st.markdown("#### 📊 Risultato")
    if esegui and st.session_state.lista_di_carico:
        
        rects_to_draw, max_L = calcola_posizionamento(st.session_state.lista_di_carico, allow_rotation)

        if max_L > CAMION_L: st.error(f"⛔ Eccesso: {max_L/100:.2f} m (Limite {CAMION_L/100}m)")
        else: st.success(f"✅ Ingombro Totale: {max_L/100:.2f} m")

        total_h = max(CAMION_L, max_L + 50) + 50
        fig_s, ax_s = plt.subplots(figsize=(1.2, 1.2 * (total_h / CAMION_W)))
        ax_s.set_aspect('equal')
        ax_s.set_xlim(0, CAMION_W); ax_s.set_ylim(total_h, -50)
        ax_s.add_patch(patches.Rectangle((0, 0), CAMION_W, CAMION_L, fill=False, edgecolor='#00386A', lw=2))
        ax_s.text(CAMION_W/2, -25, "CABINA", ha='center', fontweight='bold', color='#00386A', fontsize=5)
        
        gruppi_u = list(OrderedDict.fromkeys([r['gruppo'] for r in rects_to_draw]))
        mappa_c = {g: PALETTE[i % len(PALETTE)] for i, g in enumerate(gruppi_u)}
        for r in rects_to_draw:
            ax_s.add_patch(patches.Rectangle((r['x'], r['y']), r['w'], r['h'], facecolor=mappa_c[r['gruppo']], edgecolor='black', alpha=0.8, lw=0.5))
            ax_s.text(r['x']+r['w']/2, r['y']+r['h']/2, r['rid'], ha='center', va='center', fontsize=3, fontweight='bold')
        ax_s.axis('off')

        pdf_file = genera_pdf_reportlab(rects_to_draw, st.session_state.lista_di_carico, max_L)
        st.download_button(
            label="📄 SCARICA REPORT PDF",
            data=pdf_file,
            file_name="Report_Carico_Vicenza.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        
        st.markdown("---")
        _, col_m, _ = st.columns([1.5, 2, 1.5])
        with col_m: st.pyplot(fig_s, use_container_width=True)
        
    elif not st.session_state.lista_di_carico:
        st.info("💡 Aggiungi i bancali a sinistra o importa un file per visualizzare il piano di carico.")
