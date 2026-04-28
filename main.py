import streamlit as st
import pandas as pd

# 1. Configuração Inicial
st.set_page_config(page_title="BI Labor - Comercial", layout="wide")

# Link do seu Sheets (CSV)
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=240265302&single=true&output=csv"

@st.cache_data(ttl=60)
def load_data():
    # Lê a planilha
    df = pd.read_csv(SHEET_URL)
    
    # 1. Limpa nomes de colunas
    df.columns = df.columns.str.strip()
    
    # 2. Remove linhas que estão totalmente vazias (comum no final de planilhas)
    df = df.dropna(how='all')
    
    # 3. Tratamento do Ano (ANO_BI)
    if 'ANO_BI' in df.columns:
        # Converte para string, remove o ".0" que o Excel coloca e remove vazios
        df['ANO_BI'] = df['ANO_BI'].astype(str).str.replace('.0', '', regex=False).str.strip()
        # Filtra apenas o que parece ano (4 dígitos) e remove "nan" ou "vazio"
        df = df[df['ANO_BI'].str.contains(r'^\d{4}$', na=False)]
    else:
        # Se não achar a coluna ANO_BI, tenta extrair da coluna MÊS como plano B
        df['MÊS'] = pd.to_datetime(df['MÊS'], errors='coerce')
        df = df.dropna(subset=['MÊS'])
        df['ANO_BI'] = df['MÊS'].dt.year.astype(int).astype(str)

    # 4. Tratamento do Mês
    if 'MES_BI' not in df.columns:
        meses_pt = {1:"Janeiro", 2:"Fevereiro", 3:"Março", 4:"Abril", 5:"Maio", 6:"Junho",
                    7:"Julho", 8:"Agosto", 9:"Setembro", 10:"Outubro", 11:"Novembro", 12:"Dezembro"}
        df['MES_BI'] = pd.to_datetime(df['MÊS']).dt.month.map(meses_pt)

    # 5. Tratamento do Valor (Limpeza de moeda)
    if 'VALOR ANUAL' in df.columns:
        df['VALOR ANUAL'] = df['VALOR ANUAL'].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip()
        df['VALOR ANUAL'] = pd.to_numeric(df['VALOR ANUAL'], errors='coerce').fillna(0)
    
    return df

try:
    df_raw = load_data()

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.title("Filtros do BI")

    # Filtro de Ano
    lista_anos = sorted(df_raw['ANO_BI'].unique().tolist(), reverse=True)
    filt_ano = st.sidebar.multiselect("Selecione o Ano", options=lista_anos, default=lista_anos)

    # Filtro de Mês
    ordem_meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    meses_existentes = [m for m in ordem_meses if m in df_raw['MES_BI'].unique()]
    filt_mes = st.sidebar.multiselect("Selecione o Mês", options=meses_existentes, default=meses_existentes)

    # Filtro de Status
    lista_status = sorted(df_raw['STATUS'].fillna('NÃO INFORMADO').unique().tolist())
    filt_status = st.sidebar.multiselect("Filtrar por Status", options=lista_status, default=lista_status)

    # Aplicando os filtros
    df_filtrado = df_raw[
        (df_raw['ANO_BI'].isin(filt_ano)) & 
        (df_raw['MES_BI'].isin(filt_mes)) &
        (df_raw['STATUS'].isin(filt_status))
    ]

    # --- DASHBOARD ---
    st.title("📊 BI Labor - Comercial")

    # Cálculos
    total_aprovado = df_filtrado[df_filtrado['STATUS'].str.contains('APROVADA', na=False, case=False)]['VALOR ANUAL'].sum()
    total_apresentado = df_filtrado[df_filtrado['STATUS'].str.contains('APROVADA|APRESENTADO', na=False, case=False)]['VALOR ANUAL'].sum()
    taxa = (total_aprovado / total_apresentado * 100) if total_apresentado > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Valor Total (Filtro)", f"R$ {df_filtrado['VALOR ANUAL'].sum():,.2f}")
    col2.metric("Total Aprovado", f"R$ {total_aprovado:,.2f}")
    col3.metric("% Conversão", f"{taxa:.1f}%")

    st.divider()
    
    # Exibição da Tabela
    st.dataframe(df_filtrado[['ANO_BI', 'MES_BI', 'EMPRESA', 'VALOR ANUAL', 'STATUS']], use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Erro ao processar: {e}")
    st.info("O App está tentando ler sua planilha. Verifique se o link do Sheets ainda está ativo.")
