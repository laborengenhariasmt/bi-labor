import streamlit as st
import pandas as pd

st.set_page_config(page_title="BI Labor - Comercial", layout="wide")

# Link do seu Sheets (CSV)
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=240265302&single=true&output=csv"

@st.cache_data(ttl=60)
def load_data():
    # Lê a planilha
    df = pd.read_csv(SHEET_URL)
    # Limpa nomes de colunas para evitar erros de espaços
    df.columns = df.columns.str.strip()
    
    # Converte o Valor Anual para número (limpando R$ e pontos)
    if 'VALOR ANUAL' in df.columns:
        if df['VALOR ANUAL'].dtype == 'object':
            df['VALOR ANUAL'] = df['VALOR ANUAL'].str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['VALOR ANUAL'] = pd.to_numeric(df['VALOR ANUAL'], errors='coerce').fillna(0)
    
    # Garante que as colunas novas do Sheets sejam tratadas como texto/número limpo
    if 'ANO_BI' in df.columns:
        df['ANO_BI'] = df['ANO_BI'].astype(str).str.replace('.0', '', regex=False)
    
    return df

try:
    df_raw = load_data()

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.title("Filtros do BI")

    # Filtro de Ano (Usando a nova coluna do Sheets)
    lista_anos = sorted(df_raw['ANO_BI'].unique().tolist(), reverse=True)
    filt_ano = st.sidebar.multiselect("Selecione o Ano", options=lista_anos, default=lista_anos)

    # Filtro de Mês (Usando a nova coluna do Sheets)
    lista_meses = df_raw['MES_BI'].unique().tolist()
    filt_mes = st.sidebar.multiselect("Selecione o Mês", options=lista_meses, default=lista_meses)

    # Filtro de Status (O que você solicitou)
    lista_status = sorted(df_raw['STATUS'].unique().tolist())
    filt_status = st.sidebar.multiselect("Filtrar por Status", options=lista_status, default=lista_status)

    # Aplicando os filtros na tela
    df_filtrado = df_raw[
        (df_raw['ANO_BI'].isin(filt_ano)) & 
        (df_raw['MES_BI'].isin(filt_mes)) &
        (df_raw['STATUS'].isin(filt_status))
    ]

    # --- DASHBOARD ---
    st.title("📊 BI Labor - Gestão Comercial")

    # Cálculos de BI
    # 1. Total que o usuário está vendo no filtro
    total_filtrado = df_filtrado['VALOR ANUAL'].sum()
    
    # 2. Total especificamente de quem está "APROVADA" (dentro do tempo filtrado)
    # Independente se o usuário tirou o status 'APROVADA' do filtro visual, calculamos para a conversão
    total_aprovado = df_filtrado[df_filtrado['STATUS'].str.contains('APROVADA', na=False, case=False)]['VALOR ANUAL'].sum()
    
    # 3. Total Apresentado (Aprovadas + Apresentadas) para a base do cálculo
    total_base = df_filtrado[df_filtrado['STATUS'].str.contains('APROVADA|APRESENTADO', na=False, case=False)]['VALOR ANUAL'].sum()
    
    conversao = (total_aprovado / total_base * 100) if total_base > 0 else 0

    # Exibição dos KPIs
    c1, c2, c3 = st.columns(3)
    c1.metric("Valor Total (Filtro)", f"R$ {total_filtrado:,.2f}")
    c2.metric("Total Aprovado", f"R$ {total_aprovado:,.2f}")
    c3.metric("% Conversão (Aprov/Apres)", f"{conversao:.1f}%")

    st.divider()
    
    # Tabela Final
    st.subheader("📋 Propostas Detalhadas")
    st.dataframe(
        df_filtrado[['MÊS', 'EMPRESA', 'CATEGORIA/PRODUTO', 'VALOR ANUAL', 'STATUS']], 
        use_container_width=True, 
        hide_index=True
    )

except Exception as e:
    st.error(f"Erro ao carregar: {e}. Verifique se adicionou as colunas ANO_BI e MES_BI no Sheets.")
