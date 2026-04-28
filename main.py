import streamlit as st
import pandas as pd

st.set_page_config(page_title="BI Labor", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=240265302&single=true&output=csv"

@st.cache_data(ttl=2)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, dtype=str)
        df.columns = df.columns.str.strip().str.upper()
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"Erro: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # 1. Garantia de colunas de tempo
    if 'ANO_BI' not in df.columns:
        df['DATA_AUX'] = pd.to_datetime(df['MÊS'], errors='coerce')
        df['ANO_BI'] = df['DATA_AUX'].dt.year.fillna(0).astype(int).astype(str)
        df['MES_BI'] = df['DATA_AUX'].dt.month.fillna(0).astype(int).astype(str)

    # 2. Limpeza de Valores (Crucial para o cálculo bater)
    def clean_num(x):
        if pd.isna(x): return 0.0
        v = str(x).replace('R$', '').replace('.', '').replace(',', '.').strip()
        try: return float(v)
        except: return 0.0

    df['VALOR_NUM'] = df['VALOR ANUAL'].apply(clean_num)
    
    # 3. Limpeza de Status (Removendo espaços invisíveis que causam o erro de 100%)
    df['STATUS_FINAL'] = df['STATUS'].astype(str).str.strip().str.upper()

    # --- FILTROS ---
    st.sidebar.title("Filtros")
    def get_opts(c): return sorted([str(x) for x in df[c].unique() if str(x) not in ['nan','0','']])
    
    f_ano = st.sidebar.multiselect("Ano", get_opts('ANO_BI'), default=get_opts('ANO_BI'))
    f_mes = st.sidebar.multiselect("Mês", get_opts('MES_BI'), default=get_opts('MES_BI'))
    f_status = st.sidebar.multiselect("Status", get_opts('STATUS_FINAL'), default=get_opts('STATUS_FINAL'))

    # Filtragem dos dados
    df_f = df[(df['ANO_BI'].isin(f_ano)) & (df['MES_BI'].isin(f_mes)) & (df['STATUS_FINAL'].isin(f_status))]

    # --- TROQUE APENAS ESTE BLOCO ---
    total_visto = df_f['VALOR_NUM'].sum()
        
    # Soma quem contém "APROVAD" (pega Aprovada, Aprovado, com ou sem espaço)
    aprovadas = df_f[df_f['STATUS'].str.contains('APROVAD', na=False)]['VALOR_NUM'].sum()
        
    # Soma quem contém "APRESENTAD"
    apresentadas = df_f[df_f['STATUS'].str.contains('APRESENTAD', na=False)]['VALOR_NUM'].sum()
        
    base_conv = aprovadas + apresentadas
    tx = (aprovadas / base_calc * 100) if base_calc > 0 else 0
    # -------------------------------

    # --- EXIBIÇÃO ---
    st.title("📊 BI Comercial - Labor")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total em Tela", f"R$ {total_em_tela:,.2f}")
    c2.metric("Total Aprovado", f"R$ {v_aprovada:,.2f}")
    c3.metric("% Conversão", f"{percentual:.1f}%")

    st.divider()
    st.dataframe(df_f[['ANO_BI', 'MES_BI', 'EMPRESA', 'VALOR ANUAL', 'STATUS']], use_container_width=True, hide_index=True)
else:
    st.warning("Sem dados.")
