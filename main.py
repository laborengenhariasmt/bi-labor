import streamlit as st
import pandas as pd

# 1. Configuração de tela
st.set_page_config(page_title="BI Labor", layout="wide")

# Link do Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=240265302&single=true&output=csv"

@st.cache_data(ttl=5)
def load_data():
    try:
        # Lê a planilha tratando tudo como texto
        df = pd.read_csv(SHEET_URL, dtype=str)
        # Limpeza de nomes de colunas
        df.columns = df.columns.str.strip().str.upper()
        # Remove linhas totalmente vazias (comum no Sheets)
        df = df.dropna(how='all')
        return df
    except Exception as e:
        st.error(f"Erro na leitura do Google Sheets: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # --- GARANTIA DE COLUNAS ---
    colunas_obrigatorias = ['ANO_BI', 'MES_BI', 'STATUS', 'VALOR ANUAL', 'EMPRESA']
    for col in colunas_obrigatorias:
        if col not in df.columns:
            df[col] = "N/A"

    # --- LIMPEZA DE DADOS (BLINDAGEM) ---
    # 1. Ano e Mês como texto puro para evitar erro de ordenação
    df['ANO_BI'] = df['ANO_BI'].fillna("N/A").astype(str).str.replace('.0', '', regex=False).str.strip()
    df['MES_BI'] = df['MES_BI'].fillna("N/A").astype(str).str.strip()
    df['STATUS'] = df['STATUS'].fillna("N/A").astype(str).str.strip().str.upper()
    
    # 2. Tratamento de Valor (Padrão Brasileiro: 1.250,00 -> 1250.00)
    def limpar_valor(valor):
        if pd.isna(valor) or valor == "N/A": return 0.0
        v = str(valor).replace('R$', '').strip()
        if not v: return 0.0
        # Se tem ponto e vírgula (ex: 1.250,00), tira o ponto e troca a vírgula
        if '.' in v and ',' in v:
            v = v.replace('.', '').replace(',', '.')
        # Se só tem vírgula (ex: 1250,00), troca por ponto
        elif ',' in v:
            v = v.replace(',', '.')
        return pd.to_numeric(v, errors='coerce') or 0.0

    df['VALOR_NUM'] = df['VALOR ANUAL'].apply(limpar_valor)

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.title("Filtros")
    
    # Função de opções que não quebra se houver tipos mistos
    def get_options(coluna):
        opcoes = [str(x) for x in df[coluna].unique() if str(x) not in ['nan', 'N/A', 'None', '']]
        return sorted(opcoes)

    sel_ano = st.sidebar.multiselect("Ano", options=get_options('ANO_BI'), default=get_options('ANO_BI'))
    sel_mes = st.sidebar.multiselect("Mês", options=get_options('MES_BI'), default=get_options('MES_BI'))
    sel_status = st.sidebar.multiselect("Status", options=get_options('STATUS'), default=get_options('STATUS'))

    # Aplicação dos Filtros
    df_filtrado = df[
        (df['ANO_BI'].isin(sel_ano)) & 
        (df['MES_BI'].isin(sel_mes)) & 
        (df['STATUS'].isin(sel_status))
    ]

    # --- DASHBOARD ---
    st.title("📊 BI Comercial - Labor")

    if df_filtrado.empty:
        st.warning("Selecione os filtros na lateral para exibir os dados.")
    else:
        # KPIs
        total_visto = df_filtrado['VALOR_NUM'].sum()
        # Filtro de Aprovadas (Garante que ignore espaços e seja maiúsculo)
        aprovadas = df_filtrado[df_filtrado['STATUS'] == 'APROVADA']['VALOR_NUM'].sum()
        
        # Base de conversão (Aprovadas + Apresentadas)
        apresentadas = df_filtrado[df_filtrado['STATUS'] == 'APRESENTADO']['VALOR_NUM'].sum()
        base_conversao = aprovadas + apresentadas
        
        conv = (aprovadas / base_conversao * 100) if base_conversao > 0 else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Total em Tela", f"R$ {total_visto:,.2f}")
        c2.metric("Aprovado", f"R$ {aprovadas:,.2f}")
        c3.metric("% Conversão (Contratado/Apres)", f"{conv:.1f}%")

        st.divider()
        
        # Exibição dos dados filtrados
        st.subheader("📋 Detalhamento das Propostas")
        st.dataframe(
            df_filtrado[['ANO_BI', 'MES_BI', 'EMPRESA', 'VALOR ANUAL', 'STATUS']], 
            use_container_width=True,
            hide_index=True
        )
else:
    st.warning("Aguardando dados do Google Sheets...")
