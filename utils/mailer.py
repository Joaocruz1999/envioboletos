import smtplib
import time
from email.message import EmailMessage
from html import escape
from pathlib import Path
from typing import Dict, List

import pandas as pd
import streamlit as st

from utils.data_ops import split_cc_emails


def create_email_message(
    sender_email: str,
    recipient_email: str,
    cc_emails: List[str],
    row: pd.Series,
    pdf_path: str,
    subject_template: str,
    body_template: str,
) -> EmailMessage:
    template_values = {
        "nome": str(row["Nome"]),
        "razao_social": str(row["Razao Social"]),
        "cnpj": str(row["CNPJ"]),
    }
    subject = subject_template.format(**template_values)
    text_body = body_template.format(**template_values)
    html_body = "<br>".join(escape(text_body).splitlines())

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = recipient_email
    if cc_emails:
        message["Cc"] = ", ".join(cc_emails)
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    pdf_bytes = Path(pdf_path).read_bytes()
    message.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=Path(pdf_path).name,
    )
    return message


def send_emails(
    df: pd.DataFrame,
    sender_cfg: Dict[str, str],
    smtp_host: str,
    smtp_port: int,
    pdf_map: Dict[str, str],
    subject_template: str,
    body_template: str,
) -> pd.DataFrame:
    result_df = df.copy()
    selected_mask = result_df["Enviar"].fillna(False).astype(bool)
    selected_indexes = result_df.index[selected_mask].tolist()

    if not selected_indexes:
        st.warning("Nenhum cliente marcado para envio.")
        return result_df

    progress_bar = st.progress(0.0, text="Iniciando envios...")
    total = len(selected_indexes)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(sender_cfg["email"], sender_cfg["app_password"])

            for position, idx in enumerate(selected_indexes, start=1):
                row = result_df.loc[idx]
                recipient = str(row["Email"]).strip()
                cc_emails = split_cc_emails(row["Cópia"])
                cnpj = str(row["CNPJ"])
                pdf_path = pdf_map.get(cnpj)

                if not recipient:
                    result_df.at[idx, "Status"] = "Erro: cliente sem e-mail."
                elif not pdf_path or not Path(pdf_path).exists():
                    result_df.at[idx, "Status"] = "Erro: PDF não encontrado."
                else:
                    try:
                        message = create_email_message(
                            sender_email=sender_cfg["email"],
                            recipient_email=recipient,
                            cc_emails=cc_emails,
                            row=row,
                            pdf_path=pdf_path,
                            subject_template=subject_template,
                            body_template=body_template,
                        )
                        recipients = [recipient] + cc_emails
                        smtp.send_message(message, to_addrs=recipients)
                        result_df.at[idx, "Status"] = "Enviado com Sucesso"
                    except Exception as exc:
                        result_df.at[idx, "Status"] = f"Erro: {exc}"

                progress_bar.progress(position / total, text=f"Enviando e-mail {position}/{total}")
                if position < total:
                    time.sleep(3)

    except Exception as exc:
        selected_df = result_df.loc[selected_indexes]
        pending_indexes = selected_df[selected_df["Status"].eq("Pendente")].index
        for idx in pending_indexes:
            result_df.at[idx, "Status"] = f"Erro SMTP: {exc}"
        st.error(f"Falha na conexão/autenticação SMTP: {exc}")

    return result_df

