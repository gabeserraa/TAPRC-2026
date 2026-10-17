import logging
import os

import azure.functions as func
import pyodbc

app = func.FunctionApp()
logger = logging.getLogger(__name__)

# A cada 5 minutos (formato NCRONTAB: seg min hora dia mês dia-semana)
SCHEDULE = "0 */5 * * * *"


def get_connection():
    """Abre a conexão usando SOMENTE variáveis de ambiente (nada de credencial no código)."""
    host = os.getenv("DB_HOST")
    database = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    faltando = [
        nome
        for nome, valor in {
            "DB_HOST": host,
            "DB_NAME": database,
            "DB_USER": user,
            "DB_PASSWORD": password,
        }.items()
        if not valor
    ]
    if faltando:
        raise RuntimeError(
            f"Variáveis de ambiente não definidas: {', '.join(faltando)}"
        )

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


def extrair_tabela(tabela: str) -> list[dict]:
    """Executa SELECT * na tabela do schema itsm e devolve as linhas como dicionários."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM itsm.{tabela}")
        colunas = [col[0] for col in cursor.description]
        linhas = [dict(zip(colunas, row)) for row in cursor.fetchall()]

    logger.info(f"[itsm.{tabela}] {len(linhas)} linha(s) extraída(s)")
    for linha in linhas[:5]:  # mostra só uma amostra no log
        logger.info(f"[itsm.{tabela}] {linha}")
    return linhas


def executar(tabela: str) -> None:
    try:
        extrair_tabela(tabela)
    except (pyodbc.Error, RuntimeError) as e:
        logger.error(f"[itsm.{tabela}] Erro ao conectar/consultar o banco: {e}")


# ---------------------------------------------------------------------------
# Uma Azure Function (timer trigger) para cada tabela do banco de origem
# ---------------------------------------------------------------------------


@app.timer_trigger(
    schedule=SCHEDULE, arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def analista(myTimer: func.TimerRequest) -> None:
    executar("analista")


@app.timer_trigger(
    schedule=SCHEDULE, arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def categoria(myTimer: func.TimerRequest) -> None:
    executar("categoria")


@app.timer_trigger(
    schedule=SCHEDULE, arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def chamado(myTimer: func.TimerRequest) -> None:
    executar("chamado")


@app.timer_trigger(
    schedule=SCHEDULE, arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def chamado_sla(myTimer: func.TimerRequest) -> None:
    executar("chamado_sla")


@app.timer_trigger(
    schedule=SCHEDULE, arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def chamado_status_historico(myTimer: func.TimerRequest) -> None:
    executar("chamado_status_historico")


@app.timer_trigger(
    schedule=SCHEDULE, arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def cliente_organizacao(myTimer: func.TimerRequest) -> None:
    executar("cliente_organizacao")


@app.timer_trigger(
    schedule=SCHEDULE, arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def csat_avaliacao(myTimer: func.TimerRequest) -> None:
    executar("csat_avaliacao")


@app.timer_trigger(
    schedule=SCHEDULE, arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def fila(myTimer: func.TimerRequest) -> None:
    executar("fila")


@app.timer_trigger(
    schedule=SCHEDULE, arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def sla(myTimer: func.TimerRequest) -> None:
    executar("sla")


@app.timer_trigger(
    schedule=SCHEDULE, arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def solicitante(myTimer: func.TimerRequest) -> None:
    executar("solicitante")