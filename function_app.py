import logging
import os 
import requests
import azure.functions as func

app = func.FunctionApp()

def teste():
    logging.info('TESTANDO 1234')

@app.timer_trigger(schedule="0 */5 * * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False) 
def timer_trigger_5min(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function executed.')

    teste()

@app.timer_trigger(schedule="0 */3 * * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False) 
def timer_trigger_3min(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function executed.')

    teste()

@app.timer_trigger(schedule="0 */1 * * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False) 
def timer_trigger_1min(myTimer: func.TimerRequest) -> None:
    
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function executed.')

    teste()

@app.route(route="http_trigger", auth_level=func.AuthLevel.ANONYMOUS)
def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )




@app.timer_trigger(schedule="0 */1 * * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False) 
def timer_trigger_http(myTimer: func.TimerRequest) -> None:
    
    logging.info("Timer iniciando chamada HTTP.")

    url = os.getenv(
        "HTTP_FUNCTION_URL",
        "https://functionapp-gabriel0001-frbxc7c8hmbchmc2.eastus-01.azurewebsites.net/api/http_trigger"
    )

    parametros = {
        "name": "Gabriel"
    }

    try:
        resposta = requests.get(
            url,
            params=parametros,
            timeout=30
        )

        logging.info(f"Status HTTP: {resposta.status_code}")
        logging.info(f"Resposta da Function: {resposta.text}")

    except requests.RequestException as erro:
        logging.error(f"Erro ao chamar a HTTP Function: {erro}")