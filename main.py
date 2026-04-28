import streamlit as st
import pandas as pd

# Configuração de tela
st.set_page_config(page_title="BI Labor - Comercial", layout="wide")

# Link do seu Sheets
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKh?gid=240265302&single=true&output=csv"

@st.cache_data(ttl=10) # Atualiza quase em tempo real para testarmos
def load_data():
    # Lê a planilha forçando tudo como texto para evitar erro de float/str
    df = pd.read_csv(SHEET_URL, dtype=str)
    
    # Limpa nomes de colunas (tira espaços invisíveis)
    df.columns = df.columns.str.strip()
    
    # Remove linhas que estão totalmente vazias
    df = df.dropna(how='all')
    
    # --- LIMPEZA DAS COLUNAS DE FILTRO ---
    for col in ['ANO_BI', 'MES_BI', 'STATUS']:
        if col in df.columns:
            # Tira o ".0" que o Excel coloca em números e espaços vazios
            df[col] = df[col].astype(str).str.replace('.0', '', regex=False).str.strip()
    
    # --- TRATAMENTO DO VALOR (Onde dava o erro de <) ---
    if 'VALOR ANUAL' in df.columns:
        # Remove R$, pontos e troca vírgula por ponto
        v = df['VALOR ANUAL'].astype(str)
        v = v.str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip()
        df['VALOR ANUAL'] = pd.to_numeric(v, errors='coerce').fillna(0)
    else:
        df['VALOR ANUAL'] = 0.0

    return df

try:
    df_raw = load_data()

    # Se a coluna não existir, avisa o usuário educadamente
    if 'ANO_BI' not in df_raw.columns:
        st.error("Coluna 'ANO_BI' não encontrada. Verifique o cabeçalho da sua planilha.")
        st.stop()

    # --- BARRA LATERAL ---
    st.sidebar.title("Filtros de BI")

    # Limpa valores nulos dos filtros
    def limpar_lista(lista):
        return sorted([str(x) for x in lista if x not in ['nan', '', 'None', 'None']])

    anos = limpar_lista(df_raw['ANO_BI'].unique())
    filt_ano = st.sidebar.multiselect("Selecione o Ano", options=anos, default=anos)

    meses = limpar_lista(df_raw['MES_BI'].unique())
    filt_mes = st.sidebar.multiselect("Selecione o Mês", options=meses, default=meses)

    status = limpar_lista(df_raw['STATUS'].unique())
    filt_status = st.sidebar.multiselect("Filtrar Status", options=status, default=status)

    # Aplicação dos Filtros
    mask = (df_raw['ANO_BI'].isin(filt_ano)) & (df_raw['MES_BI'].isin(filt_mes)) & (df_raw['STATUS'].isin(filt_status))
    df_filtrado = df_raw[mask]

    # --- DASHBOARD ---
    st.title("📊 BI Labor - Comercial")

    if df_filtrado.empty:
        st.info("Selecione os filtros na lateral para visualizar os dados.")
    else:
        # KPIs
        total_tela = df_filtrado['VALOR ANUAL'].sum()
        # Filtra aprovadas ignorando maiúsculas/minúsculas
        aprovadas = df_filtrado[df_filtrado['STATUS'].str.upper() == 'APROVADA']['VALOR ANUAL'].sum()
        # Base para conversão (Aprovadas + Apresentadas)
        base = df_filtrado[df_filtrado['STATUS'].str.upper().isin(['APROVADA', 'APRESENTADO'])]['VALOR ANUAL'].sum()
        conversao = (aprovadas / base * 100) if base > 0 else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Valor Total Filtrado", f"R$ {total_tela:,.2f}")
        c2.metric("Total Aprovado", f"R$ {aprovadas:,.2f}")
        c3.metric("% Conversão (Aprov/Apres)", f"{conversao:.1f}%")

        st.divider()
        st.subheader("📋 Detalhamento das Propostas")
        
        # Mostra as colunas principais
        cols_mostrar = ['ANO_BI', 'MES_BI', 'EMPRESA', 'VALOR ANUAL', 'STATUS']
        st.dataframe(df_filtrado[cols_mostrar], use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Erro de Processamento: {e}")
    st.info("Isso pode ocorrer se a planilha estiver sendo editada agora. Aguarde 10 segundos e atualize a página.")
