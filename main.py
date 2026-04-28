import streamlit as st
import pandas as pd

# 1. Configuração de tela
st.set_page_config(page_title="BI Labor - Comercial", layout="wide")

# Seu link do Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=240265302&single=true&output=csv"

@st.cache_data(ttl=2)
def load_data():
    try:
        # Lê a planilha tratando tudo como texto
        df = pd.read_csv(SHEET_URL, dtype=str)
        df.columns = df.columns.str.strip().str.upper()
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"Erro ao acessar o Google Sheets: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # --- TRATAMENTO DE COLUNAS ---
    if 'ANO_BI' not in df.columns:
        df['DATA_AUX'] = pd.to_datetime(df['MÊS'], errors='coerce')
        df['ANO_BI'] = df['DATA_AUX'].dt.year.fillna(0).astype(int).astype(str)
        df['MES_BI'] = df['DATA_AUX'].dt.month.fillna(0).astype(int).astype(str)

    # Limpeza de Valores (Moeda para Número)
    def converter_valor(x):
        if pd.isna(x): return 0.0
        v = str(x).replace('R$', '').replace('.', '').replace(',', '.').strip()
        try:
            return float(v)
        except:
            return 0.0

    df['VALOR_NUM'] = df['VALOR ANUAL'].apply(converter_valor)
    df['STATUS_LIMPO'] = df['STATUS'].astype(str).str.strip().str.upper()

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.title("Filtros")
    def get_opts(c):
        return sorted([str(x) for x in df[c].unique() if str(x) not in ['nan','0','']])
    
    f_ano = st.sidebar.multiselect("Ano", get_opts('ANO_BI'), default=get_opts('ANO_BI'))
    f_mes = st.sidebar.multiselect("Mês", get_opts('MES_BI'), default=get_opts('MES_BI'))
    f_status = st.sidebar.multiselect("Status", get_opts('STATUS_LIMPO'), default=get_opts('STATUS_LIMPO'))

    # Aplicação dos Filtros
    df_f = df[(df['ANO_BI'].isin(f_ano)) & (df['MES_BI'].isin(f_mes)) & (df['STATUS_LIMPO'].isin(f_status))]

    # --- DASHBOARD ---
    st.title("📊 BI Comercial - Labor")
    
    # Cálculos robustos
    total_filtrado = df_f['VALOR_NUM'].sum()
    
    # Soma Aprovadas e Apresentadas ignorando pequenas variações no texto
    aprovadas = df_f[df_f['STATUS_LIMPO'].str.contains("APROVAD", na=False)]['VALOR_NUM'].sum()
    apresentadas = df_f[df_f['STATUS_LIMPO'].str.contains("APRESENTAD", na=False)]['VALOR_NUM'].sum()
    
    base_calc = aprovadas + apresentadas
    tx_conv = (aprovadas / base_calc * 100) if base_calc > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total em Tela", f"R$ {total_filtrado:,.2f}")
    c2.metric("Total Aprovado", f"R$ {aprovadas:,.2f}")
    c3.metric("% Conversão", f"{tx_conv:.1f}%")

    st.divider()
    
    if not df_f.empty:
        st.dataframe(df_f[['ANO_BI', 'MES_BI', 'EMPRESA', 'VALOR ANUAL', 'STATUS']], use_container_width=True, hide_index=True)
    else:
        st.info("Selecione os filtros para ver os dados.")

else:
    st.warning("Conectando ao banco de dados...")
