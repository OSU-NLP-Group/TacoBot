import logging

from taco.core.callables import Annotator
from taco.core.state_manager import StateManager
logger = logging.getLogger('tacologger')


class TaskSearch(Annotator):
    name="tasksearch"
    def __init__(self, state_manager: StateManager, timeout=1000, url=None, input_annotations=[]):
        super().__init__(state_manager=state_manager, timeout=timeout, url=url, input_annotations=input_annotations)

    def get_default_response(self, input_data = None):
        return None

    def execute(self, input_data=None):
        """
            tasksearch annotator for tacobot
        """
        user_utterances = [self.state_manager.current_state.text]
        taco_state = self.state_manager.current_state.status
        task_started = getattr(self.state_manager.user_attributes, 'task_started', None)
        top_k = 25
        selected_task = getattr(self.state_manager.user_attributes, 'selected_task', None)
        proposed_tasks = getattr(self.state_manager.user_attributes, 'proposed_tasks', None)

        # {"session_id": "f4125b103fef4b53a616bd8f6788e112", "creation_date_time": "2022-11-07T07:39:39.902953", "history": [], "turn_num": 0, "cache": {}, "pipeline": "", "commit_id": "", "user_id": "1", "text": "", "dialogact": {"probdist": {"hold": 0, "neg_answer": 0, "other_answers": 0, "closing": 0, "correction": 0, "non_complaint": 0, "comment": 0, "nonsense": 0, "yes_no_question": 0, "opening": 0, "appreciation": 0, "command": 0, "clarifying_question": 0, "back-channeling": 0, "abandon": 0, "opinion": 0, "open_question_personal": 0, "uncertain": 0, "dev_command": 0, "complaint": 0, "open_question_opinion": 0, "open_question_factual": 0, "pos_answer": 0, "statement": 0}, "top_1": null, "is_yes_answer": false, "is_no_answer": false, "personal_issue_score": 0.0, "top_2": null}, "navigational_intent": "<NavigationalIntentOutput: pos_intent=False, pos_topic=None, neg_intent=False, neg_topic=None>", "nounphrases": {"user_input_noun_phrases": null, "bot_response_noun_phrases": [], "performance": [0.025118350982666016], "error": false}, "question": {"is_question": false, "question_prob": 0}, "corenlp": {"ner_mentions": [], "sentiment": "<Sentiment.NEUTRAL: 2>", "sentences": [], "nounphrases": [], "verbphrases": [], "nouns": [], "proper_nouns": []}, "taskfilter": {"response": "", "performance": [0.0007150173187255859], "error": false}, "template": {"response": [""], "performance": [0.0020742416381835938], "error": false}, "neuralintent": {"response": null, "performance": [0.0007791519165039062], "error": false}, "mrc": {"response": "", "shouldEndSession": false, "performance": [0.00039124488830566406], "error": false}, "tasktype": {"tasktype": null, "tasktype_pred": {}, "taskname": "", "task_selection": [-1, 0.0], "performance": [0.002221345901489258], "error": false}, "taskname": {"foodname": {"raw_extraction": "", "tokenized_extraction": "", "lemma_expansion": "", "split_expansion": ""}, "taskname": {"raw_extraction": "", "tokenized_extraction": "", "lemma_expansion": "", "split_expansion": ""}, "task_selection": [-1, 0.0], "performance": [0.002624034881591797], "error": false}, "questiontype": {"question_types": ["EVI", "FAQ"], "performance": [5.49167275428772], "error": false}, "faq": {"response": "", "shouldEndSession": false, "profiling": [5.498724807053804, 3.8720508255064487, 1.6264436058700085], "performance": [5.5003743171691895], "error": false}, "recipesearch": null, "tasksearch": null}

        # {"user_id": "1", "user_timezone": null, "taco_state": "MethodNo0of3w1steps_StepAt5", "confirmed_complete": false, "query_result": {"documents": {"list_item_selected": {"recipe": {"ingredients": ["Food and Entertaining", "Recipes", "Baking", "Cookies and Biscuits"]}}}}, "current_step_speak": "Step =  1 Bring a pot of water to boil and cut the paddles into any size you want. Fill a pot that's at least 4 US quarts (3.8 l) in size with water and bring it to a boil over high heat. While the water is heating, cut each of the cactus paddles into pieces or strips. You can slice or cut the cactus paddles into any size you want, but keep the pieces uniform.", "list_item_selected": "list_item_selected", "is_wikihow": false}


        input_data = {'text': user_utterances, 'task_started': task_started, 'top_k': top_k,
                          'selected_task': selected_task, 'proposed_tasks': proposed_tasks}

        if not input_data['text']:
            return self.get_default_response(input_data)

        logger.debug(f'Calling TaskSearch Annotator Remote module with utterances="{user_utterances}"')
        if task_started != True and 'clarification' not in taco_state and 'chat' not in taco_state and self.check_user_said_chatty() == False:
            output = self.remote_call(input_data)
        else:
            output = False
        if output is None:
            default_response = self.get_default_response(input_data)
            logger.info(f'{type(self).__name__} using default response: {default_response}')
            return default_response

        return output
