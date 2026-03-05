import re
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


EXPECTED_COLUMNS = ["Nome", "Razao Social", "CNPJ", "Email"]
EXPECTED_COLUMNS_SET = set(EXPECTED_COLUMNS)
PDF_PATTERN = re.compile(r"^boleto_(\d{14})\.pdf$", re.IGNORECASE)


def normalize_cnpj(value: object) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits.zfill(14) if digits else ""


def extract_cnpj_from_pdf_name(filename: str) -> Optional[str]:
    match = PDF_PATTERN.match(filename.strip())
    return match.group(1) if match else None


def split_cc_emails(cc_value: object) -> List[str]:
    raw = str(cc_value or "").strip()
    if not raw:
        return []
    chunks = re.split(r"[;,]", raw)
    return [item.strip() for item in chunks if item.strip()]


def load_clients_dataframe(excel_file) -> pd.DataFrame:
    df = pd.read_excel(excel_file)
    missing = EXPECTED_COLUMNS_SET - set(df.columns)
    if missing:
        missing_fmt = ", ".join(sorted(missing))
        raise ValueError(f"Planilha sem colunas obrigatórias: {missing_fmt}")

    work_df = df[EXPECTED_COLUMNS].copy()
    work_df["CNPJ"] = work_df["CNPJ"].apply(normalize_cnpj)
    work_df = work_df[work_df["CNPJ"] != ""]
    return work_df


def cleanup_temp_dir(temp_dir: Optional[str]) -> None:
    if temp_dir and Path(temp_dir).exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


def save_uploaded_pdfs(uploaded_pdfs) -> Tuple[str, Dict[str, str], List[str], List[str]]:
    temp_dir = tempfile.mkdtemp(prefix="boletos_")
    pdf_map: Dict[str, str] = {}
    invalid_files: List[str] = []
    duplicated_cnpjs: List[str] = []

    for uploaded_pdf in uploaded_pdfs:
        cnpj = extract_cnpj_from_pdf_name(uploaded_pdf.name)
        if not cnpj:
            invalid_files.append(uploaded_pdf.name)
            continue
        if cnpj in pdf_map:
            duplicated_cnpjs.append(cnpj)
            continue

        file_path = Path(temp_dir) / uploaded_pdf.name
        file_path.write_bytes(uploaded_pdf.getbuffer())
        pdf_map[cnpj] = str(file_path)

    return temp_dir, pdf_map, invalid_files, duplicated_cnpjs


def build_match_dataframe(clients_df: pd.DataFrame, pdf_map: Dict[str, str]) -> pd.DataFrame:
    matched = clients_df[clients_df["CNPJ"].isin(pdf_map.keys())].copy()
    matched["ArquivoPDF"] = matched["CNPJ"].map(lambda cnpj: Path(pdf_map[cnpj]).name)
    matched["Enviar"] = True
    matched["Cópia"] = ""
    matched["Status"] = "Pendente"
    column_order = ["Enviar", "Nome", "Razao Social", "CNPJ", "Email", "Cópia", "ArquivoPDF", "Status"]
    return matched[column_order].reset_index(drop=True)


def get_upload_signature(excel_file, pdf_files) -> Tuple[str, Tuple[str, ...]]:
    excel_sig = excel_file.name if excel_file else ""
    pdf_sig = tuple(sorted([item.name for item in (pdf_files or [])]))
    return excel_sig, pdf_sig

