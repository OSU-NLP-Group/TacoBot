import warnings
from injector import Injector_Key
from .taco_state_manager import StateManager
from .taco_logger import LoggerFactory
# from cobot_core.service_module import ToolkitServiceModule
from .taco_service_module_manager import ServiceModuleManager
from .taco_analyzer import Analyzer
# from cobot_python_sdk.alexa_request_handler import AlexaRequestHandler
from .taco_event import Event
from .taco_dynamodb_manager import DynamoDbManager

from .taco_user_attributes import UserAttributes
from .taco_user_attributes_manager import UserAttributesManager

# from cobot_core.response_builder import ResponseBuilder
from .taco_global_intent_handler import GlobalIntentHandler
# from cobot_core.asr_processor import ASRProcessor
from cobot_core.module import SocialbotBaseModule

from .taco_dialogue_manager import DialogManager
from injector import InstanceProvider, SingletonScope
from typing import List

StateTableName = Injector_Key('state_table_name')
APIKey = Injector_Key('api_key')

class Handler:
    """
    CobotHandler is the main entry point for a Cobot instance, and handles basic component instantiation and event flow management.
    Generally, a developer will only need to worry about the arguments for the __init__ method, which is called in the main lambda_handler entry point.
    """

    def __init__(self, event,  # type: dict
                 context,  # type: dict
                 app_id=None,  # type: str
                 user_table_name=None,  # type: str
                 save_before_response=True,
                 state_table_name=None,
                 overrides=None,
                 api_key=None,
                 name='TacoBot'):
        """
        :param app_id: replace with your ASK skill id to validate ask request. None means skipping ASK request validation.
        :param user_table_name: replace with a DynamoDB table name to store user preference data. We will auto create the DynamoDB table if the table name doesn’t exist.
                            None means user preference data won’t be persisted in DynamoDB.
        :param save_before_response: If it is true, skill persists user preference data at the end of each turn.
                            Otherwise, only at the last turn of whole session.
        :param state_table_name: replace with a DynamoDB table name to store session state data. We will auto create the DynamoDB table if the table name doesn’t exist.
                            None means session state data won’t be persisted in DynamoDB.
        :param overrides: provide custom override for dialog manager components.
        :param api_key: provide AP team's API key to authenticate/authorize calls to toolkit service
        :param name: provide your cobot name, primarily used for A/B test
        """

        super(Handler, self).__init__(event, context, app_id, user_table_name, save_before_response)

        if api_key is None:
            warnings.warn(
                'Warning: API Key is not set. Please set it in your cobot instance. Otherwise you cannot connect with Alexa Prize Toolkit Service')

        def configure(binder):
            binder.bind(StateTableName, to=InstanceProvider(state_table_name))
            binder.bind(APIKey, to=InstanceProvider(api_key))
            binder.bind_scope(SingletonScope)  # DONOTDELETE: key

        if overrides:
            self.injector = self.injector.create_child_injector([SocialbotBaseModule, configure, overrides])

        else:
            self.injector = self.injector.create_child_injector([SocialbotBaseModule, configure])

        if state_table_name is not None:
            DynamoDbManager.ensure_table_exists(state_table_name, 'state')

        self._initialize_state_manager_properties()
        ToolkitServiceModule.api_key = api_key
        self.name = name
        self.service_module_manager = self.injector.get(ServiceModuleManager)

        self.logger = LoggerFactory.setup(self)
        self.logger.debug('event: {}'.format(event))
        self.logger.info('Current state: {}'.format(self.state_manager.current_state))
        self.logger.debug('Session history: {}'.format(self.state_manager.session_history))
        self.logger.debug('User attributes: {}'.format(self.state_manager.user_attributes))

    def _initialize_state_manager_properties(self):
        self.state_manager = self.injector.get(StateManager)
        self.event = self.injector.get(Event)
        self.state_manager.current_state = self.event
        self.state_manager.session_history = (
            self.event.get('session.sessionId', None), StateManager.DEFAULT_MAXIMUM_SESSION_HISTORY_COUNT)
        self.state_manager.last_state = self.event
        self.state_manager.user_attributes = self._initialize_user_attributes()

    def _initialize_user_attributes(self):
        user_attributes = self.injector.get(UserAttributes)
        user_attributes_manager = self.injector.get(UserAttributesManager)
        event = self.injector.get(Event)
        # Fetch attributes from last session and merge to current turn's attributes.
        if user_attributes_manager.persistence_enabled and (
                event.get('session.sessionId') is not None or event.get('session.new')
        ):
            persistent_attributes = user_attributes_manager.retrieve_user_attributes(event.user_id)
            if persistent_attributes is not None:
                user_attributes.merge(persistent_attributes)
                # Use the conversation_id from event as authority since last session's conversation_id may be outdated
                user_attributes.conversationId = event.conversation_id
        return user_attributes

    def add_response_generators(self, response_generators):
        """
        Called to register additional response generators with the Cobot instance.

        Each response generator specification must contain the following keys:

        name: response generator name in capital letter
        class: python class implementation. Use RemoteServiceModule for Remote Response Generator if no method override is required.
        url: remote service url. If a remote service is setup by cobot-deploy script: call ServiceURLLoader.get_url_for_module("module_name") to fetch url from service load balancer's endpoint. Otherwise provide a custom url
        context_manager_keys: a list of state keys to pass to service module.

        :param response_generators: list of response generator module specifications
        """
        for response_generator in response_generators:
            self.service_module_manager.add_response_generator_module(response_generator)

    def upsert_module(self, module):
        """
        Called to insert or update a service module with the Cobot instance.

        Each module specification must contain the following keys:

        name: service name in lower case
        class: python class implementation. Use RemoteServiceModule for Remote Response Generator if no method override is required.
        url: remote service url or 'local'. If a remote service is setup by cobot-deploy script: call ServiceURLLoader.get_url_for_module("module_name") to fetch url from service load balancer's endpoint. Otherwise provide a custom url
        context_manager_keys: a list of state keys to pass to service module.

        :param module: module specification
        """
        self.service_module_manager.upsert_module(module)

    def create_nlp_pipeline(self, nlp_def: List[List[str]]):
        """
        Called to create a NLP pipeline with the given nlp definition.
        If you need to add a new module to the pipeline, register the module by cobot.upsert_module(module)
        before creating the pipeline.

        :param nlp_def: List of service module names, default pipeline contains [["intent", "ner", "sentiment", "topic"]], modules in the same list are run in parallel,
        modules in a previous list run before modules in a later list.
        [['a', 'b'],['c']] => module a and b are run in parallel before module c, and module c can have access to module a and b's outputs
        """
        self.service_module_manager.create_nlp_pipeline(nlp_def)

    # TODO: override CobotHandler's persist method
    def persist(self, alexa_response: str, state_manager: StateManager) -> None:
        """
        Persist attributes to DynamoDB
        """
        try:
            should_end_session = alexa_response['response'].get('shouldEndSession')
            if should_end_session is None:
                super(CobotHandler, self).persist(False)
            else:
                super(CobotHandler, self).persist(alexa_response['response']['shouldEndSession'])
            self.logger.debug('Persisted user attributes')
            self.state_manager.persist_state()
            self.logger.debug('Persisted state')
        except:
            self.logger.error('Exception when persisting to DynamoDB', exc_info=True)

    def execute(self):
        # type: () -> AlexaResponseType
        """
        Execute the current cobot pipeline using the registered components to generate an AlexaResponse object, containing TTS which will be spoken to the user
        """
        speech_output = ''
        directives = []
        response_builder = self.injector.get(ResponseBuilder)
        global_intent_handler = self.injector.get(GlobalIntentHandler)
        asr_processor = self.injector.get(ASRProcessor)
        analyzer = self.injector.get(Analyzer)
        dm = self.injector.get(DialogManager)

        global_intent_output, should_end_session = global_intent_handler.execute(self.event)
        if global_intent_output:
            speech_output += global_intent_output
        if not should_end_session:
            asr_processor_output = asr_processor.process()
            if asr_processor_output:
                speech_output += ' ' + asr_processor_output
            else:
                features = analyzer.analyze()

                response_generator_output, should_end_session, directives = dm.select_response(features)
                if response_generator_output:
                    speech_output += ' ' + response_generator_output

        speech_output = speech_output.strip()
        alexa_response = response_builder.build(speech_output, should_end_session, directives)
        self.logger.info('Final alexa response:{}'.format(alexa_response))
        self.persist(alexa_response, self.state_manager)

        return alexa_response
