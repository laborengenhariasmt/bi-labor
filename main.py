import streamlit as st
import pandas as pd
from datetime import datetime
import io
import unicodedata

# ============================================================
# BI Labor - Comercial & Comissões
# Arquivo corrigido para leitura direta das abas do Google Sheets
# ============================================================

st.set_page_config(page_title="BI Labor", layout="wide")

# ------------------------------------------------------------
# CONFIGURAÇÃO DAS ABAS
# ------------------------------------------------------------
# ID real da planilha informada:
SHEET_ID = "127lrVy9gT6LTM6nLqPZrcTpRrvR0qNwRetH-KnIX-qo"

# GIDs das abas
# Atenção: gid=240265302 é a aba de propostas/externos conforme link enviado.
# O gid=8362953 estava no código original como Aba Comissões.
GID_PROPOSTAS = "240265302"
GID_COMISSOES = "8362953"

URL_PROPOSTAS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_PROPOSTAS}"
URL_COMISSOES = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_COMISSOES}"


# ------------------------------------------------------------
# FUNÇÕES DE APOIO
# ------------------------------------------------------------
def normalize_text(txt):
    """Remove acentos, espaços extras e padroniza nomes técnicos."""
    if pd.isna(txt):
        return ""
    txt = str(txt)
    txt = unicodedata.normalize("NFD", txt).encode("ascii", "ignore").decode("utf-8")
    txt = txt.strip().upper()
    txt = txt.replace("\n", " ")
    txt = " ".join(txt.split())
    txt = txt.replace(" ", "_").replace("/", "_").replace("-", "_")
    while "__" in txt:
        txt = txt.replace("__", "_")
    return txt


def clean_num(x):
    """Converte valores no padrão brasileiro para número."""
    if pd.isna(x):
        return 0.0

    v = str(x).strip()

    if v == "":
        return 0.0

    v = (
        v.replace("R$", "")
         .replace("%", "")
         .replace(" ", "")
         .replace("\xa0", "")
         .strip()
    )

    # Caso venha como 1.234,56
    if "," in v:
        v = v.replace(".", "").replace(",", ".")
    else:
        # Caso venha como 1234.56, mantém o ponto decimal
        v = v.replace(",", ".")

    try:
        return float(v)
    except Exception:
        return 0.0


def format_brl(valor):
    """Formata número como moeda brasileira."""
    try:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def get_opts(df_target, coluna):
    """Retorna opções limpas para filtros."""
    if coluna not in df_target.columns:
        return []

    valores = []
    for x in df_target[coluna].dropna().unique():
        sx = str(x).strip()
        if sx and sx.lower() not in ["nan", "none", "nat", "0"]:
            valores.append(sx)

    return sorted(valores)


def find_col(df, required_terms=None, optional_terms=None, forbidden_terms=None):
    """
    Encontra uma coluna por termos normalizados.
    required_terms: todos precisam existir no nome da coluna.
    optional_terms: se informado, pelo menos um precisa existir.
    forbidden_terms: nenhum pode existir.
    """
    required_terms = [normalize_text(t) for t in (required_terms or [])]
    optional_terms = [normalize_text(t) for t in (optional_terms or [])]
    forbidden_terms = [normalize_text(t) for t in (forbidden_terms or [])]

    for col in df.columns:
        c = normalize_text(col)

        if required_terms and not all(t in c for t in required_terms):
            continue

        if optional_terms and not any(t in c for t in optional_terms):
            continue

        if forbidden_terms and any(t in c for t in forbidden_terms):
            continue

        return col

    return None


@st.cache_data(ttl=60)
def load_data(url):
    """Carrega CSV publicado/exportado do Google Sheets."""
    try:
        df = pd.read_csv(url, dtype=str, header=1)

        # Remove linhas totalmente vazias
        df = df.dropna(how="all")

        # Normaliza nomes de colunas
        df.columns = [normalize_text(c) for c in df.columns]

        # Remove colunas totalmente vazias, comuns em planilhas do Google
        df = df.dropna(axis=1, how="all")

        return df

    except Exception as e:
        st.error(f"Erro ao acessar os dados da planilha: {e}")
        return pd.DataFrame()


def preparar_propostas(df_raw):
    """Prepara base de propostas para filtros, KPIs e gráficos."""
    df = df_raw.copy()

    if df.empty:
        return df

    col_mes = "MES" if "MES" in df.columns else find_col(df, required_terms=["MES"])
    col_data = find_col(df, required_terms=["DATA"])
    col_valor = (
        "VALOR_ANUAL" if "VALOR_ANUAL" in df.columns
        else find_col(df, required_terms=["VALOR"], optional_terms=["ANUAL", "TOTAL", "PROPOSTA"])
        or find_col(df, required_terms=["VALOR"])
    )
    col_status = "STATUS" if "STATUS" in df.columns else find_col(df, required_terms=["STATUS"])

    # Cria ANO_BI e MES_BI
    if "ANO_BI" not in df.columns or "MES_BI" not in df.columns:
        base_data = None

        if col_mes:
            base_data = pd.to_datetime(df[col_mes], errors="coerce", dayfirst=True)

        if (base_data is None or base_data.isna().all()) and col_data:
            base_data = pd.to_datetime(df[col_data], errors="coerce", dayfirst=True)

        if base_data is not None and not base_data.isna().all():
            df["ANO_BI"] = base_data.dt.year.fillna(0).astype(int).astype(str)
            df["MES_BI"] = base_data.dt.month.fillna(0).astype(int).astype(str).str.zfill(2)
        else:
            df["ANO_BI"] = "SEM_ANO"
            df["MES_BI"] = "SEM_MES"

    if col_valor:
        df["VALOR_NUM"] = df[col_valor].apply(clean_num)
    else:
        df["VALOR_NUM"] = 0.0

    if col_status:
        df["STATUS_FINAL"] = df[col_status].astype(str).str.strip().str.upper()
    else:
        df["STATUS_FINAL"] = "SEM_STATUS"

    return df


def preparar_comissoes(df_raw):
    """Prepara base de comissões."""
    df = df_raw.copy()

    if df.empty:
        return df, {
            "ok": False,
            "erro": "A aba Comissões está vazia ou não foi carregada.",
            "colunas": []
        }

    # Colunas prováveis
    c_data = (
        find_col(df, required_terms=["DATA", "RECEB"])
        or find_col(df, required_terms=["DATA", "PAG"])
        or find_col(df, required_terms=["DATA"])
    )

    c_valor = (
        find_col(df, required_terms=["VALOR", "RECEB"])
        or find_col(df, required_terms=["VALOR", "PAGO"])
        or find_col(df, required_terms=["VALOR"])
    )

    c_nova = (
        find_col(df, required_terms=["EMPRESA", "NOVA"])
        or find_col(df, required_terms=["NOVA"])
        or find_col(df, required_terms=["NOVO"])
    )

    c_empresa = (
        find_col(df, required_terms=["EMPRESA"], forbidden_terms=["NOVA"])
        or find_col(df, required_terms=["CLIENTE"])
        or find_col(df, required_terms=["NOME"])
    )

    if not c_data or not c_valor:
        return df, {
            "ok": False,
            "erro": "Não consegui identificar as colunas obrigatórias de DATA e VALOR na aba Comissões.",
            "colunas": list(df.columns),
            "c_data": c_data,
            "c_valor": c_valor,
            "c_nova": c_nova,
            "c_empresa": c_empresa,
        }

    df["VALOR_REC_NUM"] = df[c_valor].apply(clean_num)
    df["DATA_REC"] = pd.to_datetime(df[c_data], errors="coerce", dayfirst=True)
    df["ANO_REF"] = df["DATA_REC"].dt.year.astype("Int64").astype(str)
    df["MES_REF_NUM"] = df["DATA_REC"].dt.month.astype("Int64").astype(str).str.zfill(2)
    df["MES_REF"] = df["DATA_REC"].dt.strftime("%m/%Y")

    if c_nova:
        df["EMPRESA_NOVA_FLAG"] = (
            df[c_nova]
            .astype(str)
            .str.upper()
            .str.strip()
            .apply(lambda x: "SIM" if "SIM" in x or x in ["S", "YES", "TRUE", "1"] else "NAO")
        )
    else:
        df["EMPRESA_NOVA_FLAG"] = "NAO"

    # Regra padrão:
    # Empresa nova = 8%
    # Demais = 4%
    df["PERC_COMISSAO"] = df["EMPRESA_NOVA_FLAG"].apply(lambda x: 0.08 if x == "SIM" else 0.04)
    df["COMIS_VAL"] = df["VALOR_REC_NUM"] * df["PERC_COMISSAO"]

    # Guardar nomes encontrados para diagnóstico visual
    df.attrs["colunas_detectadas"] = {
        "data_recebimento": c_data,
        "valor_recebido": c_valor,
        "empresa_nova": c_nova,
        "empresa_cliente": c_empresa,
    }

    return df, {
        "ok": True,
        "erro": None,
        "colunas": list(df.columns),
        "c_data": c_data,
        "c_valor": c_valor,
        "c_nova": c_nova,
        "c_empresa": c_empresa,
    }


# ------------------------------------------------------------
# CARGA DOS DADOS
# ------------------------------------------------------------
df_propostas_raw = load_data(URL_PROPOSTAS)
df_com_raw = load_data(URL_COMISSOES)

st.title("📊 BI Comercial & Comissões - Labor")

with st.sidebar:
    st.title("Configuração")
    if st.button("🔄 Atualizar dados"):
        st.cache_data.clear()
        st.rerun()

    with st.expander("Diagnóstico técnico"):
        st.write("URL Propostas:")
        st.code(URL_PROPOSTAS)
        st.write("URL Comissões:")
        st.code(URL_COMISSOES)
        st.write("Colunas Propostas:")
        st.write(list(df_propostas_raw.columns))
        st.write("Colunas Comissões:")
        st.write(list(df_com_raw.columns))


# ------------------------------------------------------------
# TRATAMENTO DE BASE VAZIA
# ------------------------------------------------------------
if df_propostas_raw.empty:
    st.error("A base de Propostas não carregou. Verifique se a planilha está compartilhada/publicada corretamente.")
    st.stop()

df_p = preparar_propostas(df_propostas_raw)


# ------------------------------------------------------------
# FILTROS GERAIS
# ------------------------------------------------------------
st.sidebar.title("Filtros Gerais")

anos = get_opts(df_p, "ANO_BI")
meses = get_opts(df_p, "MES_BI")
status = get_opts(df_p, "STATUS_FINAL")

f_ano = st.sidebar.multiselect("Ano", anos, default=anos)
f_mes = st.sidebar.multiselect("Mês", meses, default=meses)
f_status = st.sidebar.multiselect("Status", status, default=status)

col_cat = "CATEGORIA_PRODUTO" if "CATEGORIA_PRODUTO" in df_p.columns else find_col(df_p, required_terms=["CATEGORIA"])
f_cat = []

if col_cat:
    categorias = get_opts(df_p, col_cat)
    f_cat = st.sidebar.multiselect("Categoria", categorias, default=categorias)

df_f = df_p.copy()

if f_ano:
    df_f = df_f[df_f["ANO_BI"].isin(f_ano)]

if f_mes:
    df_f = df_f[df_f["MES_BI"].isin(f_mes)]

if f_status:
    df_f = df_f[df_f["STATUS_FINAL"].isin(f_status)]

if col_cat and f_cat:
    df_f = df_f[df_f[col_cat].isin(f_cat)]


# ------------------------------------------------------------
# KPIs PROPOSTAS
# ------------------------------------------------------------
total_em_tela = df_f["VALOR_NUM"].sum()
valor_aprovado = df_f[df_f["STATUS_FINAL"].str.contains("APROVAD", na=False)]["VALOR_NUM"].sum()
taxa = (valor_aprovado / total_em_tela * 100) if total_em_tela > 0 else 0


aba_geral, aba_performance, aba_comissoes = st.tabs(
    ["📊 Visão Geral", "🚀 Performance", "💰 Comissões"]
)


# ------------------------------------------------------------
# ABA VISÃO GERAL
# ------------------------------------------------------------
with aba_geral:
    c1, c2, c3 = st.columns(3)
    c1.metric("Total em Tela", format_brl(total_em_tela))
    c2.metric("Aprovado", format_brl(valor_aprovado))
    c3.metric("% Conversão", f"{taxa:.1f}%")

    st.divider()
    st.subheader("Base filtrada de propostas")
    st.dataframe(df_f, use_container_width=True, hide_index=True)


# ------------------------------------------------------------
# ABA PERFORMANCE
# ------------------------------------------------------------
with aba_performance:
    st.subheader("Top 10 Empresas")

    col_empresa = (
        "EMPRESA" if "EMPRESA" in df_f.columns
        else find_col(df_f, required_terms=["EMPRESA"])
        or find_col(df_f, required_terms=["CLIENTE"])
    )

    if col_empresa and not df_f.empty:
        top_empresas = (
            df_f.groupby(col_empresa, as_index=False)["VALOR_NUM"]
            .sum()
            .sort_values("VALOR_NUM", ascending=False)
            .head(10)
        )

        st.bar_chart(top_empresas, x=col_empresa, y="VALOR_NUM")
        st.dataframe(top_empresas, use_container_width=True, hide_index=True)
    else:
        st.warning("Não encontrei coluna de empresa/cliente para montar o ranking.")


# ------------------------------------------------------------
# ABA COMISSÕES
# ------------------------------------------------------------
with aba_comissoes:
    st.subheader("Comissões")

    df_c, diag = preparar_comissoes(df_com_raw)

    if not diag["ok"]:
        st.warning(diag["erro"])
        st.write("Colunas encontradas na aba Comissões:")
        st.write(diag.get("colunas", []))
        st.info(
            "Para esta aba funcionar, a planilha precisa ter pelo menos uma coluna de data de recebimento "
            "e uma coluna de valor recebido. Exemplo: DATA DO RECEBIMENTO e VALOR RECEBIDO."
        )
    else:
        with st.expander("Diagnóstico da aba Comissões"):
            st.write("Colunas identificadas:")
            st.json({
                "Data": diag["c_data"],
                "Valor": diag["c_valor"],
                "Empresa nova": diag["c_nova"],
                "Empresa/Cliente": diag["c_empresa"],
            })

        df_c_valid = df_c.dropna(subset=["DATA_REC"]).copy()

        if df_c_valid.empty:
            st.warning("A aba Comissões carregou, mas nenhuma data de recebimento foi reconhecida.")
            st.dataframe(df_c, use_container_width=True, hide_index=True)
        else:
            anos_com = get_opts(df_c_valid, "ANO_REF")
            meses_com = sorted(df_c_valid["MES_REF"].dropna().unique())

            col1, col2 = st.columns(2)

            with col1:
                sel_ano_com = st.multiselect("Ano de pagamento", anos_com, default=anos_com)

            df_c_filtro = df_c_valid.copy()
            if sel_ano_com:
                df_c_filtro = df_c_filtro[df_c_filtro["ANO_REF"].isin(sel_ano_com)]

            meses_com_filtrados = sorted(df_c_filtro["MES_REF"].dropna().unique())

            with col2:
                sel_mes_com = st.multiselect(
                    "Mês de pagamento",
                    meses_com_filtrados,
                    default=meses_com_filtrados
                )

            if sel_mes_com:
                df_c_filtro = df_c_filtro[df_c_filtro["MES_REF"].isin(sel_mes_com)]

            total_recebido = df_c_filtro["VALOR_REC_NUM"].sum()
            total_comissao = df_c_filtro["COMIS_VAL"].sum()
            qtd_lancamentos = len(df_c_filtro)

            k1, k2, k3 = st.columns(3)
            k1.metric("Total Recebido", format_brl(total_recebido))
            k2.metric("Total Comissão", format_brl(total_comissao))
            k3.metric("Lançamentos", qtd_lancamentos)

            st.divider()

            st.subheader("Resumo por mês")
            resumo_mes = (
                df_c_filtro.groupby("MES_REF", as_index=False)
                .agg(
                    TOTAL_RECEBIDO=("VALOR_REC_NUM", "sum"),
                    TOTAL_COMISSAO=("COMIS_VAL", "sum"),
                    LANCAMENTOS=("COMIS_VAL", "count")
                )
                .sort_values("MES_REF")
            )

            st.dataframe(resumo_mes, use_container_width=True, hide_index=True)

            if not resumo_mes.empty:
                st.bar_chart(resumo_mes, x="MES_REF", y="TOTAL_COMISSAO")

            st.divider()

            st.subheader("Detalhamento das comissões")
            st.dataframe(df_c_filtro, use_container_width=True, hide_index=True)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df_c_filtro.to_excel(writer, sheet_name="Comissoes", index=False)
                resumo_mes.to_excel(writer, sheet_name="Resumo_Mes", index=False)

            st.download_button(
                "📥 Exportar Excel",
                output.getvalue(),
                file_name=f"Comissoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
