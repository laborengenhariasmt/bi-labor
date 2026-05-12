import streamlit as st
import pandas as pd
from datetime import datetime
import io

# 1. Configuração de tela
st.set_page_config(page_title="BI Labor", layout="wide")

# URLs das abas do Google Sheets (Publicadas como CSV para leitura de dados)
URL_PROPOSTAS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=240265302&single=true&output=csv"
URL_COMISSOES = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQardvk5f0S9_dB41dMjd69GGVssEdPFx-pwd9u3lVtev-08iTKhz7b5uqL6lEX1bJ5BGQSpL9cSiNd/pub?gid=1543319084&single=true&output=csv"

@st.cache_data(ttl=2)
def load_data(url):
    try:
        df = pd.read_csv(url, dtype=str)
        # Limpeza agressiva de nomes de colunas (remove espaços e padroniza em maiúsculas)
        df.columns = df.columns.str.strip().str.upper()
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

    # --- BARRA LATERAL (FILTROS COMPLETOS RESTAURADOS) ---
    st.sidebar.title("Filtros Gerais")
    def get_opts(df_target, c): 
        if c in df_target.columns:
            return sorted([str(x) for x in df_target[c].unique() if str(x) not in ['nan','0','']])
        return []
    
    f_ano = st.sidebar.multiselect("Ano", get_opts(df_p, 'ANO_BI'), default=get_opts(df_p, 'ANO_BI'))
    f_mes = st.sidebar.multiselect("Mês", get_opts(df_p, 'MES_BI'), default=get_opts(df_p, 'MES_BI'))
    f_status = st.sidebar.multiselect("Status", get_opts(df_p, 'STATUS_FINAL'), default=get_opts(df_p, 'STATUS_FINAL'))
    f_categoria = st.sidebar.multiselect("Categoria/Produto", get_opts(df_p, 'CATEGORIA/PRODUTO'), default=get_opts(df_p, 'CATEGORIA/PRODUTO'))
    
    # Filtragem Baseada nos Filtros Laterais
    df_f = df_p[
        (df_p['ANO_BI'].isin(f_ano)) & 
        (df_p['MES_BI'].isin(f_mes)) & 
        (df_p['STATUS_FINAL'].isin(f_status)) &
        (df_p['CATEGORIA/PRODUTO'].isin(f_categoria))
    ]

    # --- CÁLCULOS VISÃO GERAL ---
    total_em_tela = df_f['VALOR_NUM'].sum()
    valor_aprovado = df_f[df_f['STATUS_FINAL'].str.contains('APROVAD', na=False)]['VALOR_NUM'].sum()
    taxa_final = (valor_aprovado / total_em_tela * 100) if total_em_tela > 0 else 0

    # --- SISTEMA DE ABAS ---
    aba_geral, aba_indicadores, aba_comissoes = st.tabs(["📊 Visão Geral", "🚀 Performance", "💰 Comissões"])

    with aba_geral:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total em Tela", f"R$ {total_em_tela:,.2f}")
        c2.metric("Total Aprovado", f"R$ {valor_aprovado:,.2f}")
        c3.metric("% Conversão (Aprov/Tela)", f"{taxa_final:.1f}%")
        st.divider()
        st.dataframe(df_f[['ANO_BI', 'MES_BI', 'EMPRESA', 'CATEGORIA/PRODUTO', 'VALOR ANUAL', 'STATUS']], use_container_width=True, hide_index=True)

    with aba_indicadores:
        st.subheader("🏆 Maiores Oportunidades (Top 10)")
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
            
            # --- BLINDAGEM DE COLUNAS DE COMISSÃO ---
            col_empresa_nova = 'EMPRESA NOVA'
            if col_empresa_nova not in df_c.columns:
                # Busca por nomes parecidos caso haja erro de digitação no Sheets
                similares = [c for c in df_c.columns if 'EMPRESA' in c and 'NOVA' in c]
                col_empresa_nova = similares[0] if similares else 'EMPRESA NOVA'
                if col_empresa_nova not in df_c.columns: df_c[col_empresa_nova] = 'NÃO'

            col_valor_rec = 'VALOR RECEBIDO' if 'VALOR RECEBIDO' in df_c.columns else df_c.columns[0]
            df_c['VALOR_REC_NUM'] = df_c[col_valor_rec].apply(clean_num)
            
            col_data_rec = 'DATA DO RECEBIMENTO' if 'DATA DO RECEBIMENTO' in df_c.columns else df_c.columns[0]
            df_c['DATA_REC'] = pd.to_datetime(df_c[col_data_rec], errors='coerce')
            df_c['MES_REF_COM'] = df_c['DATA_REC'].dt.strftime('%m/%Y')
            
            # Limpeza do critério para cálculo (8% ou 4%)
            df_c['EMPRESA_NOVA_LIMPO'] = df_c[col_empresa_nova].astype(str).str.strip().str.upper()

            # Regra de Cálculo de Comissão
            def regra_comissao(row):
                perc = 0.08 if row['EMPRESA_NOVA_LIMPO'] == 'SIM' else 0.04
                return row['VALOR_REC_NUM'] * perc

            df_c['VALOR_COMISSAO'] = df_c.apply(regra_comissao, axis=1)

            # Filtro por Mês de Recebimento
            meses_com = sorted(df_c['MES_REF_COM'].dropna().unique())
            if meses_com:
                mes_pago_sel = st.selectbox("Selecione o Mês do Recebimento para Comissões", meses_com, key="sel_com_aba")
                df_mes_pago = df_c[df_c['MES_REF_COM'] == mes_pago_sel]

                total_com_mes = df_mes_pago['VALOR_COMISSAO'].sum()
                st.metric(f"Total Comissão Calculada ({mes_pago_sel})", f"R$ {total_com_mes:,.2f}")

                st.markdown("### Detalhamento Analítico de Comissões")
                # Colunas para o relatório analítico
                exibir_com = [c for c in [col_data_rec, 'EMPRESA', col_valor_rec, col_empresa_nova, 'VALOR_COMISSAO'] if c in df_mes_pago.columns or c == 'VALOR_COMISSAO']
                st.dataframe(df_mes_pago[exibir_com], use_container_width=True, hide_index=True)

                # Exportação para Excel
                col_ex1, col_ex2 = st.columns(2)
                output_com = io.BytesIO()
                with pd.ExcelWriter(output_com, engine='xlsxwriter') as writer:
                    df_mes_pago[exibir_com].to_excel(writer, index=False, sheet_name='Comissoes_Labor')
                
                col_ex1.download_button(
                    label="📥 Exportar Comissões para Excel",
                    data=output_com.getvalue(),
                    file_name=f"Comissoes_Labor_{mes_pago_sel.replace('/','_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                col_ex2.info("Para gerar PDF: Use o atalho Ctrl+P no seu navegador.")
            else:
                st.warning("Verifique se as datas na coluna 'DATA DO RECEBIMENTO' estão corretas.")
        else:
            st.warning("Aba de Comissões não detectada ou vazia.")
else:
    st.error("Erro ao carregar os dados. Verifique os links no GitHub.")
