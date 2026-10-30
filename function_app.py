import json
import logging
import os
from datetime import datetime, timezone

import pyodbc
import azure.functions as func
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()

SCHEMA = "itsm"
CONTAINER = "bronze"

TABELAS = [
    "analista",
    "categoria",
    "chamado",
    "chamado_sla",
    "chamado_status_historico",
    "cliente_organizacao",
    "csat_avaliacao",
    "fila",
    "sla",
    "solicitante",
]


def get_env(name: str) -> str:
    valor = os.getenv(name)
    if not valor:
        raise RuntimeError(f"Variavel de ambiente ausente: {name}")
    return valor


def get_conn_str() -> str:
    return (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={get_env('DB_HOST')};"
        f"DATABASE={get_env('DB_NAME')};"
        f"UID={get_env('DB_USER')};"
        f"PWD={get_env('DB_PASSWORD')};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )


def extrair_tabela(cursor, tabela: str) -> list[dict]:
    cursor.execute(f"SELECT * FROM {SCHEMA}.{tabela}")
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def gravar_bronze(blob_service, tabela: str, dados: list[dict], now: datetime) -> str:
    conteudo_json = json.dumps(dados, ensure_ascii=False, indent=2, default=str)

    file_path = (
        f"{SCHEMA}/{tabela}/"
        f"ano={now:%Y}/mes={now:%m}/dia={now:%d}/"
        f"{tabela}_{now:%Y%m%dT%H%M%SZ}.json"
    )

    blob_client = blob_service.get_blob_client(container=CONTAINER, blob=file_path)
    blob_client.upload_blob(conteudo_json.encode("utf-8"), overwrite=False)
    return file_path


@app.timer_trigger(
    schedule="0 * * * * *",  # a cada minuto; ex.: "0 0 * * * *" = de hora em hora
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def extract_itsm(myTimer: func.TimerRequest) -> None:
    logging.info(f"Iniciando extracao do schema {SCHEMA} ({len(TABELAS)} tabelas)")

    now = datetime.now(timezone.utc)
    blob_service = BlobServiceClient.from_connection_string(
        get_env("DATALAKE_CONNECTION_STRING")
    )

    falhas = []

    with pyodbc.connect(get_conn_str()) as conn:
        cursor = conn.cursor()

        for tabela in TABELAS:
            try:
                dados = extrair_tabela(cursor, tabela)
                caminho = gravar_bronze(blob_service, tabela, dados, now)
                logging.info(f"[{tabela}] {len(dados)} registros -> {CONTAINER}/{caminho}")
            except Exception:
                logging.exception(f"[{tabela}] Erro na extracao")
                falhas.append(tabela)

    if falhas:
        raise RuntimeError(f"Falha em {len(falhas)} tabela(s): {', '.join(falhas)}")

    logging.info("Extracao concluida com sucesso")