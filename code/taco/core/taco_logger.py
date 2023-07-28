import configparser
import os
import logging

from taco_event import Event


class ConfigReader(object):
    def __init__(self):
        self.config = configparser.ConfigParser()
        current_path = os.path.dirname(__file__)
        config_path = os.path.join(current_path, 'taco_logging.conf')
        self.config.read(config_path)

    def get(self, section, key):
        return self.config.get(section, key)


class CustomAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        custom_prefix = ' '.join([v for k, v in self.extra.items()])
        return '%s %s' % (custom_prefix, msg), kwargs


class LoggerFactory(object):

    @classmethod
    def setup(cls, clazz: object, event=None):
        logger = logging.getLogger(__name__)
        logger.setLevel(ConfigReader().get('logger_root', 'level'))

        formatter = [key.strip() for key in ConfigReader().get('logger_root', 'formatter_prefix').split(',')]
        extra_data = {}
        for key in formatter:
            value=None
            if event:
                value = getattr(Event(event), key, '')
            elif hasattr(clazz, 'state_manager'):
                value = getattr(clazz.state_manager.current_state, key, '')
            if value is not None:
                extra_data[key] = value
        return CustomAdapter(logger, extra_data)