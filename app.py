import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import uuid

# Configuração da página do Streamlit (deve ser a primeira instrução)
st.set_page_config(
    page_title="Controle de Compras e Estoque - Aquático-SP",
    page_icon="🛳️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilização CSS Personalizada (Azul Escuro Corporativo e Design Limpo)
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .header-box {
        background-color: #0d233a;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 25px;
        border-left: 6px solid #4DD0E1;
        color: white;
    }
    .header-box h2 {
        color: white !important;
        margin: 0 !important;
        font-family: 'Segoe UI', sans-serif;
        font-weight: 600;
    }
    .header-box p {
        color: #b0bec5;
        margin: 5px 0 0 0 !important;
        font-size: 14px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 24px;
    }
    /* Estilos das tabelas customizadas por Frota */
    .table-title-gerais { background-color: #f1f3f4; border-left: 4px solid #212121; padding: 6px 12px; font-weight: bold; color: #212121; margin-top: 15px; }
    .table-title-borore { background-color: #e8f0fe; border-left: 4px solid #0d47a1; padding: 6px 12px; font-weight: bold; color: #0d47a1; margin-top: 15px; }
    .table-title-santoamaro { background-color: #fff3e0; border-left: 4px solid #e65100; padding: 6px 12px; font-weight: bold; color: #e65100; margin-top: 15px; }
    .table-title-pedreira { background-color: #e0f2f1; border-left: 4px solid #004d40; padding: 6px 12px; font-weight: bold; color: #004d40; margin-top: 15px; }
    </style>
""", unsafe_allow_html=True)

# Banner do Cabeçalho
st.markdown("""
    <div class="header-box">
        <h2>🛳️ CONTROLE DE COMPRAS E ESTOQUE - AQUÁTICO-SP</h2>
        <p>Sistema de Gestão de Ativos e Manutenção Hidroviária (Sincronização Ativa em Nuvem)</p>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 1. CONEXÃO COM O GOOGLE SHEETS
# ==========================================
@st.cache_resource
def obter_conexao_sheets():
    escopos = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # No Streamlit Cloud, as credenciais ficam guardadas de forma segura em st.secrets
    info_credenciais = json.loads(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(info_credenciais, scopes=escopos)
    client = gspread.authorize(creds)
    return client.open("Controle_Estoque_Naval").sheet1

try:
    aba_planilha = obter_conexao_sheets()
except Exception as e:
    st.error(f"❌ Erro de Conexão com o Google Sheets: {e}")
    st.stop()

# ==========================================
# 2. CARREGAMENTO E TRATAMENTO DOS DADOS
# ==========================================
def carregar_dados():
    try:
        dados = aba_planilha.get_all_records()
        if len(dados) == 0:
            return pd.DataFrame()
        df = pd.DataFrame(dados)
        colunas = list(df.columns)
        
        # Mapeamento robusto dos cabeçalhos
        col_id = next((n for n in ["ID", "Id", "id"] if n in colunas), colunas[0])
        col_status = next((n for n in ["Status", "Status de Compra", "Status da Compra"] if n in colunas), colunas[7])
        col_embarcacao = next((n for n in ["Embarcação", "Embarcacao", "Frota"] if n in colunas), colunas[1])
        col_item = next((n for n in ["Item/Peça", "Item", "Peça"] if n in colunas), colunas[3])
        
        # Padroniza os tipos de dados para evitar erros de serialização (int64)
        df[col_id] = df[col_id].astype(str)
        df[col_status] = df[col_status].astype(str)
        df[col_embarcacao] = df[col_embarcacao].astype(str)
        df[col_item] = df[col_item].astype(str)
        
        # Garante ordenação alfabética pelo nome do item
        df = df.sort_values(by=col_item, ascending=True)
        return df, col_id, col_status, col_embarcacao, col_item
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame(), None, None, None, None

df_dados, col_id, col_status, col_embarcacao, col_item = carregar_dados()

# ==========================================
# 3. GERENCIAMENTO DE ESTADO (SESSION STATE)
# ==========================================
# Permite guardar na memória qual item está selecionado para edição
if "item_selecionado" not in st.session_state:
    st.session_state.item_selecionado = None

# ==========================================
# 4. FORMULÁRIO DE CADASTRO E EDIÇÃO
# ==========================================
st.markdown("### 📝 Painel de Cadastro e Modificação")

# Se há um item selecionado na memória, preenchemos os campos com os valores dele
item_dados = {}
if st.session_state.item_selecionado is not None and not df_dados.empty:
    filtro = df_dados[df_dados[col_id] == st.session_state.item_selecionado]
    if not filtro.empty:
        item_dados = filtro.iloc[0].to_dict()

# Formulário estruturado em colunas
col1, col2 = st.columns(2)

with col1:
    v_id = st.text_input("Nº do Item (ID) - Gerado Automaticamente", value=item_dados.get(col_id, ""), disabled=True)
    
    opcoes_aplicacao = ["Gerais / Almoxarifado", "Bororé", "Santo Amaro", "Pedreira"]
    idx_aplicacao = opcoes_aplicacao.index(item_dados.get(col_embarcacao)) if item_dados.get(col_embarcacao) in opcoes_aplicacao else 0
    v_aplicacao = st.selectbox("Aplicação / Frota", options=opcoes_aplicacao, index=idx_aplicacao)
    
    v_item = st.text_input("Item / Peça", value=item_dados.get(col_item, ""))
    v_especificacao = st.text_input("Especificação Técnica (Dados, modelo, part number)", value=item_dados.get("Especificação", ""))

with col2:
    opcoes_status = ["Necessidade de Compra", "Mapeando Preço", "Aprovado (Aguardando Entrega)", "Recebido (Em Estoque)"]
    idx_status = opcoes_status.index(item_dados.get(col_status)) if item_dados.get(col_status) in opcoes_status else 0
    v_status = st.selectbox("Status de Compra", options=opcoes_status, index=idx_status)
    
    v_qtd = st.number_input("Quantidade", min_value=1, value=int(item_dados.get("Quantidade", 1)))
    v_fornecedor = st.text_input("Fornecedor", value=item_dados.get("Fornecedor", ""))
    v_doc = st.text_input("Nota Fiscal / Ref / Link", value=item_dados.get("Nota Fiscal / Ref", item_dados.get("Nota fiscal / Ref / Link", "")))

v_obs = st.text_area("Observações Complementares", value=item_dados.get("Observação", ""))

# Botões de Ação do Painel
bt_col1, bt_col2, bt_col3, bt_col4 = st.columns(4)

with bt_col1:
    if st.button("💾 Salvar Alterações", use_container_width=True, type="primary"):
        if not v_id:
            st.warning("⚠️ Selecione um item na lista abaixo primeiro para editá-lo.")
        else:
            # Atualização no Google Sheets
            try:
                dados_completos = aba_planilha.get_all_records()
                df_temp = pd.DataFrame(dados_completos)
                colunas_disponiveis = list(df_temp.columns)
                idx_linha = df_temp[df_temp[col_id] == v_id].index[0] + 2
                
                for pos, col in enumerate(colunas_disponiveis, 1):
                    if col in ["Embarcação", "Embarcacao"]: aba_planilha.update_cell(idx_linha, pos, v_aplicacao)
                    elif col in ["Item/Peça", "Item"]: aba_planilha.update_cell(idx_linha, pos, v_item)
                    elif col in ["Especificação", "Especificação Técnica"]: aba_planilha.update_cell(idx_linha, pos, v_especificacao)
                    elif col in ["Quantidade", "Qtd"]: aba_planilha.update_cell(idx_linha, pos, int(v_qtd))
                    elif col in ["Status", "Status de Compra"]: aba_planilha.update_cell(idx_linha, pos, v_status)
                    elif col in ["Fornecedor"]: aba_planilha.update_cell(idx_linha, pos, v_fornecedor)
                    elif col in ["Nota Fiscal / Ref", "Doc / Ref", "Nota fiscal / Ref / Link"]: aba_planilha.update_cell(idx_linha, pos, v_doc)
                    elif col in ["Observação", "Observações"]: aba_planilha.update_cell(idx_linha, pos, v_obs)
                
                st.success(f"💾 Alterações salvas com sucesso para o ID: {v_id}!")
                st.session_state.item_selecionado = None
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar alterações: {e}")

with bt_col2:
    if st.button("➕ Inserir como Novo", use_container_width=True):
        if not v_item.strip():
            st.error("⚠️ O campo 'Item/Peça' é obrigatório!")
        else:
            try:
                novo_id = str(uuid.uuid4())[:8]
                colunas_disponiveis = list(pd.DataFrame(aba_planilha.get_all_records()).columns)
                nova_linha_dict = {c: "" for c in colunas_disponiveis}
                
                for c in colunas_disponiveis:
                    if c in ["ID", "Id", "id"]: nova_linha_dict[c] = novo_id
                    elif c in ["Embarcação", "Embarcacao"]: nova_linha_dict[c] = v_aplicacao
                    elif c in ["Item/Peça", "Item"]: nova_linha_dict[c] = v_item
                    elif c in ["Especificação", "Especificação Técnica"]: nova_linha_dict[c] = v_especificacao
                    elif c in ["Quantidade", "Qtd"]: nova_linha_dict[c] = int(v_qtd)
                    elif c in ["Status", "Status de Compra"]: nova_linha_dict[c] = v_status
                    elif c in ["Fornecedor"]: nova_linha_dict[c] = v_fornecedor
                    elif c in ["Nota Fiscal / Ref", "Doc / Ref", "Nota fiscal / Ref / Link"]: nova_linha_dict[c] = v_doc
                    elif c in ["Observação", "Observações"]: nova_linha_dict[c] = v_obs
                    else: nova_linha_dict[c] = "-"
                
                aba_planilha.append_row(list(nova_linha_dict.values()))
                st.success(f"🔹 Item '{v_item}' cadastrado sob o ID: {novo_id}!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao cadastrar: {e}")

with bt_col3:
    if st.button("🗑️ Apagar Item Definitivamente", use_container_width=True):
        if not v_id:
            st.warning("⚠️ Selecione um item na lista abaixo para excluir.")
        else:
            try:
                dados_completos = aba_planilha.get_all_records()
                df_temp = pd.DataFrame(dados_completos)
                idx_linha = df_temp[df_temp[col_id] == v_id].index[0] + 2
                aba_planilha.delete_rows(int(idx_linha))
                st.success(f"🗑️ Item ID '{v_id}' removido definitivamente!")
                st.session_state.item_selecionado = None
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao deletar: {e}")

with bt_col4:
    if st.button("🧹 Limpar Seleção", use_container_width=True):
        st.session_state.item_selecionado = None
        st.rerun()

st.markdown("---")

# ==========================================
# 5. LISTAGEM SEGMENTADA EM ABAS DO STREAMLIT
# ==========================================
st.markdown("### 📋 Status de Compras e Estoque (Dividido por Frotas)")

# Mapeamento das Abas Solicitadas
status_map = [
    ("Necessidade de Compra", "🔴 Pedido de compra", "#FFEBEE", "#d32f2f"),
    ("Mapeando Preço", "🟡 Em andamento", "#FFFDE7", "#f57f17"),
    ("Aprovado (Aguardando Entrega)", "🔵 Aprovado", "#E0F7FA", "#0288d1"),
    ("Recebido (Em Estoque)", "🟢 Recebido", "#E8F5E9", "#388e3c")
]

embarcacoes_map = [
    ("Gerais / Almoxarifado", "table-title-gerais"),
    ("Bororé", "table-title-borore"),
    ("Santo Amaro", "table-title-santoamaro"),
    ("Pedreira", "table-title-pedreira")
]

# Cria as Abas Nativas do Streamlit na interface
abas_streamlit = st.tabs([label for _, label, _, _ in status_map])

for idx_status, (status_real, _, bg_color, text_color) in enumerate(status_map):
    with abas_streamlit[idx_status]:
        # Filtra os dados pertencentes ao status desta aba específica
        df_status = df_dados[df_dados[col_status] == status_real] if not df_dados.empty else pd.DataFrame()
        
        if df_status.empty:
            st.info("Nenhum item cadastrado com este status.")
            continue
            
        # Para cada aplicação/frota, exibe um bloco visual isolado
        for nome_emb, classe_css in embarcacoes_map:
            df_final = df_status[df_status[col_embarcacao] == nome_emb]
            
            if not df_final.empty:
                # Título da sub-tabela estilizado
                st.markdown(f'<div class="{classe_css}">&nbsp;🛳️ {nome_emb.upper()}</div>', unsafe_allow_html=True)
                
                # Exibição interativa e responsiva do Streamlit
                # Criamos um botão interativo para carregar cada item para edição
                for _, row in df_final.iterrows():
                    # Formatação estilosa por linha de dados
                    c_id = row[col_id]
                    c_item = row[col_item]
                    c_spec = row.get("Especificação", "-")
                    c_qtd = row.get("Quantidade", 1)
                    c_forn = row.get("Fornecedor", "-")
                    c_doc = row.get("Nota Fiscal / Ref", row.get("Nota fiscal / Ref / Link", "-"))
                    
                    lbl_linha = f"**ID:** `{c_id}` | **Item:** **{c_item}** | **Qtd:** {c_qtd} | **Especificação:** {c_spec} | **Fornecedor:** {c_forn} | **Link/Doc:** {c_doc}"
                    
                    col_linha_txt, col_linha_btn = st.columns([8.5, 1.5])
                    with col_linha_txt:
                        st.markdown(lbl_linha)
                    with col_linha_btn:
                        # Botão que joga o ID selecionado na memória e recarrega para edição
                        if st.button("📝 Editar", key=f"btn_edit_{c_id}", use_container_width=True):
                            st.session_state.item_selecionado = c_id
                            st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)
