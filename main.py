import streamlit as st
import pandas as pd
from datetime import datetime
import io

# 1. Configuração de tela
st.set_page_config(page_title="BI Labor", layout="wide")

# URLs CORRETAS (Sempre terminando em output=csv)
URL_PROPOSTAS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=240265302&single=true&output=csv"
URL_COMISSOES = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=1543319084&single=true&output=csv"

@st.cache_data(ttl=2)
def load_data(url):
    try:
        df = pd.read_csv(url, dtype=str)
        # Limpa espaços vazios no início e fim dos nomes das colunas e dos dados
        df.columns = df.columns.str.strip().str.upper()
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"Erro ao acessar os dados: {e}")
        return pd.DataFrame()

# --- CARGA DOS DADOS ---
# Certifique-se que o URL_COMISSOES termina com output=csv
df_propostas_raw = load_data(URL_PROPOSTAS)
df_com_raw = load_data(URL_COMISSOES)

def clean_num(x):
    if pd.isna(x): return 0.0
    v = str(x).replace('R$', '').replace('.', '').replace(',', '.').replace(' ', '').strip()
    try: return float(v)
    except: return 0.0

# --- CARGA DOS DADOS ---
df_propostas_raw = load_data(URL_PROPOSTAS)
df_com_raw = load_data(URL_COMISSOES)

st.title("📊 BI Comercial & Comissões - Labor")

# --- PROCESSAMENTO PROPOSTAS ---
if not df_propostas_raw.empty:
    df_p = df_propostas_raw.copy()
    
    # Garantia de colunas de tempo
    if 'ANO_BI' not in df_p.columns:
        df_p['DATA_AUX'] = pd.to_datetime(df_p['MÊS'], errors='coerce')
        df_p['ANO_BI'] = df_p['DATA_AUX'].dt.year.fillna(0).astype(int).astype(str)
        df_p['MES_BI'] = df_p['DATA_AUX'].dt.month.fillna(0).astype(int).astype(str)
    
    df_p['VALOR_NUM'] = df_p['VALOR ANUAL'].apply(clean_num)
    df_p['STATUS_FINAL'] = df_p['STATUS'].astype(str).str.strip().str.upper()

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.title("Filtros Gerais")
    def get_opts(df_target, c): 
        if c in df_target.columns:
            return sorted([str(x) for x in df_target[c].unique() if str(x) not in ['nan','0','']])
        return []
    
    f_ano = st.sidebar.multiselect("Ano", get_opts(df_p, 'ANO_BI'), default=get_opts(df_p, 'ANO_BI'))
    f_mes = st.sidebar.multiselect("Mês", get_opts(df_p, 'MES_BI'), default=get_opts(df_p, 'MES_BI'))
    f_status = st.sidebar.multiselect("Status", get_opts(df_p, 'STATUS_FINAL'), default=get_opts(df_p, 'STATUS_FINAL'))
    f_categoria = st.sidebar.multiselect("Categoria/Produto", get_opts(df_p, 'CATEGORIA/PRODUTO'), default=get_opts(df_p, 'CATEGORIA/PRODUTO'))
    
    df_f = df_p[
        (df_p['ANO_BI'].isin(f_ano)) & 
        (df_p['MES_BI'].isin(f_mes)) & 
        (df_p['STATUS_FINAL'].isin(f_status)) &
        (df_p['CATEGORIA/PRODUTO'].isin(f_categoria))
    ]

    # --- CÁLCULOS ---
    total_em_tela = df_f['VALOR_NUM'].sum()
    valor_aprovado = df_f[df_f['STATUS_FINAL'].str.contains('APROVAD', na=False)]['VALOR_NUM'].sum()
    taxa_final = (valor_aprovado / total_em_tela * 100) if total_em_tela > 0 else 0

    # --- ABAS ---
    aba_geral, aba_indicadores, aba_comissoes = st.tabs(["📊 Visão Geral", "🚀 Performance", "💰 Comissões"])

    with aba_geral:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total em Tela", f"R$ {total_em_tela:,.2f}")
        c2.metric("Total Aprovado", f"R$ {valor_aprovado:,.2f}")
        c3.metric("% Conversão (Aprov/Tela)", f"{taxa_final:.1f}%")
        st.divider()
        st.dataframe(df_f[['ANO_BI', 'MES_BI', 'EMPRESA', 'CATEGORIA/PRODUTO', 'VALOR ANUAL', 'STATUS']], use_container_width=True, hide_index=True)

    with aba_indicadores:
        st.subheader("🏆 Maiores Oportunidades")
        top_propostas = df_f.sort_values(by='VALOR_NUM', ascending=False).head(10)
        st.bar_chart(top_propostas, x="EMPRESA", y="VALOR_NUM", color="#004A99")

        col_ind1, col_ind2 = st.columns(2)
        with col_ind1:
            st.markdown("### 📈 Tendência Mensal")
            tendencia = df_f.groupby('MES_BI')['VALOR_NUM'].sum().reset_index()
            st.line_chart(tendencia, x="MES_BI", y="VALOR_NUM")
        with col_ind2:
            st.markdown("### 🔍 Análise de Categoria")
            if 'CATEGORIA/PRODUTO' in df_f.columns:
                cat_sum = df_f.groupby('CATEGORIA/PRODUTO')['VALOR_NUM'].sum().sort_values(ascending=False)
                st.write(cat_sum)

    with aba_comissoes:
        if not df_com_raw.empty:
            df_c = df_com_raw.copy()
            
            # --- LOCALIZADOR INTELIGENTE DE COLUNAS (BLINDAGEM) ---
            def find_col(possible_names, df_cols):
                for name in possible_names:
                    if name in df_cols: return name
                return None

            col_emp_nova = find_col(['EMPRESA NOVA', 'EMPRESA_NOVA', 'NOVA EMPRESA'], df_c.columns)
            col_val_rec = find_col(['VALOR RECEBIDO', 'VALOR_RECEBIDO', 'VALOR'], df_c.columns)
            col_data_rec = find_col(['DATA DO RECEBIMENTO', 'DATA_DO_RECEBIMENTO', 'DATA'], df_c.columns)

            if col_val_rec and col_data_rec:
                df_c['VALOR_REC_NUM'] = df_c[col_val_rec].apply(clean_num)
                df_c['DATA_REC'] = pd.to_datetime(df_c[col_data_rec], errors='coerce')
                df_c['MES_REF_COM'] = df_c['DATA_REC'].dt.strftime('%m/%Y')
                
                # Se não achar a coluna 'Empresa Nova', assume 4% (Não)
                if col_emp_nova:
                    df_c['STATUS_NOVA'] = df_c[col_emp_nova].astype(str).str.strip().str.upper()
                else:
                    df_c['STATUS_NOVA'] = 'NÃO'

                # Cálculo: SIM = 8% | NÃO = 4%
                df_c['COMISSAO'] = df_c.apply(lambda r: r['VALOR_REC_NUM'] * 0.08 if r['STATUS_NOVA'] == 'SIM' else r['VALOR_REC_NUM'] * 0.04, axis=1)

                meses_com = sorted(df_c['MES_REF_COM'].dropna().unique())
                if meses_com:
                    mes_sel = st.selectbox("Selecione o Mês do Recebimento", meses_com, key="com_sel")
                    df_mes = df_c[df_c['MES_REF_COM'] == mes_sel]
                    
                    st.metric(f"Total Comissão - {mes_sel}", f"R$ {df_mes['COMISSAO'].sum():,.2f}")
                    st.dataframe(df_mes[[col_data_rec, 'EMPRESA', col_val_rec, 'COMISSAO']], use_container_width=True, hide_index=True)
                    
                    # Exportação
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_mes.to_excel(writer, index=False, sheet_name='Comissoes')
                    st.download_button("📥 Baixar Excel", output.getvalue(), f"Comissoes_{mes_sel.replace('/','_')}.xlsx")
            else:
                st.warning("Colunas de 'Valor' ou 'Data' não encontradas na aba de Comissões.")
        else:
            st.warning("Aba de Comissões vazia.")
else:
    st.error("Falha ao carregar Propostas. Verifique o link do Google Sheets.")
