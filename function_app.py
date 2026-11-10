import json
import logging
import os
from datetime import datetime, timezone

import pyodbc
import azure.functions as func
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()

SCHEMA_ORIGEM = "itsm"
SCHEMA_DESTINO = "dbo"
CONTAINER = "bronze"

TABELAS = [
    "categoria",
    "cliente_organizacao",
    "fila",
    "sla",
    "analista",
    "solicitante",
    "chamado",
    "chamado_sla",
    "chamado_status_historico",
    "csat_avaliacao",
]


def get_env(name: str) -> str:
    valor = os.getenv(name)
    if not valor:
        raise RuntimeError(f"Variavel de ambiente ausente: {name}")
    return valor


def get_conn_str_origem() -> str:
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


def get_conn_str_destino() -> str:
    return (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={get_env('DB_DEST_HOST')};"
        f"DATABASE={get_env('DB_DEST_NAME')};"
        f"UID={get_env('DB_DEST_USER')};"
        f"PWD={get_env('DB_DEST_PASSWORD')};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )


def extrair_tabela(cursor, tabela: str) -> list[dict]:
    cursor.execute(f"SELECT * FROM {SCHEMA_ORIGEM}.{tabela}")
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def gravar_bronze(blob_service, tabela: str, dados: list[dict], now: datetime) -> str:
    conteudo_json = json.dumps(dados, ensure_ascii=False, indent=2, default=str)

    file_path = (
        f"{SCHEMA_ORIGEM}/{tabela}/"
        f"ano={now:%Y}/mes={now:%m}/dia={now:%d}/"
        f"{tabela}_{now:%Y%m%dT%H%M%SZ}.json"
    )

    blob_client = blob_service.get_blob_client(container=CONTAINER, blob=file_path)
    blob_client.upload_blob(conteudo_json.encode("utf-8"), overwrite=False)
    return file_path


def popular_tabela_destino(cursor_destino, tabela: str, dados: list[dict]) -> tuple[int, int]:
    if not dados:
        return 0, 0

    tabela_completa = f"{SCHEMA_DESTINO}.{tabela}"
    pk = f"id_{tabela}"
    colunas = list(dados[0].keys())
    colunas_sem_pk = [col for col in colunas if col != pk]

    cursor_destino.execute(f"SELECT {pk} FROM {tabela_completa}")
    ids_existentes = {row[0] for row in cursor_destino.fetchall()}

    novos = [row for row in dados if row[pk] not in ids_existentes]
    existentes = [row for row in dados if row[pk] in ids_existentes]

    if novos:
        cols_sql = ", ".join(f"[{col}]" for col in colunas)
        placeholders = ", ".join("?" for _ in colunas)
        sql_insert = f"INSERT INTO {tabela_completa} ({cols_sql}) VALUES ({placeholders})"
        valores_insert = [tuple(row[col] for col in colunas) for row in novos]

        cursor_destino.execute(
            f"IF OBJECTPROPERTY(OBJECT_ID('{tabela_completa}'), 'TableHasIdentity') = 1 "
            f"SET IDENTITY_INSERT {tabela_completa} ON;"
        )
        try:
            cursor_destino.executemany(sql_insert, valores_insert)
        finally:
            cursor_destino.execute(
                f"IF OBJECTPROPERTY(OBJECT_ID('{tabela_completa}'), 'TableHasIdentity') = 1 "
                f"SET IDENTITY_INSERT {tabela_completa} OFF;"
            )

    if existentes and colunas_sem_pk:
        set_clause = ", ".join(f"[{col}] = ?" for col in colunas_sem_pk)
        sql_update = f"UPDATE {tabela_completa} SET {set_clause} WHERE [{pk}] = ?"
        valores_update = [
            tuple(row[col] for col in colunas_sem_pk) + (row[pk],)
            for row in existentes
        ]
        cursor_destino.executemany(sql_update, valores_update)

    return len(novos), len(existentes)


@app.timer_trigger(
    schedule="0 0 0 * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False,
)
def extract_itsm(myTimer: func.TimerRequest) -> None:
    logging.info(f"Iniciando extracao e carga do schema {SCHEMA_ORIGEM} ({len(TABELAS)} tabelas)")

    now = datetime.now(timezone.utc)
    blob_service = BlobServiceClient.from_connection_string(
        get_env("DATALAKE_CONNECTION_STRING")
    )

    falhas = []

    with (
        pyodbc.connect(get_conn_str_origem()) as conn_origem,
        pyodbc.connect(get_conn_str_destino()) as conn_destino,
    ):
        cursor_origem = conn_origem.cursor()
        cursor_destino = conn_destino.cursor()

        for tabela in TABELAS:
            try:
                dados = extrair_tabela(cursor_origem, tabela)
                caminho = gravar_bronze(blob_service, tabela, dados, now)
                logging.info(f"[{tabela}] {len(dados)} registros extraidos -> {CONTAINER}/{caminho}")

                inseridos, atualizados = popular_tabela_destino(cursor_destino, tabela, dados)
                conn_destino.commit()
                logging.info(
                    f"[{tabela}] Destino ({SCHEMA_DESTINO}.{tabela}): "
                    f"{inseridos} inseridos, {atualizados} atualizados"
                )
            except Exception:
                conn_destino.rollback()
                logging.exception(f"[{tabela}] Erro na extracao/carga")
                falhas.append(tabela)

    if falhas:
        raise RuntimeError(f"Falha em {len(falhas)} tabela(s): {', '.join(falhas)}")

    logging.info("Extracao e carga no banco de destino concluidas com sucesso")