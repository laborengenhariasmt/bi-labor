import streamlit as st
import pandas as pd

# 1. Configuração de tela
st.set_page_config(page_title="BI Labor - Comercial", layout="wide")

# Seu link do Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=240265302&single=true&output=csv"

@st.cache_data(ttl=30) # Atualiza rápido para podermos testar
def load_data():
    # Lê a planilha e força tudo a vir como TEXTO primeiro para não dar erro de cálculo
    df = pd.read_csv(SHEET_URL, dtype=str)
    
    # Limpa nomes de colunas
    df.columns = df.columns.str.strip()
    
    # Remove linhas totalmente vazias
    df = df.dropna(how='all')

    # Trata as colunas de filtro (Garante que não tenham espaços e nem .0)
    for col in ['ANO_BI', 'MES_BI', 'STATUS']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace('.0', '', regex=False).str.strip()
    
    # Trata o Valor Anual (Converte de texto para número real)
    if 'VALOR ANUAL' in df.columns:
        df['VALOR ANUAL'] = df['VALOR ANUAL'].str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['VALOR ANUAL'] = pd.to_numeric(df['VALOR ANUAL'], errors='coerce').fillna(0)
    
    return df

try:
    df_raw = load_data()

    # --- BARRA LATERAL ---
    st.sidebar.title("Filtros de BI")

    # Filtro de Ano (Puxa direto da coluna ANO_BI que você criou)
    anos_disp = sorted([a for a in df_raw['ANO_BI'].unique() if a not in ['nan', '', 'None']])
    filt_ano = st.sidebar.multiselect("Anos", options=anos_disp, default=anos_disp)

    # Filtro de Mês (Puxa direto da coluna MES_BI que você criou)
    meses_disp = [m for m in df_raw['MES_BI'].unique() if m not in ['nan', '', 'None']]
    filt_mes = st.sidebar.multiselect("Meses", options=meses_disp, default=meses_disp)

    # Filtro de Status
    status_disp = sorted([s for s in df_raw['STATUS'].unique() if s not in ['nan', '', 'None']])
    filt_status = st.sidebar.multiselect("Status", options=status_disp, default=status_disp)

    # Aplicação dos Filtros
    df_filtrado = df_raw[
        (df_raw['ANO_BI'].isin(filt_ano)) & 
        (df_raw['MES_BI'].isin(filt_mes)) &
        (df_raw['STATUS'].isin(filt_status))
    ]

    # --- DASHBOARD ---
    st.title("📊 BI Labor - Comercial")

    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados. Verifique se as colunas ANO_BI e MES_BI estão preenchidas no Sheets.")
    else:
        # Cálculos
        total_visto = df_filtrado['VALOR ANUAL'].sum()
        total_aprovado = df_filtrado[df_filtrado['STATUS'].str.upper() == 'APROVADA']['VALOR ANUAL'].sum()
        
        # Base de conversão (Aprovadas + Apresentadas)
        base_conv = df_filtrado[df_filtrado['STATUS'].str.upper().isin(['APROVADA', 'APRESENTADO'])]['VALOR ANUAL'].sum()
        taxa = (total_aprovado / base_conv * 100) if base_conv > 0 else 0

        # KPIs
        c1, c2, c3 = st.columns(3)
        c1.metric("Total em Tela", f"R$ {total_visto:,.2f}")
        c2.metric("Total Aprovado", f"R$ {total_aprovado:,.2f}")
        c3.metric("% Conversão", f"{taxa:.1f}%")

        st.divider()
        
        # Tabela
        st.subheader("📋 Dados da Planilha")
        st.dataframe(df_filtrado[['ANO_BI', 'MES_BI', 'EMPRESA', 'VALOR ANUAL', 'STATUS']], use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Erro Crítico: {e}")
