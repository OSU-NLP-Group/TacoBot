"""
in main loop:

1. run remote modules
2. initialize text agent (run server)
3. enter loop in commandline and interact with text agent
"""
import os
from pathlib import Path
import logging
from servers.local.callable_config import callable_config
from agents.local_agent import LocalAgent
# from agents.local_agent_debug import LocalAgent
from chirpy.core.logging_utils import LoggerSettings, setup_logger
from servers.local.local_callable_manager import LocalCallableManager

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

CHIRPY_HOME = os.environ.get('CHIRPY_HOME', Path(__file__).parent.parent)

logger = logging.getLogger('chirpylogger')

# Logging settings
LOGTOSCREEN_LEVEL = logging.INFO + 7
# LOGTOSCREEN_LEVEL = logging.INFO + 7
LOGTOFILE_LEVEL = logging.DEBUG


CONVERSATION_STATE = {}


def init_logger():
    logger_settings = LoggerSettings(logtoscreen_level=LOGTOSCREEN_LEVEL, logtoscreen_usecolor=True,
                                     logtofile_level=LOGTOFILE_LEVEL, logtofile_path='',
                                     logtoscreen_allow_multiline=True, integ_test=False, remove_root_handlers=False)
    setup_logger(logger_settings)



def setup_callables():
    callable_manager = LocalCallableManager(callable_config)
    # callable_manager.start_containers()
    for callable, config in callable_config.items():
        os.environ[f'{callable}_URL'] = config['url']
    return callable_manager


@app.route("/", methods=["GET"])
def index_get():
    return render_template("base.html")


@app.route("/predict", methods=["POST"])
def predict():
    text = request.get_json(force=True).get("message")
    response = get_response(text)
    message = {"answer": response}
    return jsonify(message)


def init_chat():
    init_logger()
    callable_manager = setup_callables() # check if container is already running
    # execute dialogue in loop
    local_agent = LocalAgent(debug=False)
    should_end_conversation = False
    k = 0
    return k, should_end_conversation, callable_manager, local_agent


def get_response(user_utterance):
    k = CONVERSATION_STATE["turn"]
    should_end_conversation = CONVERSATION_STATE["should_end_conversation"]
    callable_manager = CONVERSATION_STATE["callable_manager"]
    local_agent = CONVERSATION_STATE["local_agent"]

    if should_end_conversation:
        callable_manager.stop_containers()
    else:
        response, deserialized_current_state = local_agent.process_utterance(user_utterance)
        should_end_conversation = deserialized_current_state['should_end_session']
        print(response)
        k += 1
        CONVERSATION_STATE["turn"] = k
        CONVERSATION_STATE["should_end_conversation"] = should_end_conversation
        CONVERSATION_STATE["callable_manager"] = callable_manager
        CONVERSATION_STATE["local_agent"] = local_agent

        return response
    


def main():
    init_logger()
    callable_manager = setup_callables() # check if container is already running
    # execute dialogue in loop
    local_agent = LocalAgent(debug=False)
    should_end_conversation = False
    k = 0

    while not should_end_conversation:
        user_utterance = input("> ")
        # if k == 0:
        #     user_utterance = "let's work together"
        response, deserialized_current_state = local_agent.process_utterance(user_utterance)
        should_end_conversation = deserialized_current_state['should_end_session']
        print(response)
        k += 1

    callable_manager.stop_containers()


if __name__ == "__main__":
   main()


# if __name__ == "__main__":
#     k, should_end_conversation, callable_manager, local_agent  = init_chat()
#     CONVERSATION_STATE["turn"] = k
#     CONVERSATION_STATE["should_end_conversation"] = should_end_conversation
#     CONVERSATION_STATE["callable_manager"] = callable_manager
#     CONVERSATION_STATE["local_agent"] = local_agent

#     app.run(host='0.0.0.0', port=5050)
