import streamlit as st
import pandas as pd

# 1. Configuração Inicial
st.set_page_config(page_title="BI Labor - Comercial", layout="wide")

# Link da sua planilha
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=240265302&single=true&output=csv"

@st.cache_data(ttl=60) 
def load_data():
    # Lê o CSV
    df = pd.read_csv(SHEET_URL)
    
    # Limpa nomes de colunas (remove espaços invisíveis)
    df.columns = df.columns.str.strip()
    
    # --- TRATAMENTO DA COLUNA A (MÊS/DATA) ---
    col_data = 'MÊS'
    
    # Converte para data. O 'dayfirst=True' ajuda se a planilha estiver em formato brasileiro (DD/MM/AAAA)
    df[col_data] = pd.to_datetime(df[col_data], errors='coerce', dayfirst=True)
    
    # Remove linhas onde a data é inválida ou vazia
    df = df.dropna(subset=[col_data])
    
    # EXTRAÇÃO DO ANO E MÊS
    df['Ano'] = df[col_data].dt.year.astype(int)
    
    # Dicionário de meses em português
    meses_pt = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    df['Mes_Nome'] = df[col_data].dt.month.map(meses_pt)
    
    # --- TRATAMENTO DO VALOR ANUAL ---
    # Remove R$, pontos de milhar e troca vírgula por ponto se necessário
    if 'VALOR ANUAL' in df.columns:
        if df['VALOR ANUAL'].dtype == 'object':
            df['VALOR ANUAL'] = df['VALOR ANUAL'].str.replace('R$', '', regex=False)
            df['VALOR ANUAL'] = df['VALOR ANUAL'].str.replace('.', '', regex=False)
            df['VALOR ANUAL'] = df['VALOR ANUAL'].str.replace(',', '.', regex=False)
            df['VALOR ANUAL'] = pd.to_numeric(df['VALOR ANUAL'], errors='coerce')
        else:
            df['VALOR ANUAL'] = pd.to_numeric(df['VALOR ANUAL'], errors='coerce')
        df['VALOR ANUAL'] = df['VALOR ANUAL'].fillna(0)
        
    return df

try:
    df_raw = load_data()

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.title("Filtros de Análise")

    # Filtro de Ano (Agora garantido)
    lista_anos = sorted(df_raw['Ano'].unique().tolist(), reverse=True)
    anos_selecionados = st.sidebar.multiselect("Selecione o(s) Ano(s)", options=lista_anos, default=lista_anos)

    # Filtro de Mês
    ordem_meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    lista_meses_presentes = [m for m in ordem_meses if m in df_raw['Mes_Nome'].unique()]
    meses_selecionados = st.sidebar.multiselect("Selecione o(s) Mês(es)", options=lista_meses_presentes, default=lista_meses_presentes)

    # Aplicação dos Filtros
    df_filtrado = df_raw[
        (df_raw['Ano'].isin(anos_selecionados)) & 
        (df_raw['Mes_Nome'].isin(meses_selecionados))
    ]

    # --- DASHBOARD ---
    st.title("📊 BI Labor - Esforço Comercial")
    
    # Padronização do Status para o cálculo
    df_filtrado['STATUS'] = df_filtrado['STATUS'].fillna('').str.strip().str.upper()

    # KPIs
    valor_aprovado = df_filtrado[df_filtrado['STATUS'] == 'APROVADA']['VALOR ANUAL'].sum()
    valor_apresentado = df_filtrado[df_filtrado['STATUS'].isin(['APROVADA', 'APRESENTADO'])]['VALOR ANUAL'].sum()
    taxa_conversao = (valor_aprovado / valor_apresentado * 100) if valor_apresentado > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Aprovado", f"R$ {valor_aprovado:,.2f}")
    col2.metric("Total Apresentado", f"R$ {valor_apresentado:,.2f}")
    col3.metric("% Conversão (Contratado/Apresentado)", f"{taxa_conversao:.1f}%")

    st.divider()
    
    # Tabela de Dados
    st.subheader("📋 Detalhamento das Propostas")
    # Formatação para exibição
    df_display = df_filtrado.copy()
    df_display['MÊS'] = df_display['MÊS'].dt.strftime('%d/%m/%Y')
    st.dataframe(df_display[['MÊS', 'EMPRESA', 'CATEGORIA/PRODUTO', 'VALOR ANUAL', 'STATUS']], use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Ocorreu um erro ao processar os dados: {e}")
    st.info("Dica: Verifique se a coluna A da sua planilha se chama exatamente 'MÊS' e se contém datas válidas.")
