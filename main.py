import streamlit as st
import pandas as pd

# 1. Configuração de tela
st.set_page_config(page_title="BI Labor - Comercial", layout="wide")

# Seu link do Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=240265302&single=true&output=csv"

@st.cache_data(ttl=5)
def load_data():
    try:
        # Lê a planilha tratando tudo como texto
        df = pd.read_csv(SHEET_URL, dtype=str)
        df.columns = df.columns.str.strip().str.upper()
        df = df.dropna(how='all')
        return df
    except Exception as e:
        st.error(f"Erro ao acessar o Google Sheets: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # --- SISTEMA ANTI-ERRO DE COLUNAS ---
    # Se você ainda não criou ou o Sheets não atualizou, o Python cria agora:
    if 'ANO_BI' not in df.columns or 'MES_BI' not in df.columns:
        # Tenta converter a coluna MÊS original para data
        df['DATA_REF'] = pd.to_datetime(df['MÊS'], errors='coerce')
        df['ANO_BI'] = df['DATA_REF'].dt.year.fillna(0).astype(int).astype(str)
        meses_map = {1:'Janeiro', 2:'Fevereiro', 3:'Março', 4:'Abril', 5:'Maio', 6:'Junho',
                     7:'Julho', 8:'Agosto', 9:'Setembro', 10:'Outubro', 11:'Novembro', 12:'Dezembro'}
        df['MES_BI'] = df['DATA_REF'].dt.month.map(meses_map).fillna("N/A")

    # Garante que as colunas essenciais existam
    for c in ['STATUS', 'VALOR ANUAL', 'EMPRESA']:
        if c not in df.columns: df[c] = "N/A"

    # --- LIMPEZA DE DADOS ---
    df['ANO_BI'] = df['ANO_BI'].astype(str).str.replace('.0', '', regex=False).str.strip()
    df['STATUS'] = df['STATUS'].fillna("N/A").astype(str).str.strip().str.upper()
    
    # Tratamento de Valor (Lida com R$, pontos e vírgulas)
    def clean_val(x):
        if pd.isna(x) or x == "N/A": return 0.0
        v = str(x).replace('R$', '').replace('.', '').replace(',', '.').strip()
        return pd.to_numeric(v, errors='coerce') or 0.0

    df['VALOR_NUM'] = df['VALOR ANUAL'].apply(clean_val)

    # --- FILTROS LATERAIS (ORDENADOS E SEM ERRO) ---
    st.sidebar.title("Filtros")
    
    def get_opts(col):
        return sorted([str(x) for x in df[col].unique() if str(x) not in ['nan', '0', 'N/A', '']])

    filt_ano = st.sidebar.multiselect("Ano", options=get_opts('ANO_BI'), default=get_opts('ANO_BI'))
    filt_mes = st.sidebar.multiselect("Mês", options=get_opts('MES_BI'), default=get_opts('MES_BI'))
    filt_status = st.sidebar.multiselect("Status", options=get_opts('STATUS'), default=get_opts('STATUS'))

    # Aplicação dos Filtros
    df_f = df[(df['ANO_BI'].isin(filt_ano)) & (df['MES_BI'].isin(filt_mes)) & (df['STATUS'].isin(filt_status))]

    # --- DASHBOARD ---
    st.title("📊 BI Comercial - Labor")

    if not df_f.empty:
        # KPIs
        total_visto = df_f['VALOR_NUM'].sum()
        aprovadas = df_f[df_f['STATUS'] == 'APROVADA']['VALOR_NUM'].sum()
        apresentadas = df_f[df_f['STATUS'] == 'APRESENTADO']['VALOR_NUM'].sum()
        
        base_conv = aprovadas + apresentadas
        tx = (aprovadas / base_conv * 100) if base_conv > 0 else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Valor Filtrado", f"R$ {total_visto:,.2f}")
        c2.metric("Total Aprovado", f"R$ {aprovadas:,.2f}")
        c3.metric("% Conversão", f"{tx:.1f}%")

        st.divider()
        st.dataframe(df_f[['ANO_BI', 'MES_BI', 'EMPRESA', 'VALOR ANUAL', 'STATUS']], use_container_width=True, hide_index=True)
    else:
        st.info("Ajuste os filtros para visualizar os dados.")

else:
    st.warning("Conectando ao banco de dados...")
