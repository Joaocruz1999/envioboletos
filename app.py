import pandas as pd
import streamlit as st

from utils.config import get_access_password, get_senders, get_smtp_config, init_session_state
from utils.data_ops import (
    build_match_dataframe,
    cleanup_temp_dir,
    get_upload_signature,
    load_clients_dataframe,
    save_uploaded_pdfs,
)
from utils.mailer import send_emails

DEFAULT_SUBJECT_TEMPLATE = "Boleto bancário - {razao_social}"
DEFAULT_BODY_TEMPLATE = (
    "Olá,\n\n"
    "Segue anexo o boleto referente à empresa {razao_social} (CNPJ: {cnpj}).\n\n"
    "Se tiver dúvidas, responda este e-mail.\n\n"
    "Atenciosamente."
)


def render_login() -> None:
    st.title("Envio de Boletos")
    st.subheader("Acesso restrito")

    with st.form("login_form"):
        password_input = st.text_input("Senha de acesso", type="password")
        submitted = st.form_submit_button("Entrar", use_container_width=True)

    if submitted:
        if not get_access_password():
            st.error("Senha de acesso não configurada em st.secrets.")
            return

        if password_input == get_access_password():
            st.session_state.authenticated = True
            st.success("Login realizado com sucesso.")
            st.rerun()
        else:
            st.error("Senha inválida.")
def render_sidebar_sender_selector(senders: dict) -> str:
    st.sidebar.header("Configurações de envio")
    options = list(senders.keys())
    selected_sender_key = st.sidebar.selectbox(
        "E-mail Remetente",
        options=options,
        format_func=lambda key: f"{senders[key]['display_name']} ({senders[key]['email']})",
    )
    return selected_sender_key


def render_email_templates() -> tuple[str, str]:
    st.sidebar.subheader("Modelo de e-mail")
    st.sidebar.caption("Placeholders disponíveis: {nome}, {razao_social}, {cnpj}")
    subject_template = st.sidebar.text_input(
        "Assunto",
        value=DEFAULT_SUBJECT_TEMPLATE,
    )
    body_template = st.sidebar.text_area(
        "Corpo do e-mail",
        value=DEFAULT_BODY_TEMPLATE,
        height=220,
    )
    return subject_template, body_template


def main() -> None:
    st.set_page_config(page_title="Envio de Boletos", layout="wide")
    init_session_state()

    if not st.session_state.authenticated:
        render_login()
        return

    senders = get_senders()
    if not senders:
        st.error("Nenhum remetente válido encontrado em st.secrets['senders'].")
        return

    selected_sender_key = render_sidebar_sender_selector(senders)
    sender_cfg = senders[selected_sender_key]
    smtp_host, smtp_port = get_smtp_config()
    subject_template, body_template = render_email_templates()

    st.title("Painel de Envio de Boletos")
    st.caption("Faça upload da planilha e dos PDFs para cruzar e disparar os e-mails.")

    excel_file = st.file_uploader(
        "Planilha principal (Excel)",
        type=["xlsx", "xls"],
        help="Colunas esperadas: Nome, Razao Social, CNPJ, Email",
    )
    uploaded_pdfs = st.file_uploader(
        "Boletos em PDF",
        type=["pdf"],
        accept_multiple_files=True,
        help="Padrão esperado: PREFIXO_00111222000199.pdf (ex.: boleto_, TFF_, CRPS_)",
    )

    process_button = st.button("Processar uploads", type="primary", use_container_width=True)
    upload_signature = get_upload_signature(excel_file, uploaded_pdfs)

    if process_button:
        if not excel_file:
            st.warning("Envie a planilha principal para continuar.")
            return
        if not uploaded_pdfs:
            st.warning("Envie ao menos um boleto em PDF para continuar.")
            return

        cleanup_temp_dir(st.session_state.temp_dir)
        st.session_state.temp_dir = None
        st.session_state.pdf_map = {}
        st.session_state.match_df = pd.DataFrame()

        try:
            clients_df = load_clients_dataframe(excel_file)
            temp_dir, pdf_map, invalid_files, duplicated_cnpjs = save_uploaded_pdfs(uploaded_pdfs)
            match_df = build_match_dataframe(clients_df, pdf_map)

            st.session_state.temp_dir = temp_dir
            st.session_state.pdf_map = pdf_map
            st.session_state.match_df = match_df
            st.session_state.last_upload_signature = upload_signature

            if invalid_files:
                st.warning(
                    "Arquivos ignorados por nome inválido: "
                    + ", ".join(sorted(invalid_files))
                )
            if duplicated_cnpjs:
                st.warning(
                    "PDFs duplicados por CNPJ ignorados: "
                    + ", ".join(sorted(set(duplicated_cnpjs)))
                )
            if match_df.empty:
                st.info("Nenhum cliente com boleto correspondente neste upload.")

        except Exception as exc:
            st.error(f"Erro ao processar uploads: {exc}")

    if not st.session_state.match_df.empty:
        if st.session_state.last_upload_signature != upload_signature:
            st.info("Uploads alterados. Clique em 'Processar uploads' para atualizar o cruzamento.")

        st.subheader("Clientes com boletos correspondentes")
        edited_df = st.data_editor(
            st.session_state.match_df,
            hide_index=True,
            use_container_width=True,
            key="boletos_editor",
            disabled=["Nome", "Razao Social", "CNPJ", "Email", "ArquivoPDF", "Status"],
            column_config={
                "Enviar": st.column_config.CheckboxColumn("Enviar"),
                "Cópia": st.column_config.TextColumn(
                    "Cópia (CC)",
                    help="Separe múltiplos e-mails com ; ou ,",
                ),
            },
        )
        st.session_state.match_df = edited_df

        if st.button("Disparar E-mails", use_container_width=True):
            if not st.session_state.pdf_map:
                st.error("Nenhum PDF temporário encontrado. Refaça o upload e o processamento.")
                return
            if not subject_template.strip():
                st.error("Preencha o assunto do e-mail.")
                return
            if not body_template.strip():
                st.error("Preencha o corpo do e-mail.")
                return

            # Validação antecipada dos placeholders para evitar erro durante o lote.
            validation_values = {"nome": "Cliente", "razao_social": "Empresa Exemplo", "cnpj": "00111222000199"}
            try:
                subject_template.format(**validation_values)
                body_template.format(**validation_values)
            except KeyError as exc:
                st.error(
                    "Placeholder inválido no assunto/corpo: "
                    f"{exc}. Use apenas {{nome}}, {{razao_social}} e {{cnpj}}."
                )
                return

            try:
                sent_df = send_emails(
                    df=st.session_state.match_df,
                    sender_cfg=sender_cfg,
                    smtp_host=smtp_host,
                    smtp_port=smtp_port,
                    pdf_map=st.session_state.pdf_map,
                    subject_template=subject_template,
                    body_template=body_template,
                )
                st.session_state.match_df = sent_df
                st.success("Processo de disparo finalizado.")
            finally:
                cleanup_temp_dir(st.session_state.temp_dir)
                st.session_state.temp_dir = None
                st.session_state.pdf_map = {}
                st.info("Arquivos temporários removidos da VPS.")


if __name__ == "__main__":
    main()
