import logging
import os
import azure.functions as func
import pyodbc

app = func.FunctionApp()

def get_connection():
    host = os.getenv("DB_HOST")
    database = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER=tcp:{host};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)


@app.timer_trigger(schedule="0 * * * * *", arg_name="myTimer",
                   run_on_startup=False, use_monitor=False)
def chamados(myTimer: func.TimerRequest) -> None:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT TOP 10 * FROM itsm.chamado")
            for row in cursor.fetchall():
                logging.info(row)
    except Exception as e:
        logging.error(f"Erro ao conectar/consultar o banco: {e}")


def analista(myTimer: func.TimerRequest) -> None:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT TOP 10 * FROM itsm.analista")
            for row in cursor.fetchall():
                logging.info(row)
    except Exception as e:
        logging.error(f"Erro ao conectar/consultar o banco: {e}")        