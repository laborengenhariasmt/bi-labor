import streamlit as st
import pandas as pd

st.set_page_config(page_title="BI Labor", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=240265302&single=true&output=csv"

@st.cache_data(ttl=2)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL, dtype=str)
        df.columns = df.columns.str.strip().str.upper()
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"Erro: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # 1. Garantia de colunas de tempo
    if 'ANO_BI' not in df.columns:
        df['DATA_AUX'] = pd.to_datetime(df['MÊS'], errors='coerce')
        df['ANO_BI'] = df['DATA_AUX'].dt.year.fillna(0).astype(int).astype(str)
        df['MES_BI'] = df['DATA_AUX'].dt.month.fillna(0).astype(int).astype(str)

    # 2. Limpeza de Valores (Crucial para o cálculo bater)
    def clean_num(x):
        if pd.isna(x): return 0.0
        v = str(x).replace('R$', '').replace('.', '').replace(',', '.').strip()
        try: return float(v)
        except: return 0.0

    df['VALOR_NUM'] = df['VALOR ANUAL'].apply(clean_num)
    
    # 3. Limpeza de Status (Removendo espaços invisíveis que causam o erro de 100%)
    df['STATUS_FINAL'] = df['STATUS'].astype(str).str.strip().str.upper()

    # --- FILTROS ---
    st.sidebar.title("Filtros")
    def get_opts(c): return sorted([str(x) for x in df[c].unique() if str(x) not in ['nan','0','']])
    
    f_ano = st.sidebar.multiselect("Ano", get_opts('ANO_BI'), default=get_opts('ANO_BI'))
    f_mes = st.sidebar.multiselect("Mês", get_opts('MES_BI'), default=get_opts('MES_BI'))
    f_status = st.sidebar.multiselect("Status", get_opts('STATUS_FINAL'), default=get_opts('STATUS_FINAL'))

    # Filtragem dos dados
    df_f = df[(df['ANO_BI'].isin(f_ano)) & (df['MES_BI'].isin(f_mes)) & (df['STATUS_FINAL'].isin(f_status))]

    # --- BLOCO DE CÁLCULO CORRIGIDO ---
    # 1. Total de tudo que está aparecendo conforme os filtros (Total em Tela)
    total_em_tela = df_f['VALOR_NUM'].sum()
        
    # 2. Total apenas das propostas APROVADAS (Total Aprovado)
    # Filtramos por quem contém "APROVAD" para evitar erros de espaço ou gênero (O/A)
    valor_aprovado = df_f[df_f['STATUS_FINAL'].str.contains('APROVAD', na=False)]['VALOR_NUM'].sum()
        
    # 3. A CONTA QUE VOCÊ PEDIU: Total Aprovado / Total em Tela
    taxa_final = (valor_aprovado / total_em_tela * 100) if total_em_tela > 0 else 0

    # --- EXIBIÇÃO NOS CARTÕES ---
    st.title("📊 BI Comercial - Labor")
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total em Tela", f"R$ {total_em_tela:,.2f}")
    col_b.metric("Total Aprovado", f"R$ {valor_aprovado:,.2f}")
    col_c.metric("% Conversão (Aprov/Tela)", f"{taxa_final:.1f}%")
    # -----------------------

    st.divider()
    st.dataframe(df_f[['ANO_BI', 'MES_BI', 'EMPRESA', 'VALOR ANUAL', 'STATUS']], use_container_width=True, hide_index=True)
else:
    st.warning("Sem dados.")
