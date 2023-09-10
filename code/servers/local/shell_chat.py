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
from taco.core.logging_utils import LoggerSettings, setup_logger
from servers.local.local_callable_manager import LocalCallableManager

logger = logging.getLogger('tacologger')

# Logging settings
LOGTOSCREEN_LEVEL = logging.INFO + 7
LOGTOFILE_LEVEL = logging.DEBUG

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

def main():
    init_logger()
    callable_manager = setup_callables() # check if container is already running
    # execute dialogue in loop
    local_agent = LocalAgent(debug=False)
    should_end_conversation = False
    k = 0

    while not should_end_conversation:
        user_utterance = input("> ")
        response, deserialized_current_state = local_agent.process_utterance(user_utterance)
        should_end_conversation = deserialized_current_state['should_end_session']
        print(response)
        k += 1

    callable_manager.stop_containers()
    
if __name__ == "__main__":
    main()
