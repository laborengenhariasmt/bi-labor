import streamlit as st
import pandas as pd
from datetime import datetime
import io

st.set_page_config(page_title="BI Labor", layout="wide")

# URLs das abas do Google Sheets (Publicadas como CSV individualmente)
URL_PROPOSTAS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=240265302&single=true&output=csv"
# O usuário deve publicar a aba 'comissões' como CSV e colocar a URL aqui:
URL_COMISSOES = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=1543319084&single=true&output=csv"

@st.cache_data(ttl=2)
def load_data(url):
    try:
        df = pd.read_csv(url, dtype=str)
        df.columns = df.columns.str.strip().str.upper()
        return df.dropna(how='all')
    except Exception as e:
        return pd.DataFrame()

def clean_num(x):
    if pd.isna(x): return 0.0
    v = str(x).replace('R$', '').replace('.', '').replace(',', '.').replace(' ', '').strip()
    try: return float(v)
    except: return 0.0

# --- CARGA ---
df_propostas = load_data(https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pubhtml?gid=240265302&single=true)
df_com_raw = load_data(https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pubhtml?gid=8362953&single=true)

st.title("📊 BI Comercial & Comissões - Labor")

# Abas do Sistema
aba_geral, aba_indicadores, aba_comissoes = st.tabs(["📊 Visão Geral", "🚀 Performance", "💰 Comissões"])

# --- PROCESSAMENTO PROPOSTAS ---
if not df_propostas.empty:
    df_propostas['VALOR_NUM'] = df_propostas['VALOR ANUAL'].apply(clean_num)
    df_propostas['STATUS_FINAL'] = df_propostas['STATUS'].astype(str).str.strip().str.upper()
    
    # Datas Propostas
    df_propostas['DATA_AUX'] = pd.to_datetime(df_propostas['MÊS'], errors='coerce')
    df_propostas['ANO_BI'] = df_propostas['DATA_AUX'].dt.year.fillna(0).astype(int).astype(str)
    df_propostas['MES_BI'] = df_propostas['DATA_AUX'].dt.month.fillna(0).astype(int).astype(str)

    # Filtros Laterais
    st.sidebar.title("Filtros Gerais")
    def get_opts(df, c): return sorted([str(x) for x in df[c].unique() if str(x) not in ['nan','0','']])
    
    f_ano = st.sidebar.multiselect("Ano", get_opts(df_propostas, 'ANO_BI'), default=get_opts(df_propostas, 'ANO_BI'))
    f_mes = st.sidebar.multiselect("Mês", get_opts(df_propostas, 'MES_BI'), default=get_opts(df_propostas, 'MES_BI'))
    
    df_f = df_propostas[(df_propostas['ANO_BI'].isin(f_ano)) & (df_propostas['MES_BI'].isin(f_mes))]

    with aba_geral:
        total_em_tela = df_f['VALOR_NUM'].sum()
        valor_aprovado = df_f[df_f['STATUS_FINAL'].str.contains('APROVAD', na=False)]['VALOR_NUM'].sum()
        taxa_final = (valor_aprovado / total_em_tela * 100) if total_em_tela > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total em Tela", f"R$ {total_em_tela:,.2f}")
        c2.metric("Total Aprovado", f"R$ {valor_aprovado:,.2f}")
        c3.metric("% Conversão", f"{taxa_final:.1f}%")
        st.divider()
        st.dataframe(df_f[['ANO_BI', 'MES_BI', 'EMPRESA', 'CATEGORIA/PRODUTO', 'VALOR ANUAL', 'STATUS']], use_container_width=True)

    with aba_indicadores:
        st.subheader("Maiores Oportunidades")
        st.bar_chart(df_f.sort_values('VALOR_NUM', ascending=False).head(10), x="EMPRESA", y="VALOR_NUM")

# --- ABA COMISSÕES (O SEU PEDIDO NOVO) ---
with aba_comissoes:
    if not df_com_raw.empty:
        # 1. Tratamento de Dados
        # Espera colunas: 'EMPRESA', 'VALOR RECEBIDO', 'DATA DO RECEBIMENTO', 'EMPRESA NOVA'
        df_c = df_com_raw.copy()
        df_c['VALOR_REC_NUM'] = df_c['VALOR RECEBIDO'].apply(clean_num)
        df_c['DATA_REC'] = pd.to_datetime(df_c['DATA DO RECEBIMENTO'], errors='coerce')
        df_c['MES_REF'] = df_c['DATA_REC'].dt.strftime('%m/%Y')
        df_c['EMPRESA_NOVA'] = df_c['EMPRESA NOVA'].astype(str).str.strip().str.upper()

        # 2. Critério de Cálculo
        # Empresa Nova (SIM) = 8% | Não = 4%
        def calc_comissao(row):
            percentual = 0.08 if row['EMPRESA_NOVA'] == 'SIM' else 0.04
            return row['VALOR_REC_NUM'] * percentual

        df_c['VALOR_COMISSAO'] = df_c.apply(calc_comissao, axis=1)

        # 3. Filtro de Mês para Analítico
        meses_disponiveis = sorted(df_c['MES_REF'].dropna().unique())
        mes_sel = st.selectbox("Selecione o Mês para Pagamento", meses_disponiveis)

        df_mes_pago = df_c[df_c['MES_REF'] == mes_sel]

        # 4. Resumo Mensal
        total_mes = df_mes_pago['VALOR_COMISSAO'].sum()
        st.metric(f"Total Comissão - {mes_sel}", f"R$ {total_mes:,.2f}")

        # 5. Lista Analítica
        st.markdown("### Detalhamento Analítico")
        exibir_cols = ['DATA DO RECEBIMENTO', 'EMPRESA', 'VALOR RECEBIDO', 'EMPRESA NOVA', 'VALOR_COMISSAO']
        st.dataframe(df_mes_pago[exibir_cols], use_container_width=True, hide_index=True)

        # 6. Exportação
        col_ex1, col_ex2 = st.columns(2)
        
        # Exportar Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_mes_pago[exibir_cols].to_excel(writer, index=False, sheet_name='Comissoes')
        col_ex1.download_button(
            label="📥 Exportar para Excel",
            data=output.getvalue(),
            file_name=f"Comissoes_Labor_{mes_sel.replace('/','_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        col_ex2.info("Para salvar em PDF: Use o atalho Ctrl+P no seu navegador e selecione 'Salvar como PDF'.")
    else:
        st.warning("Aguardando dados da aba 'Comissões'. Certifique-se de que a coluna 'EMPRESA NOVA' (SIM/NÃO) e 'VALOR RECEBIDO' existem.")
