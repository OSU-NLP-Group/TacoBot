"""
This file contains functions to create and configure the tacologger
"""

import logging
import sys
import colorama
from dataclasses import dataclass
from typing import Optional
from taco.core.logging_formatting import tacoFormatter


PRIMARY_INFO_NUM = logging.INFO + 5  # between INFO and WARNING
TACO_PRIMARY_INFO_NUM = logging.INFO + 7  # between INFO and WARNING
TACO_MERGE_INFO_NUM = logging.INFO + 7  # higher than primary info
TIME_MAN_INFO_NUM = logging.INFO + 5  # higher than primary info


@dataclass
class LoggerSettings:
    logtoscreen_level: int
    logtoscreen_usecolor: bool
    logtofile_level: Optional[int]  # None means don't log to file
    logtofile_path: Optional[str]  # None means don't log to file
    logtoscreen_allow_multiline: bool  # If true, log-to-screen messages contain \n. If false, all the \n are replaced with <linebreak>
    integ_test: bool  # If True, we setup the logger in a special way to work with nosetests
    remove_root_handlers: bool  # If True, we remove all other handlers on the root logger


# AWS adds a LambdaLoggerHandler to the root handler, which causes duplicate logging because we have our customized
# StreamHandler on the root logger too. So we set remove_root_handlers=True to remove the LambdaLoggerHandler.
# See here: https://stackoverflow.com/questions/50909824/getting-logs-twice-in-aws-lambda-function
PROD_LOGGER_SETTINGS = LoggerSettings(logtoscreen_level=logging.INFO,
                                      logtoscreen_usecolor=True,
                                      logtofile_level=None,
                                      logtofile_path=None,
                                      logtoscreen_allow_multiline=False,
                                      integ_test=False,
                                      remove_root_handlers=True)


def setup_logger(logger_settings, session_id=None):
    """
    Sets up the tacologger using given logger_settings and session_id.

    Following best practices (https://docs.python.org/3/library/logging.html#logging.Logger.propagate) we attach our
    customized handlers to the root logger. The tacologger is a descendent of the root logger, so all tacologger
    messages are passed to the root logger, and then handled by our handlers.
    """
    # Set elasticsearch level to ERROR (it does excessive long WARNING logs)
    logging.getLogger('elasticsearch').setLevel(logging.ERROR)

    # For colored logging, automatically add RESET_ALL after each print statement.
    # This is especially important for when we log errors/warnings in red (we do not RESET ourselves because we want the
    # stack trace to be red too).
    if logger_settings.logtoscreen_usecolor:
        colorama.init(convert=False, strip=False, autoreset=True)

    # Either create or get existing logger with name tacologger
    taco_logger = logging.getLogger('tacologger')

    # Save our logger_settings in taco_logger
    taco_logger.logger_settings = logger_settings

    # Get root logger
    root_logger = logging.getLogger()

    # If the root logger already has our handler(s) set up, no need to do anything else
    if hasattr(root_logger, 'taco_handlers'):
        return taco_logger

    # Optionally, remove any pre-existing handlers on the root logger
    if logger_settings.remove_root_handlers:
        for h in root_logger.handlers:
            root_logger.removeHandler(h)

    # For integration tests, we need our logger to work with nosetests Logcapture plugin.
    # For complicated reasons, that means we need to set taco_logger to have the desired level (not the handlers)
    # See the "integration tests" internal documentation for explanation.
    if logger_settings.integ_test:
        if logger_settings.logtofile_level:
            assert logger_settings.logtoscreen_level == logger_settings.logtofile_level, f'For integration testing, ' \
                f'logtoscreen_level={logger_settings.logtoscreen_level} must equal logtofile_level={logger_settings.logtofile_level}'
            taco_logger.setLevel(logger_settings.logtoscreen_level)
    else:
        # For non integration tests, set taco logger's level as low as possible.
        # This means tacologger passes on all messages, and the handlers filter by level.
        taco_logger.setLevel(logging.DEBUG)

    # Create the stream handler and attach it to the root logger
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logger_settings.logtoscreen_level)
    stream_formatter = tacoFormatter(allow_multiline=logger_settings.logtoscreen_allow_multiline, use_color=logger_settings.logtoscreen_usecolor, session_id=session_id)
    stream_handler.setFormatter(stream_formatter)
    root_logger.addHandler(stream_handler)

    # Create the file handler and attach it to the root logger
    if logger_settings.logtofile_path:
        file_handler = logging.FileHandler(logger_settings.logtofile_path, mode='w')
        file_handler.setLevel(logger_settings.logtofile_level)
        file_formatter = tacoFormatter(allow_multiline=True, use_color=False, session_id=session_id)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Mark that the root logger has the taco handlers attached
    root_logger.taco_handlers = True

    # Add the custom PRIMARY_INFO level to taco logger
    add_new_level(taco_logger, 'TACO_PRIMARY_INFO', TACO_PRIMARY_INFO_NUM)
    add_new_level(taco_logger, 'PRIMARY_INFO', PRIMARY_INFO_NUM)
    add_new_level(taco_logger, 'TACO_MERGE', TACO_MERGE_INFO_NUM)
    add_new_level(taco_logger, 'TIME_track', TIME_MAN_INFO_NUM)

    return taco_logger


def add_new_level(logger, level_name, level_num):
    """
    Add a new logging level to a logging.Logger object.

    logger: a Logger
    level_name: string
    level_num: int
    """

    # Add the level name
    logging.addLevelName(level_num, level_name.upper())

    # Make a function to log messages at the new level
    # This function copies the convenience functions Logger.debug(), Logger.info(), etc
    def log_message_at_level(msg, *args, **kwargs):
        if logger.isEnabledFor(level_num):
            logger._log(level_num, msg, args, **kwargs)

    # Attach this function to the logger
    setattr(logger, level_name.lower(), log_message_at_level)


def update_logger(session_id, function_version):
    """
    This function does some updates that need to be done at the start of every turn.
    It is assumed that setup_logger has already been run.
    """
    root_logger = logging.getLogger()
    taco_logger = logging.getLogger('tacologger')
    logger_settings = taco_logger.logger_settings

    # When running integration tests with nosetests and the logcapture plugin, logs are captured by MyMemoryHandler
    # (which is attached to root logger) and then printed for failed tests.
    # See "integration tests" internal documentation for more info.
    # For readability, we want MyMemoryHandler to use tacoFormatter. This needs to be set every turn because
    # MyMemoryHandler sometimes gets reinitialized between turns/tests.
    if logger_settings.integ_test:
        for h in root_logger.handlers:
            if type(h).__name__ == 'MyMemoryHandler':
                # use_color=False because it shows up as color codes, rather than actual colors, when we view the
                # nosetest results in an output text file / in dev pipeline.
                stream_formatter = tacoFormatter(allow_multiline=logger_settings.logtoscreen_allow_multiline,
                                                   use_color=False, session_id=session_id)
                h.setFormatter(stream_formatter)

    # Add session_id and function_version to the tacoFormatters attached to handlers on the root logger
    # This will mean session_id and function_version are shown in every log message.
    for handler in root_logger.handlers:
        if isinstance(handler.formatter, tacoFormatter):
            handler.formatter.update_session_id(session_id)
            handler.formatter.update_function_version(function_version)
