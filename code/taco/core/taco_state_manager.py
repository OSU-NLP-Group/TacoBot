
from boto3.dynamodb.conditions import Key
from injector import Injector
from injector import inject, singleton
# from cobot_core.dependency_type import StateTableName
# from cobot_core.log.logger import LoggerFactory
from taco_event import Event
# from cobot_python_sdk.base_dependency_type import Context
from taco_user_attributes import UserAttributes
from taco_dynamodb_manager import DynamoDbManager
from taco_state import State
from taco_logger import LoggerFactory

StateTableName = "StateTable"  # Injector('state_table_name')
# Context = Injector('context')

@singleton
class StateManager(object):
    """
    Persists state information across sessions, establishes uniqueness of information for a given user session
    """
    DEFAULT_MAXIMUM_SESSION_HISTORY_COUNT = 50   # Rationale of setting the limit as 50: Larger limits cause too much latency when querying DynamoDB.
                                                 # 50 turns is enough to represent "short-term memory." "Long-term memory" can be stored in user attributes.
    @inject(
        table_name=StateTableName,
        user_attributes=UserAttributes
    )
    def __init__(self, table_name: StateTableName, user_attributes: UserAttributes, current_state: State) -> None:
        self.table_name = table_name
        self._user_attributes = user_attributes
        self._current_state = current_state
        self._last_state = current_state
        self.logger = LoggerFactory.setup(self)

    @property
    def event(self):
        return self._event

    @event.setter
    def event(self, event):
        self._event = event
        self.logger = LoggerFactory.setup(self, event)

    @property
    def current_state(self):
        return self._current_state

    @current_state.setter
    def current_state(self, event):
        self._current_state = State.from_ask_request(event)

    @property
    def user_attributes(self):
        return self._user_attributes

    @user_attributes.setter
    def user_attributes(self, user_attributes):
        self._user_attributes = user_attributes

    @property
    def session_history(self):
        return self._session_history

    @session_history.setter
    def session_history(self, val):
        session_id, maximum_session_history_count = val
        if session_id:
            session_history_from_ddb = self.fetch_session_history(session_id, maximum_session_history_count)
            self._session_history = session_history_from_ddb
        else:
            self._session_history = []

    @property
    def last_state(self):
        return self._last_state

    @last_state.setter
    def last_state(self, event):
        session_id = event.get('session.sessionId', None)
        new_session = event.get('session.new')
        # Load session history from DynamoDB if it's existing session and session_history is None
        if session_id and not new_session and self._session_history is None:
            self._session_history = self.session_history(session_id)
        if len(self._session_history) > 0:
            self._last_state = self._session_history[0]
        else:
            self._last_state = None

    # def create_new_state(self, event: Event, context: Context) -> State:
    def create_new_state(self, event: Event) -> State:
        """
        Create a State from ASK lambda event and context.
        :param event: ASK event
        :param context: ASK context
        :return: State object
        """
        self.current_state = State.from_ask_request(event)
        return self.current_state

    def fetch_current_state(self) -> State:
        """
        Fetch the current State object in the StateManager.
        :return: current State object
        """
        return self.current_state

    def fetch_session_history(self, session_id: str=None, maximum_session_history_count: int=None):
        """
        Fetch session history with the max(maximum_session_history_count, session_total_state_count) session states from DynamoDB for the provided session_id.
        If the provided session_id has more session states than maximal_session_history_count, return the maximal_session_history_count states sorted by creation_timestamp in the descending order.
        :param session_id: session id
        :param maximum_session_history_count: maximum state count for session history.
        :return: a List of State object
        """
        if maximum_session_history_count is None:
            maximum_session_history_count = StateManager.DEFAULT_MAXIMUM_SESSION_HISTORY_COUNT
        if self.table_name:
            if session_id is None:
                return []
            try:
                items = DynamoDbManager.query(table_name=self.table_name,
                                            key_condition=Key('session_id').eq(session_id),
                                            limit = maximum_session_history_count,
                                            scan_index_forward=False)
                return items
            except:
                self.logger.error("Exception when fetching session history from DynamoDB TABLE: " + self.table_name, exc_info=True)
                return []

    def persist_state(self, state: State = None, force_save: bool = True) -> bool:
        """
        Save the provided State object as the current State in the StateManager. If force_save is True, also persist the provided State object to DynamoDB.
        :param state: state object, if None State is passed, use current state object in the State Manager
        :param force_save: whether to persist state record to DynamoDB
        :return: status code, True for success, False for failure
        """
        if self.table_name:
            if state is not None:
                self._current_state = state
            try:
                if force_save:
                    filtered_dict = {}
                    for k, v in self.current_state.__dict__.items():
                        if v is not None and k != 'features':
                            if type(v) not in [str, dict, list, float, int, bool, type(None)]:
                                filtered_dict[k] = v.to_json()
                            else:
                                filtered_dict[k] = v
                        
                    DynamoDbManager.put_item(table_name=self.table_name, item_dict=filtered_dict)
                return True
            except:
                self.logger.error("Exception when persisting state to DynamoDB TABLE: " + self.table_name, exc_info=True)
                return False

# For integ testing:
# sm = StateManager(table_name='StateTableLoadTest', user_attributes=None)
# print(StateManager.DEFAULT_MAXIMUM_SESSION_HISTORY_COUNT)
# StateManager.DEFAULT_MAXIMUM_SESSION_HISTORY_COUNT = 100
# sm.session_history = ('amzn1.echo-api.session.loadtest',200)
# print(len(sm.session_history))
# print(sm.session_history[0].get('creation_date_time'))
# print(sm.session_history[49].get('creation_date_time'))
# print(sm.session_history[99].get('creation_date_time'))