import streamlit as st
import pandas as pd
from datetime import datetime
import io

# 1. Configuração de tela
st.set_page_config(page_title="BI Labor", layout="wide")

# URLs INDIVIDUAIS - O segredo da estabilidade
URL_PROPOSTAS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=240265302&single=true&output=csv"
URL_COMISSOES = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=8362953&single=true&output=csv"

@st.cache_data(ttl=2)
def load_data(url):
    try:
        df = pd.read_csv(url, dtype=str)
        df.columns = df.columns.str.strip().str.upper()
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"Erro ao acessar os dados: {e}")
        return pd.DataFrame()

def clean_num(x):
    if pd.isna(x): return 0.0
    v = str(x).replace('R$', '').replace('.', '').replace(',', '.').replace(' ', '').strip()
    try: return float(v)
    except: return 0.0

# CARGA INDEPENDENTE
df_propostas_raw = load_data(URL_PROPOSTAS)
df_com_raw = load_data(URL_COMISSOES)

st.title("📊 BI Comercial & Comissões - Labor")

# Definição das Abas primeiro para organizar o fluxo
aba_geral, aba_indicadores, aba_comissoes = st.tabs(["📊 Visão Comercial", "🚀 Performance", "💰 Gestão de Comissões"])

# --- LÓGICA COMERCIAL (Abas 1 e 2) ---
if not df_propostas_raw.empty:
    df_p = df_propostas_raw.copy()
    
    # Processamento de Datas apenas para Comercial
    df_p['DATA_AUX'] = pd.to_datetime(df_p['MÊS'], errors='coerce')
    df_p['ANO_BI'] = df_p['DATA_AUX'].dt.year.fillna(0).astype(int).astype(str)
    df_p['MES_BI'] = df_p['DATA_AUX'].dt.month.fillna(0).astype(int).astype(str)
    df_p['VALOR_NUM'] = df_p['VALOR ANUAL'].apply(clean_num)
    df_p['STATUS_FINAL'] = df_p['STATUS'].astype(str).str.strip().str.upper()

    # Filtros na Sidebar (Apenas para Comercial)
    st.sidebar.title("Filtros Comercial")
    def get_opts(df, c): return sorted([str(x) for x in df[c].unique() if str(x) not in ['nan','0','']])
    
    f_ano = st.sidebar.multiselect("Ano", get_opts(df_p, 'ANO_BI'), default=get_opts(df_p, 'ANO_BI'))
    f_mes = st.sidebar.multiselect("Mês", get_opts(df_p, 'MES_BI'), default=get_opts(df_p, 'MES_BI'))
    
    df_f = df_p[(df_p['ANO_BI'].isin(f_ano)) & (df_p['MES_BI'].isin(f_mes))]

    # Conteúdo Aba Geral
    with aba_geral:
        total_tela = df_f['VALOR_NUM'].sum()
        aprovado = df_f[df_f['STATUS_FINAL'].str.contains('APROVAD', na=False)]['VALOR_NUM'].sum()
        taxa = (aprovado / total_tela * 100) if total_tela > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total em Tela", f"R$ {total_tela:,.2f}")
        c2.metric("Aprovado", f"R$ {aprovado:,.2f}")
        c3.metric("% Conversão", f"{taxa:.1f}%")
        st.dataframe(df_f, use_container_width=True, hide_index=True)

    with aba_indicadores:
        st.subheader("Performance por Empresa")
        st.bar_chart(df_f.sort_values('VALOR_NUM', ascending=False).head(10), x="EMPRESA", y="VALOR_NUM")

# --- LÓGICA DE COMISSÕES (Aba 3) - TOTALMENTE INDEPENDENTE ---
with aba_comissoes:
    if not df_com_raw.empty:
        df_c = df_com_raw.copy()
        
        # Mapeamento de colunas com limpeza profunda
        def find_col(keys, cols):
            for k in keys:
                for c in cols:
                    if k in c: return c
            return None

        # Busca as colunas mesmo que o nome mude levemente no Sheets
        c_empresa = find_col(['EMPRESA'], df_c.columns)
        c_valor = find_col(['VALOR'], df_c.columns)
        c_data = find_col(['DATA'], df_c.columns)
        c_nova = find_col(['NOVA'], df_c.columns)

        if c_valor and c_data:
            df_c['VAL_REC'] = df_c[c_valor].apply(clean_num)
            df_c['DT_REC'] = pd.to_datetime(df_c[c_data], errors='coerce')
            df_c['MES_REF'] = df_c['DT_REC'].dt.strftime('%m/%Y')
            
            # Cálculo de Comissão: Regra 8% se Nova, 4% se não
            def calc_comis(row):
                val = row['VAL_REC']
                is_nova = str(row[c_nova]).strip().upper() if c_nova else "NÃO"
                return val * 0.08 if "SIM" in is_nova else val * 0.04

            df_c['COMISSAO_RS'] = df_c.apply(calc_comis, axis=1)

            # Seletor de Mês ÚNICO para esta aba
            meses_disponiveis = sorted(df_c['MES_REF'].dropna().unique())
            if meses_disponiveis:
                escolha_mes = st.selectbox("Filtrar Mês de Recebimento", meses_disponiveis)
                df_mes_com = df_c[df_c['MES_REF'] == escolha_mes]
                
                st.metric(f"Total Comissão ({escolha_mes})", f"R$ {df_mes_com['COMISSAO_RS'].sum():,.2f}")
                st.dataframe(df_mes_com[[c_data, c_empresa, c_valor, 'COMISSAO_RS']], use_container_width=True)
                
                # Botão de Excel para fechamento
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_mes_com.to_excel(writer, index=False, sheet_name='Comissoes')
                st.download_button("📥 Baixar Fechamento (Excel)", output.getvalue(), f"Comissoes_{escolha_mes.replace('/','_')}.xlsx")
        else:
            st.error(f"Erro: Não achei as colunas de 'Valor' ou 'Data'. Colunas lidas: {list(df_c.columns)}")
    else:
        st.warning("Dados de comissão não encontrados.")
