import streamlit as st
import pandas as pd

# Configuração Inicial
st.set_page_config(page_title="BI Labor - Comercial", layout="wide")

# Link da sua planilha
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=240265302&single=true&output=csv"

@st.cache_data(ttl=60) 
def load_data():
    df = pd.read_csv(SHEET_URL)
    
    # --- TRATAMENTO CRÍTICO: Limpa nomes de colunas com espaços extras ---
    df.columns = df.columns.str.strip()
    
    # Tratamento de Data
    # Se a coluna 'MÊS' não existir, ele tentará achar 'MES'
    col_data = 'MÊS' if 'MÊS' in df.columns else 'MES'
    df[col_data] = pd.to_datetime(df[col_data], errors='coerce')
    df = df.dropna(subset=[col_data]) 
    
    df['Ano'] = df[col_data].dt.year.astype(int)
    meses_pt = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    df['Mes_Nome'] = df[col_data].dt.month.map(meses_pt)
    
    # Tratamento do Valor Anual (Forçando limpeza de caracteres de moeda se houver)
    if 'VALOR ANUAL' in df.columns:
        df['VALOR ANUAL'] = df['VALOR ANUAL'].replace(r'[R\$\.\,]', '', regex=True).astype(float) / 100 if df['VALOR ANUAL'].dtype == 'object' else df['VALOR ANUAL']
        df['VALOR ANUAL'] = pd.to_numeric(df['VALOR ANUAL'], errors='coerce').fillna(0)
    else:
        st.error(f"Coluna 'VALOR ANUAL' não encontrada. Colunas disponíveis: {list(df.columns)}")
        st.stop()
        
    return df

try:
    df_raw = load_data()

    # --- BARRA LATERAL ---
    st.sidebar.title("Filtros")
    lista_anos = sorted(df_raw['Ano'].unique().tolist(), reverse=True)
    anos_selecionados = st.sidebar.multiselect("Selecione o(s) Ano(s)", options=lista_anos, default=lista_anos)

    ordem_meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    lista_meses = [m for m in ordem_meses if m in df_raw['Mes_Nome'].unique()]
    meses_selecionados = st.sidebar.multiselect("Selecione o(s) Mês(es)", options=lista_meses, default=lista_meses)

    df_filtrado = df_raw[(df_raw['Ano'].isin(anos_selecionados)) & (df_raw['Mes_Nome'].isin(meses_selecionados))]

    # --- DASHBOARD ---
    st.title("📊 BI Labor - Esforço Comercial")
    
    # Ajuste de Status (Removendo espaços e padronizando)
    df_filtrado['STATUS'] = df_filtrado['STATUS'].str.strip().str.upper()

    valor_aprovado = df_filtrado[df_filtrado['STATUS'] == 'APROVADA']['VALOR ANUAL'].sum()
    valor_apresentado = df_filtrado[df_filtrado['STATUS'].isin(['APROVADA', 'APRESENTADO'])]['VALOR ANUAL'].sum()
    taxa_conversao = (valor_aprovado / valor_apresentado * 100) if valor_apresentado > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Aprovado", f"R$ {valor_aprovado:,.2f}")
    col2.metric("Total Apresentado", f"R$ {valor_apresentado:,.2f}")
    col3.metric("% Conversão", f"{taxa_conversao:.1f}%")

    st.divider()
    st.subheader("📋 Detalhamento")
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Erro inesperado: {e}")
