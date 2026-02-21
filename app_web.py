import streamlit as st
import pandas as pd
from rectpack import newPacker, SORT_NONE
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import random
import math
from collections import OrderedDict

# --- CONFIGURAZIONE PAGINA WEB ---
st.set_page_config(page_title="DACHSER 2D Packer", page_icon="🚛", layout="wide") 

# --- STILE GRAFICO UFFICIALE DACHSER (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #f4f5f7; }
    h1, h2, h3, h4 { color: #00386A !important; font-weight: 800; }
    
    .stButton > button {
        background-color: white !important;
        color: #00386A !important;
        border: 1px solid #00386A !important;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: #00386A !important;
        color: white !important;
    }
    
    .stButton button[kind="primary"] {
        background-color: #FFD100 !important;
        color: #00386A !important;
        border: 2px solid #00386A !important;
        font-size: 18px !important;
        padding: 10px !important;
    }
    .stButton button[kind="primary"]:hover {
        background-color: #00386A !important;
        color: #FFD100 !important;
    }
    
    div[data-testid="stAlert"] {
        background-color: white;
        border-left: 5px solid #00386A;
        color: black;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
    }
    
    /* Linea di separazione verticale virtuale */
    .css-1r6slb0 { border-right: 2px solid #e1e4e8; padding-right: 20px;}
    </style>
""", unsafe_allow_html=True)

# --- INIZIALIZZAZIONE VARIABILI ---
if 'lista_di_carico' not in st.session_state:
    st.session_state.lista_di_carico = []

if 'in_gruppo' not in st.session_state: st.session_state.in_gruppo = "CARICO 1"
if 'in_lung' not in st.session_state: st.session_state.in_lung = 120
if 'in_larg' not in st.session_state: st.session_state.in_larg = 80
if 'in_alt' not in st.session_state: st.session_state.in_alt = 150
if 'in_sovr' not in st.session_state: st.session_state.in_sovr = False
if 'in_qta' not in st.session_state: st.session_state.in_qta = 1

st.markdown("<h1 style='text-align: center;'>DACHSER Intelligent Logistics</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>Ottimizzatore Carico Multi-Drop</h3>", unsafe_allow_html=True)
st.markdown("---")

# --- FUNZIONI DI SUPPORTO MANUALI ---
def aggiungi_bancale():
    if st.session_state.in_alt > 250:
        st.error("⛔ Altezza massima consentita superata (250 cm)!")
    else:
        gruppo_pulito = st.session_state.in_gruppo.strip().upper()
        if not gruppo_pulito: gruppo_pulito = "STANDARD"

        st.session_state.lista_di_carico.append((
            gruppo_pulito,
            st.session_state.in_lung, 
            st.session_state.in_larg, 
            st.session_state.in_alt, 
            st.session_state.in_sovr, 
            st.session_state.in_qta
        ))

def edita_riga(index):
    g, l, w, h, s, q = st.session_state.lista_di_carico.pop(index)
    st.session_state.in_gruppo = g
    st.session_state.in_lung = l
    st.session_state.in_larg = w
    st.session_state.in_alt = h
    st.session_state.in_sovr = s
    st.session_state.in_qta = q

def elimina_riga(index):
    st.session_state.lista_di_carico.pop(index)

# ==========================================
# CREAZIONE DELLE DUE MACRO-COLONNE
# ==========================================
col_sinistra, col_destra = st.columns([1.2, 1], gap="large")

# ------------------------------------------
# PARTE SINISTRA: INPUT DATI E LISTA
# ------------------------------------------
with col_sinistra:
    # 1. IMPORTAZIONE MASSIVA
    with st.expander("📂 IMPORTA MASSIVAMENTE DA FILE (Excel / CSV)"):
        st.markdown("""
        Crea un file Excel/CSV con questa intestazione:
        **`GRUPPO`** | **`LUNGHEZZA`** | **`LARGHEZZA`** | **`ALTEZZA`** | **`SOVRAPPONIBILE`** *(S/N)* | **`QUANTITA`**
        """)
        uploaded_file = st.file_uploader("Trascina o seleziona qui il tuo file", type=['xlsx', 'csv'])
        
        if uploaded_file is not None:
            if st.button("📥 CARICA DATI NEL PIANALE", use_container_width=True):
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df = pd.read_csv(uploaded_file, sep=None, engine='python')
                    else:
                        df = pd.read_excel(uploaded_file)
                    
                    df.columns = df.columns.str.strip().str.upper()
                    
                    for index, row in df.iterrows():
                        g = str(row.get('GRUPPO', 'STANDARD')).strip().upper()
                        if g == 'NAN' or not g: g = "STANDARD"
                        
                        l = int(row.get('LUNGHEZZA', 120))
                        w = int(row.get('LARGHEZZA', 80))
                        h = int(row.get('ALTEZZA', 150))
                        
                        s_str = str(row.get('SOVRAPPONIBILE', 'N')).strip().upper()
                        s = True if s_str in ['SI', 'SÌ', 'YES', 'TRUE', '1', 'VERO', 'S'] else False
                        
                        q = int(row.get('QUANTITA', row.get('QUANTITÀ', 1)))
                        
                        st.session_state.lista_di_carico.append((g, l, w, h, s, q))
                    
                    st.success("File importato con successo!")
                    st.rerun()
                except Exception as e:
                    st.error(f"⛔ Errore durante la lettura: {e}")

    # 2. INSERIMENTO MANUALE
    st.markdown("#### 📥 Inserimento Manuale")
    col_g, col_q = st.columns([3, 1])
    with col_g:
        st.text_input("📍 Gruppo / Destinazione", key="in_gruppo")
    with col_q:
        st.number_input("📦 Quantità", min_value=1, step=1, key="in_qta")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.number_input("Lunghezza (cm)", min_value=1, step=10, key="in_lung")
    with col2:
        st.number_input("Larghezza (cm)", min_value=1, step=10, key="in_larg")
    with col3:
        st.number_input("Altezza (cm)", min_value=1, step=10, key="in_alt")
    with col4:
        st.write("") 
        st.write("") 
        st.checkbox("Sovrapponibile", key="in_sovr")
        
    st.button("➕ AGGIUNGI BANCALE SINGOLO", on_click=aggiungi_bancale, use_container_width=True)
    st.write("")

    # 3. LISTA BANCALI
    if st.session_state.lista_di_carico:
        st.markdown("#### 📦 Lista di carico in attesa:")
        for i, (g, l, w, h, s, q) in enumerate(st.session_state.lista_di_carico):
            sovr_testo = "Sì" if s else "No"
            
            c_txt, c_ed, c_del = st.columns([8, 1, 1])
            with c_txt:
                st.info(f"**{g}** | **{q}x** Pallet {l}x{w} h:{h} | Sovr: {sovr_testo}")
            with c_ed:
                st.button("✏️", key=f"edit_{i}", on_click=edita_riga, args=(i,))
            with c_del:
                st.button("❌", key=f"del_{i}", on_click=elimina_riga, args=(i,))
        
        if st.button("🗑️ Svuota Tutto"):
            st.session_state.lista_di_carico.clear()
            st.rerun()

    st.markdown("---")
    
    # 4. BOTTONE DI CALCOLO
    allow_rotation = st.checkbox("🔄 Permetti Rotazione Libera (Usa IA Tetris)", value=False)
    st.caption("💡 **Nota:** Disattivata usa la simulazione gravitazionale riempiendo i buchi dei carichi precedenti in ordine cronologico.")

    esegui_calcolo = st.button("⚡ OTTIMIZZA PIANALE", type="primary", use_container_width=True)


# ------------------------------------------
# PARTE DESTRA: VISUALIZZAZIONE GRAFICA
# ------------------------------------------
with col_destra:
    st.markdown("#### 📊 Risultato Ottimizzazione")
    
    if esegui_calcolo:
        if not st.session_state.lista_di_carico:
            st.warning("La lista di carico è vuota! Inserisci della merce a sinistra.")
        else:
            larghezza_camion = 240
            lunghezza_camion = 1360
            altezza_camion = 250
            
            gruppi_unici = []
            for g, _, _, _, _, _ in st.session_state.lista_di_carico:
                if g not in gruppi_unici:
                    gruppi_unici.append(g)

            rectangles_to_draw = []

            if not allow_rotation:
                placed_rects = []
                for g, l, w, h, s, q in st.session_state.lista_di_carico:
                    tiers = 1 if not s else max(1, altezza_camion // h) if h > 0 else 1
                    posti_a_terra = math.ceil(q / tiers)
                    nome_base = f"{l}x{w}"
                    label_grafico = f"{nome_base}\n(x{tiers})" if tiers > 1 else nome_base
                    
                    for _ in range(posti_a_terra):
                        best_y = float('inf')
                        best_x = 0
                        
                        xs_to_try = [0] + [r['x'] + r['w'] for r in placed_rects if r['x'] + r['w'] + w <= larghezza_camion]
                        xs_to_try = sorted(list(set(xs_to_try)))
                        if not xs_to_try: xs_to_try = [0]
                        
                        for x in xs_to_try:
                            max_y_in_interval = 0
                            for r in placed_rects:
                                if x < r['x'] + r['w'] and x + w > r['x']:
                                    if r['y'] + r['h'] > max_y_in_interval:
                                        max_y_in_interval = r['y'] + r['h']
                            
                            if max_y_in_interval < best_y:
                                best_y = max_y_in_interval
                                best_x = x
                                
                        new_rect = {'x': best_x, 'y': best_y, 'w': w, 'h': l, 'rid': label_grafico, 'gruppo': g}
                        placed_rects.append(new_rect)
                
                rectangles_to_draw = placed_rects
                max_lunghezza_occupata = max([r['y'] + r['h'] for r in placed_rects]) if placed_rects else 0

            else:
                p = newPacker(rotation=True, sort_algo=SORT_NONE)
                lunghezza_virtuale = 10000 
                p.add_bin(larghezza_camion, lunghezza_virtuale)
                
                for g, l, w, h, s, q in st.session_state.lista_di_carico:
                    tiers = 1 if not s else max(1, altezza_camion // h) if h > 0 else 1
                    posti_a_terra = math.ceil(q / tiers)
                    nome_base = f"{l}x{w}"
                    label_grafico = f"{nome_base}\n(x{tiers})" if tiers > 1 else nome_base

                    for _ in range(posti_a_terra):
                        p.add_rect(w, l, rid=f"{g}###{label_grafico}")

                p.pack()

                for b in p:
                    for rect in b:
                        g_estr, testo_estr = str(rect.rid).split("###")
                        rectangles_to_draw.append({
                            'x': rect.x, 'y': rect.y, 'w': rect.width, 'h': rect.height,
                            'rid': testo_estr, 'gruppo': g_estr
                        })
                max_lunghezza_occupata = max([r['y'] + r['h'] for r in rectangles_to_draw]) if rectangles_to_draw else 0

            # RISULTATI TESTUALI
            if max_lunghezza_occupata > lunghezza_camion:
                st.error(f"⛔ **CARICO ECCESSIVO!** Occupi {max_lunghezza_occupata/100:.2f} m (+{(max_lunghezza_occupata - lunghezza_camion)/100:.2f} m di fuori sagoma)")
            else:
                st.success(f"✅ **Ingombro Fisico:** {max_lunghezza_occupata/100:.2f} m")

            # GRAFICA
            lunghezza_disegno = max(lunghezza_camion, max_lunghezza_occupata + 100)
            ratio = lunghezza_disegno / larghezza_camion
            
            # Ridimensionato il grafico a larghezza 2.5 per bilanciarlo con la colonna sinistra
            fig, ax = plt.subplots(figsize=(2.5, 2.5 * ratio))
            ax.set_xlim(0, larghezza_camion)
            ax.set_ylim(lunghezza_disegno, 0)
            ax.set_aspect('equal')
            
            ax.add_patch(patches.Rectangle((0, 0), larghezza_camion, lunghezza_camion, fill=False, edgecolor='#00386A', lw=4))
            ax.text(larghezza_camion/2, -30, "⬆ CABINA ⬆", ha='center', va='center', fontsize=10, fontweight='bold', color='#00386A')

            palette_colori = ['#3498db', '#e67e22', '#2ecc71', '#9b59b6', '#f1c40f', '#1abc9c', '#e74c3c']
            mappa_colori_gruppi = {}
            for idx, nome_g in enumerate(gruppi_unici):
                mappa_colori_gruppi[nome_g] = palette_colori[idx % len(palette_colori)]
            
            for rect in rectangles_to_draw:
                colore_gruppo = mappa_colori_gruppi[rect['gruppo']]
                
                if rect['y'] >= lunghezza_camion:
                    colore_fill = "#ecf0f1"
                    colore_bordo = "red"
                else:
                    colore_fill = colore_gruppo
                    colore_bordo = "black"

                ax.add_patch(patches.Rectangle((rect['x'], rect['y']), rect['w'], rect['h'], facecolor=colore_fill, edgecolor=colore_bordo, lw=2, alpha=0.9))
                ax.text(rect['x'] + rect['w']/2, rect['y'] + rect['h']/2, rect['rid'], ha='center', va='center', fontsize=6, fontweight='bold', color='black')

            if max_lunghezza_occupata > lunghezza_camion:
                ax.axhline(y=lunghezza_camion, color='red', linestyle='--', linewidth=3)
                ax.text(larghezza_camion/2, lunghezza_camion - 20, "⛔ LIMITE (13.60m) ⛔", ha='center', va='center', color='red', fontweight='bold', fontsize=8)
            else:
                ax.text(larghezza_camion/2, lunghezza_camion + 40, "⬇ PORTELLONE ⬇", ha='center', va='center', fontsize=10, fontweight='bold', color='#00386A')

            ax.axis('off')
            
            # Usando st.pyplot centrerà o adatterà automaticamente l'immagine nella colonna di destra
            st.pyplot(fig)
            
            st.markdown("---")
            st.markdown("**LEGENDA CARICHI:**")
            for nome_g, colore in mappa_colori_gruppi.items():
                st.markdown(f"<span style='color:{colore}; font-size: 16px;'>■</span> **{nome_g}**", unsafe_allow_html=True)
                
    else:
        st.info("👈 Compila i dati a sinistra e clicca su **OTTIMIZZA PIANALE** per visualizzare il grafico.")