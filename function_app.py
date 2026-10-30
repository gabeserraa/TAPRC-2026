
import json
import logging
import os
from datetime import datetime, timezone

import pyodbc
import azure.functions as func
from azure.storage.filedatalake import DataLakeServiceClient

app = func.FunctionApp()


@app.timer_trigger(
    schedule="0 * * * * *",
    arg_name="myTimer",
    run_on_startup=False,
    use_monitor=False
)
def extract_chamado(myTimer: func.TimerRequest) -> None:
    logging.info("Iniciando extracao da tabela itsm.chamado")

    sql_server = os.environ["DB_HOST"]
    sql_database = os.environ["DB_NAME"]
    sql_user = os.environ["DB_USER"]
    sql_pass = os.environ["DB_PASSWORD"]

    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={sql_server};"
        f"DATABASE={sql_database};"
        f"UID={sql_user};"
        f"PWD={sql_pass};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    logging.info(f"Testeeeeeeee")

    try:
        # 1. Extrair os dados do SQL Server
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM itsm.chamado")

            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

            dados = [
                dict(zip(columns, row))
                for row in rows
            ]

        logging.info(f"Registros extraidos: {len(dados)}")

        # 2. Converter os registros para JSON
        conteudo_json = json.dumps(
            dados,
            ensure_ascii=False,
            indent=2,
            default=str
        )

        # 3. Criar o caminho particionado por data UTC
        now = datetime.now(timezone.utc)

        diretorio = (
            f"itsm/chamados/"
            f"ano={now:%Y}/"
            f"mes={now:%m}/"
            f"dia={now:%d}"
        )

        nome_arquivo = (
            f"chamados_{now:%Y%m%dT%H%M%SZ}.json"
        )

        file_path = f"{diretorio}/{nome_arquivo}"

        # 4. Conectar ao Azure Data Lake
        datalake = DataLakeServiceClient.from_connection_string(
            os.environ["DATALAKE_CONNECTION_STRING"]
        )

        # 5. Gravar o arquivo no container Bronze
        file_system = datalake.get_file_system_client("bronze")
        file_client = file_system.get_file_client(file_path)

        file_client.upload_data(
            conteudo_json.encode("utf-8"),
            overwrite=False
        )

        logging.info(f"Arquivo gravado: bronze/{file_path}")

    except Exception:
        logging.exception("Erro durante a extracao de itsm.chamado")
        raise
