import streamlit as st
import pandas as pd
from datetime import datetime
import io
import unicodedata

# 1. Configuração de tela
st.set_page_config(page_title="BI Labor", layout="wide")

# URLs INDIVIDUAIS (Mantenha assim, é o jeito mais seguro)
URL_PROPOSTAS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=240265302&single=true&output=csv"
URL_COMISSOES = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=8362953&single=true&output=csv"

def normalize_text(txt):
    """Remove acentos, espaços extras e padroniza para busca técnica"""
    if not isinstance(txt, str): return str(txt)
    txt = unicodedata.normalize('NFD', txt).encode('ascii', 'ignore').decode('utf-8')
    return txt.strip().upper().replace(" ", "_").replace("/", "_")

@st.cache_data(ttl=2)
def load_data(url):
    try:
        df = pd.read_csv(url, dtype=str)
        # Limpa os nomes das colunas de forma profunda
        df.columns = [normalize_text(c) for c in df.columns]
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"Erro ao acessar os dados: {e}")
        return pd.DataFrame()

def clean_num(x):
    if pd.isna(x): return 0.0
    v = str(x).replace('R$', '').replace('.', '').replace(',', '.').replace(' ', '').strip()
    try: return float(v)
    except: return 0.0

# --- CARGA DOS DADOS ---
df_propostas_raw = load_data(URL_PROPOSTAS)
df_com_raw = load_data(URL_COMISSOES)

st.title("📊 BI Comercial & Comissões - Labor")

# --- PROPOSTAS ---
if not df_propostas_raw.empty:
    df_p = df_propostas_raw.copy()
    
    # Busca nomes normalizados
    col_mes = "MES" if "MES" in df_p.columns else df_p.columns[0]
    
    if 'ANO_BI' not in df_p.columns:
        df_p['DATA_AUX'] = pd.to_datetime(df_p[col_mes], errors='coerce')
        df_p['ANO_BI'] = df_p['DATA_AUX'].dt.year.fillna(0).astype(int).astype(str)
        df_p['MES_BI'] = df_p['DATA_AUX'].dt.month.fillna(0).astype(int).astype(str)
    
    # VALOR_ANUAL normalizado vira VALOR_ANUAL
    col_valor = "VALOR_ANUAL" if "VALOR_ANUAL" in df_p.columns else "VALOR"
    df_p['VALOR_NUM'] = df_p[col_valor].apply(clean_num)
    df_p['STATUS_FINAL'] = df_p['STATUS'].astype(str).str.strip().str.upper()

    st.sidebar.title("Filtros Gerais")
    def get_opts(df_target, c): 
        if c in df_target.columns:
            return sorted([str(x) for x in df_target[c].unique() if str(x) not in ['nan','0','']])
        return []
    
    f_ano = st.sidebar.multiselect("Ano", get_opts(df_p, 'ANO_BI'), default=get_opts(df_p, 'ANO_BI'))
    f_mes = st.sidebar.multiselect("Mês", get_opts(df_p, 'MES_BI'), default=get_opts(df_p, 'MES_BI'))
    f_status = st.sidebar.multiselect("Status", get_opts(df_p, 'STATUS_FINAL'), default=get_opts(df_p, 'STATUS_FINAL'))
    
    col_cat = "CATEGORIA_PRODUTO" if "CATEGORIA_PRODUTO" in df_p.columns else None
    if col_cat:
        f_cat = st.sidebar.multiselect("Categoria", get_opts(df_p, col_cat), default=get_opts(df_p, col_cat))
    
    df_f = df_p[(df_p['ANO_BI'].isin(f_ano)) & (df_p['MES_BI'].isin(f_mes)) & (df_p['STATUS_FINAL'].isin(f_status))]
    if col_cat: df_f = df_f[df_f[col_cat].isin(f_cat)]

    total_em_tela = df_f['VALOR_NUM'].sum()
    valor_aprovado = df_f[df_f['STATUS_FINAL'].str.contains('APROVAD', na=False)]['VALOR_NUM'].sum()
    taxa = (valor_aprovado / total_em_tela * 100) if total_em_tela > 0 else 0

    aba_geral, aba_performance, aba_comissoes = st.tabs(["📊 Visão Geral", "🚀 Performance", "💰 Comissões"])

    with aba_geral:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total em Tela", f"R$ {total_em_tela:,.2f}")
        c2.metric("Aprovado", f"R$ {valor_aprovado:,.2f}")
        c3.metric("% Conversão", f"{taxa:.1f}%")
        st.divider()
        st.dataframe(df_f, use_container_width=True, hide_index=True)

    with aba_performance:
        st.subheader("Top 10 Empresas")
        st.bar_chart(df_f.sort_values('VALOR_NUM', ascending=False).head(10), x="EMPRESA", y="VALOR_NUM")

    with aba_comissoes:
        if not df_com_raw.empty:
            df_c = df_com_raw.copy()
            
            # Busca colunas normalizadas: DATA_DO_RECEBIMENTO vira DATA_DO_RECEBIMENTO
            c_data = next((c for c in df_c.columns if "DATA" in c and "RECEB" in c), None)
            c_valor = next((c for c in df_c.columns if "VALOR" in c and "RECEB" in c), None)
            c_nova = next((c for c in df_c.columns if "EMPRESA" in c and "NOVA" in c), None)

            if c_data and c_valor:
                df_c['VALOR_REC_NUM'] = df_c[c_valor].apply(clean_num)
                df_c['DATA_REC'] = pd.to_datetime(df_c[c_data], errors='coerce')
                df_c['MES_REF'] = df_c['DATA_REC'].dt.strftime('%m/%Y')
                
                status_nova = df_c[c_nova].str.upper().str.strip() if c_nova else "NAO"
                df_c['COMIS_VAL'] = df_c.apply(lambda r: r['VALOR_REC_NUM'] * 0.08 if "SIM" in str(r[c_nova]).upper() else r['VALOR_REC_NUM'] * 0.04, axis=1)

                meses = sorted(df_c['MES_REF'].dropna().unique())
                if meses:
                    sel_mes_com = st.selectbox("Mês de Pagamento", meses)
                    df_mes_com = df_c[df_c['MES_REF'] == sel_mes_com]
                    st.metric(f"Total Comissões {sel_mes_com}", f"R$ {df_mes_com['COMIS_VAL'].sum():,.2f}")
                    st.dataframe(df_mes_com, use_container_width=True)
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_mes_com.to_excel(writer, index=False)
                    st.download_button("📥 Exportar Excel", output.getvalue(), f"Comissoes_{sel_mes_com}.xlsx")
            else:
                st.warning(f"Colunas não identificadas. Encontradas: {list(df_c.columns)}")
        else:
            st.warning("Aba Comissões sem dados.")
