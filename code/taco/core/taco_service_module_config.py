from .taco_utils import is_url_valid


class ServiceModuleConfig(object):

    def __init__(self, module: dict):
        """
        :param name: [required] module name in lowercase.
        :param class: [required] python class implementation.
                      Use RemoteServiceModule for remote modules if no method override is required.
        :param url: [optional] remote service url or ‘local’. Default is 'local'.
                    For services in the Cobot stack, call ServiceURLLoader.get_url_for_module(“module_name”)
                    to fetch the service load balancer’s endpoint. Otherwise provide a custom url.
        :param context_manager_keys: [optional] a list of state keys to pass to service module.
        :param input_user_attributes_keys: [optional] a list of user attribute keys to pass to service module.
        :param history_turns: [optional] the number of history turns, excluding the current turn,
                              to fetch from the session history.
        :param timeout_in_millis: [optional] service module timeout in milliseconds. Default is 1000.
        """
        self.name = module['name']
        self.clazz = module['class']
        self.url = module.get('url', 'local')
        self.context_manager_keys = module.get('context_manager_keys', [])
        self.input_user_attributes_keys = module.get('input_user_attributes_keys', [])
        self.history_turns = module.get('history_turns', 0)
        # Use 1000 millisec as default timeout.
        self.timeout_in_millis = module.get('timeout_in_millis', 1000)

        if self.url != '' and self.url != 'local' and not is_url_valid(self.url):
            raise Exception('{} url: {} is not valid'.format(self.name, self.url))

        if self.history_turns < 0 or not isinstance(self.history_turns, int):
            raise Exception('history_turns must be a non-negative integer for {}'.format(self.module_name))