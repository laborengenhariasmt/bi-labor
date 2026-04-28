import streamlit as st
import pandas as pd

# 1. Configuração Inicial
st.set_page_config(page_title="BI Labor - Comercial", layout="wide")

# Link que você me enviou
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=240265302&single=true&output=csv"

@st.cache_data(ttl=600) # Atualiza os dados a cada 10 minutos
def load_data():
    # Lê o CSV diretamente do link do Google Sheets
    df = pd.read_csv(SHEET_URL)
    
    # Tratamento de Data
    df['MÊS'] = pd.to_datetime(df['MÊS'], errors='coerce')
    df = df.dropna(subset=['MÊS']) # Remove linhas sem data
    
    # Criar colunas de Ano e Mês (Nome)
    df['Ano'] = df['MÊS'].dt.year.astype(int)
    # Dicionário para meses em português
    meses_pt = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    df['Mes_Nome'] = df['MÊS'].dt.month.map(meses_pt)
    
    # Tratamento de Valores Numéricos
    df['VALOR ANUAL'] = pd.to_numeric(df['VALOR ANUAL'], errors='coerce').fillna(0)
    
    return df

# Execução do Carregamento
try:
    df_raw = load_data()

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.image("https://www.google.com/s2/favicons?sz=64&domain=streamlit.io") # Espaço para logo
    st.sidebar.title("Filtros")

    # Filtro de Ano
    lista_anos = sorted(df_raw['Ano'].unique().tolist(), reverse=True)
    anos_selecionados = st.sidebar.multiselect("Selecione o(s) Ano(s)", options=lista_anos, default=lista_anos[0])

    # Filtro de Mês
    ordem_meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    lista_meses = [m for m in ordem_meses if m in df_raw['Mes_Nome'].unique()]
    meses_selecionados = st.sidebar.multiselect("Selecione o(s) Mês(es)", options=lista_meses, default=lista_meses)

    # Aplicar Filtros ao DataFrame
    df_filtrado = df_raw[
        (df_raw['Ano'].isin(anos_selecionados)) & 
        (df_raw['Mes_Nome'].isin(meses_selecionados))
    ]

    # --- DASHBOARD PRINCIPAL ---
    st.title("📊 BI Labor - Esforço Comercial")
    st.markdown(f"Exibindo dados de: **{', '.join(map(str, anos_selecionados))}**")

    # Cálculos para os Cartões (KPIs)
    valor_aprovado = df_filtrado[df_filtrado['STATUS'] == 'APROVADA']['VALOR ANUAL'].sum()
    valor_apresentado = df_filtrado[df_filtrado['STATUS'].isin(['APROVADA', 'APRESENTADO'])]['VALOR ANUAL'].sum()
    
    # Conversão
    taxa_conversao = (valor_aprovado / valor_apresentado * 100) if valor_apresentado > 0 else 0

    # Exibição dos Cartões
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Aprovado", f"R$ {valor_aprovado:,.2f}")
    col2.metric("Total Apresentado", f"R$ {valor_apresentado:,.2f}")
    col3.metric("% Conversão", f"{taxa_conversao:.1f}%")

    st.divider()

    # Detalhamento
    st.subheader("📋 Lista de Propostas Filtradas")
    st.dataframe(
        df_filtrado[['MÊS', 'EMPRESA', 'CATEGORIA/PRODUTO', 'VALOR ANUAL', 'STATUS']],
        use_container_width=True,
        hide_index=True
    )

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.info("Verifique se a planilha do Google Sheets ainda está publicada como CSV.")
