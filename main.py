import streamlit as st
import pandas as pd

# 1. Configuração Inicial
st.set_page_config(page_title="BI Labor - Comercial", layout="wide")

# Link da sua planilha (ajustado para garantir a aba correta se necessário)
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=240265302&single=true&output=csv"

@st.cache_data(ttl=60) 
def load_data():
    df = pd.read_csv(SHEET_URL)
    
    # Limpeza de nomes de colunas
    df.columns = df.columns.str.strip()
    
    # --- TRATAMENTO DA DATA (COLUNA MÊS) ---
    col_data = 'MÊS'
    
    # Forçar conversão para data - lidando com o formato da sua planilha
    df[col_data] = pd.to_datetime(df[col_data], errors='coerce', dayfirst=True)
    
    # Se a conversão falhar e restar vazios, tentamos tratar como string
    df = df.dropna(subset=[col_data])
    
    # Criando colunas de filtro explicitamente
    df['Ano'] = df[col_data].dt.year.astype(int)
    
    meses_pt = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    df['Mes_Nome'] = df[col_data].dt.month.map(meses_pt)
    
    # --- TRATAMENTO DO VALOR ---
    if 'VALOR ANUAL' in df.columns:
        if df['VALOR ANUAL'].dtype == 'object':
            df['VALOR ANUAL'] = df['VALOR ANUAL'].str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df['VALOR ANUAL'] = pd.to_numeric(df['VALOR ANUAL'], errors='coerce').fillna(0)
        
    # Limpeza da coluna STATUS
    if 'STATUS' in df.columns:
        df['STATUS'] = df['STATUS'].fillna('NÃO INFORMADO').str.strip()

    return df

try:
    df_raw = load_data()

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.title("Filtros de BI")

    # 1. Filtro de Ano
    anos = sorted(df_raw['Ano'].unique().tolist(), reverse=True)
    filt_ano = st.sidebar.multiselect("Anos", options=anos, default=anos)

    # 2. Filtro de Mês
    ordem_meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    meses_da_base = [m for m in ordem_meses if m in df_raw['Mes_Nome'].unique()]
    filt_mes = st.sidebar.multiselect("Meses", options=meses_da_base, default=meses_da_base)

    # 3. Filtro de Status (O que você pediu)
    status_disponiveis = sorted(df_raw['STATUS'].unique().tolist())
    filt_status = st.sidebar.multiselect("Status das Propostas", options=status_disponiveis, default=status_disponiveis)

    # Aplicação dos Filtros
    df_filtrado = df_raw[
        (df_raw['Ano'].isin(filt_ano)) & 
        (df_raw['Mes_Nome'].isin(filt_mes)) &
        (df_raw['STATUS'].isin(filt_status))
    ]

    # --- DASHBOARD ---
    st.title("📊 BI Labor - Esforço Comercial")

    # Cálculos para os KPIs (Independente do filtro de status para manter a lógica de conversão)
    # Valor Aprovado: Apenas o que é 'APROVADA'
    # Valor Apresentado: Tudo que foi ofertado (Aprovada + Apresentado)
    
    val_aprovado = df_filtrado[df_filtrado['STATUS'].str.upper() == 'APROVADA']['VALOR ANUAL'].sum()
    
    # Para o cálculo de apresentado, consideramos o que o usuário está vendo no filtro
    # Mas para a sua meta de conversão, fazemos sobre a base filtrada de tempo
    val_total_visto = df_filtrado['VALOR ANUAL'].sum()
    
    # Taxa de conversão específica: Aprovadas vs (Aprovadas + Apresentadas)
    base_conversao = df_filtrado[df_filtrado['STATUS'].str.upper().isin(['APROVADA', 'APRESENTADO'])]['VALOR ANUAL'].sum()
    taxa = (val_aprovado / base_conversao * 100) if base_conversao > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Valor Filtrado (Total)", f"R$ {val_total_visto:,.2f}")
    col2.metric("Aprovado (Neste Filtro)", f"R$ {val_aprovado:,.2f}")
    col3.metric("% Conversão (Aprov/Apres)", f"{taxa:.1f}%")

    st.divider()
    
    # Tabela formatada
    st.subheader("📋 Detalhamento")
    df_view = df_filtrado.copy()
    df_view['MÊS'] = df_view['MÊS'].dt.strftime('%d/%m/%Y')
    st.dataframe(df_view[['MÊS', 'EMPRESA', 'CATEGORIA/PRODUTO', 'VALOR ANUAL', 'STATUS']], use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Erro: {e}")
