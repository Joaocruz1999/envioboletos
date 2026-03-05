from collections.abc import Mapping
from typing import Dict, Tuple

import pandas as pd
import streamlit as st


def init_session_state() -> None:
    defaults = {
        "authenticated": False,
        "match_df": pd.DataFrame(),
        "temp_dir": None,
        "pdf_map": {},
        "last_upload_signature": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_access_password() -> str:
    app_secrets = st.secrets.get("app", {})
    return app_secrets.get("access_password", "")


def get_senders() -> Dict[str, Dict[str, str]]:
    senders = st.secrets.get("senders", {})
    if not isinstance(senders, Mapping):
        return {}

    normalized = {}
    for sender_name, sender_cfg in senders.items():
        if not isinstance(sender_cfg, Mapping):
            continue

        email = str(sender_cfg.get("email", "")).strip()
        app_password = str(sender_cfg.get("app_password", "")).strip()
        display_name = str(sender_cfg.get("display_name", sender_name)).strip()

        if email and app_password:
            normalized[sender_name] = {
                "email": email,
                "app_password": app_password,
                "display_name": display_name,
            }
    return normalized


def get_smtp_config() -> Tuple[str, int]:
    smtp_cfg = st.secrets.get("smtp", {})
    host = smtp_cfg.get("host", "smtp.gmail.com")
    port = int(smtp_cfg.get("port", 587))
    return host, port

