import streamlit as st
import pandas as pd

# 1. Configuração de tela
st.set_page_config(page_title="BI Labor", layout="wide")

# Link do Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=240265302&single=true&output=csv"

@st.cache_data(ttl=5)
def load_data():
    try:
        # Lê a planilha tratando tudo como texto para evitar conflitos
        df = pd.read_csv(SHEET_URL, on_bad_lines='skip', dtype=str)
        df.columns = df.columns.str.strip().str.upper() # Tudo para MAIÚSCULO e sem espaços
        df = df.dropna(how='all') # Remove linhas vazias
        return df
    except Exception as e:
        st.error(f"Erro na leitura do link: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # --- GARANTIA DE COLUNAS (Se não existir, criamos para não dar erro) ---
    for col in ['ANO_BI', 'MES_BI', 'STATUS', 'VALOR ANUAL', 'EMPRESA']:
        if col not in df.columns:
            df[col] = "N/A"

    # --- LIMPEZA DE DADOS ---
    df['ANO_BI'] = df['ANO_BI'].astype(str).str.replace('.0', '', regex=False).str.strip()
    df['MES_BI'] = df['MES_BI'].astype(str).str.strip()
    df['STATUS'] = df['STATUS'].astype(str).str.strip().str.upper()
    
    # Tratamento de Valor (Blindado contra R$ e pontos)
    v = df['VALOR ANUAL'].astype(str).str.replace(r'[^0-9,]', '', regex=True).str.replace(',', '.')
    df['VALOR_NUM'] = pd.to_numeric(v, errors='coerce').fillna(0)

    # --- BARRA LATERAL ---
    st.sidebar.title("Filtros")
    
    def get_options(col):
        return sorted([x for x in df[col].unique() if x not in ['nan', 'N/A', 'None', '']])

    sel_ano = st.sidebar.multiselect("Ano", options=get_options('ANO_BI'), default=get_options('ANO_BI'))
    sel_mes = st.sidebar.multiselect("Mês", options=get_options('MES_BI'), default=get_options('MES_BI'))
    sel_status = st.sidebar.multiselect("Status", options=get_options('STATUS'), default=get_options('STATUS'))

    # Aplicação dos Filtros
    df_filtrado = df[
        (df['ANO_BI'].isin(sel_ano)) & 
        (df['MES_BI'].isin(sel_mes)) & 
        (df['STATUS'].isin(sel_status))
    ]

    # --- DASHBOARD ---
    st.title("📊 BI Comercial - Labor")

    # KPIs
    total_visto = df_filtrado['VALOR_NUM'].sum()
    aprovadas = df_filtrado[df_filtrado['STATUS'] == 'APROVADA']['VALOR_NUM'].sum()
    # Base conversão: APROVADA + APRESENTADO
    base = df_filtrado[df_filtrado['STATUS'].isin(['APROVADA', 'APRESENTADO'])]['VALOR_NUM'].sum()
    conv = (aprovadas / base * 100) if base > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total no Filtro", f"R$ {total_visto:,.2f}")
    c2.metric("Total Aprovado", f"R$ {aprovadas:,.2f}")
    c3.metric("% Conversão", f"{conv:.1f}%")

    st.divider()
    st.dataframe(df_filtrado[['ANO_BI', 'MES_BI', 'EMPRESA', 'VALOR_NUM', 'STATUS']], use_container_width=True)
else:
    st.warning("Aguardando conexão com o Google Sheets...")
