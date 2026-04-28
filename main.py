import streamlit as st
import pandas as pd

st.set_page_config(page_title="BI Labor - Comercial", layout="wide")

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
    # 1. Cria colunas de data caso não existam no Sheets
    if 'ANO_BI' not in df.columns:
        df['DATA_AUX'] = pd.to_datetime(df['MÊS'], errors='coerce')
        df['ANO_BI'] = df['DATA_AUX'].dt.year.fillna(0).astype(int).astype(str)
        df['MES_BI'] = df['DATA_AUX'].dt.month.fillna(0).astype(int).astype(str)

    # 2. LIMPEZA TOTAL DE VALORES (Garante que R$ 1.250,00 vire 1250.00)
    def converter_valor(x):
        if pd.isna(x): return 0.0
        v = str(x).replace('R$', '').replace('.', '').replace(',', '.').strip()
        try:
            return float(v)
        except:
            return 0.0

    df['VALOR_NUM'] = df['VALOR ANUAL'].apply(converter_valor)
    
    # 3. PADRONIZAÇÃO DE STATUS (Tira espaços e deixa tudo igual)
    df['STATUS_LIMPO'] = df['STATUS'].astype(str).str.strip().str.upper()

    # --- FILTROS ---
    st.sidebar.title("Filtros")
    def get_opts(c): return sorted([str(x) for x in df[c].unique() if str(x) not in ['nan','0','']])
    
    f_ano = st.sidebar.multiselect("Ano", get_opts('ANO_BI'), default=get_opts('ANO_BI'))
    f_mes = st.sidebar.multiselect("Mês", get_opts('MES_BI'), default=get_opts('MES_BI'))
    f_status = st.sidebar.multiselect("Status", get_opts('STATUS_LIMPO'), default=get_opts('STATUS_LIMPO'))

    df_f = df[(df['ANO_BI'].isin(f_ano)) & (df['MES_BI'].isin(f_mes)) & (df['STATUS_LIMPO'].isin(f_status))]

    # --- CÁLCULOS (AQUI ESTAVA O ERRO) ---
    # Usamos .str.contains para pegar "APROVADA" ou "APROVADO"
    total_filtrado = df_f['VALOR_NUM'].sum()
    
    # Soma o que for APROVADO/A
    aprovadas = df_f[df_f['STATUS_LIMPO'].str.contains("APROVAD", na=False)]['VALOR_NUM'].sum()
    
    # Soma o que for APRESENTADO
    apresentadas = df_f[df_f['STATUS_LIMPO'].str.contains("APRESENTAD", na=False)]['VALOR_NUM'].sum()
    
    # Base de cálculo: Aprovados + Apresentados
    base_calc = aprovadas + apresentadas
    tx_conv = (aprovadas / base_calc * 100) if base_calc > 0 else 0

    # --- DASHBOARD ---
    st.title("📊 BI Comercial - Labor")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Valor Total Filtrado", f"R$ {total_filtrado:,.2f}")
    c2.metric("Total Aprovado", f"R$ {aprovadas:,.2f}")
    c3.metric("% Conversão (Apro/Apre)", f"{tx_conv:.1f}%")

    st.divider()
    st.dataframe(df_f[['ANO_BI', 'MES_BI', 'EMPRESA', 'VALOR ANUAL', 'STATUS']], use_container_width=True, hide_index=True)
else:
    st.warning("Sem dados.")
