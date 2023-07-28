"""
A sample TaskBot that demonstrates how to use the CoBot SDK.

User Guide:
* Say a "how" phrase such as "how to paint a wall" to search wikiHow
* Say a "recipe" phrase such as "find some recipes for walnuts" to search for recipes
* Tap on the screen or say "select the first one" to select an article/recipe
* Say "start cooking" to move from recipe ingredients to recipe steps
* Say "next" or "previous" to go to the next ingredient or step in a task
* Say "complete" to mark a task as complete
* Say "resume" to resume an ongoing task
* Say "scroll up/down/left/right" to scroll the display
* Ask "who built you" to test certification compliance
* Say a "timer" phrase such as "set timer for three minutes" to use the Timers API
* Say a "list" phrase such as "add maple syrup to my shopping list" to use the List API
* Say "stop" to exit

"""

import os
import cobot_core as Cobot
from cobot_core.nlp.nlp_modules import PunctuationModule
from cobot_core.service_module import RemoteServiceModule
from cobot_core.service_url_loader import ServiceURLLoader

from taco.dialogue_manager.taco_ranking_strategy import TacoRankingStrategy
from taco.dialogue_manager.taco_response_builder import TacoResponseBuilder
from taco.dialogue_manager.taco_selecting_strategy import TacoSelectingStrategy
from taco.global_intent.taco_global_intent_handler import SampleTaskBotGlobalIntentHandler

from taco.response_modules.exception.sensitive_response_generator.sensitive_response_generator import ResponseGeneratorSensitive
from taco.response_modules.qa.taco_ingredient_qa import ResponseGeneratorIngredientQA

from taco.response_modules.exception.taco_bad_task import TacoBadTask
from taco.response_modules.exception.taco_error import TacoError
from taco.response_modules.exception.taco_help import TacoHelp

from taco.response_modules.choice.taco_choice import TacoChoice
from taco.response_modules.execution.taco_execution import TacoExecution
from taco.response_modules.halt.taco_halt import TacoHalt
from taco.response_modules.qa.taco_step_qa import TacoStepQA
from taco.response_modules.qa.taco_substitute_qa import TacoSubstituteQA
from taco.response_modules.welcome.taco_launch import TacoLaunch
from taco.response_modules.preparation.taco_preparation import TacoPreparation

from taco.response_modules.utils.taco_repeat import TacoRepeat
from taco.response_modules.utils.taco_stop import TacoStop

from taco.response_modules.list.taco_list_management import TacoListManagement
from taco.response_modules.qa.taco_evi import TacoEVI
from taco.response_modules.qa.taco_idk import TacoIDK
from taco.response_modules.timer.taco_timer_management import TacoTimerManagement

'''
The overrides(binder) method you implement in your Cobot instance defines the dialog management strategy used by your 
Cobot, and allows you to customize any aspect of your bot’s behavior by overriding one of the Core library interfaces.
'''
def overrides(binder):
    binder.bind(Cobot.GlobalIntentHandler, to=SampleTaskBotGlobalIntentHandler)  # Use TaskBot welcome prompt
    binder.bind(Cobot.ASRProcessor, to=Cobot.FastASRProcessor)  # Check offensive utterance at response selection
    binder.bind(Cobot.DialogManager, to=Cobot.AdvancedDialogManager)  # Send a dict to ranking strategy
    binder.bind(Cobot.SelectingStrategy, to=TacoSelectingStrategy)  # Simple keyword-matching
    binder.bind(Cobot.RankingStrategy, to=TacoRankingStrategy)  # Custom priority ranking
    binder.bind(Cobot.ResponseBuilder, to=TacoResponseBuilder) # Clean invalid SSML characters


def lambda_handler(event, context):
    # app_id: replace with your ASK skill id to validate ask request. None means skipping ASK request validation.
    # user_table_name: replace with a DynamoDB table name to store user preference data. We will auto create the
    #                  DynamoDB table if the table name doesn’t exist.
    #                  None means user preference data won’t be persisted in DynamoDB.
    # save_before_response: If it is true, skill persists user preference data at the end of each turn.
    #                       Otherwise, only at the last turn of whole session.
    # state_table_name: replace with a DynamoDB table name to store session state data. We will auto create the
    #                   DynamoDB table if the table name doesn’t exist.
    #                   None means session state data won’t be persisted in DynamoDB.
    # overrides: provide custom override for dialog manager components.
    # api_key: replace with your api key

    if os.environ.get('STAGE') == 'PROD':
        user_table_name = 'UserTable'
        state_table_name = 'StateTable'
    else:
        user_table_name = 'UserTableBeta'
        state_table_name = 'StateTableBeta'

    api_key = os.environ.get('API_KEY', 'zwh6kpQgQC4RHqefVdP3n8cwmpSaWzPT7A1OxgFO')

    cobot = Cobot.handler(event,
                          context,
                          app_id="amzn1.ask.skill.3b97dff4-566d-4857-a580-66d12ce3b1f5",
                          user_table_name=user_table_name,
                          save_before_response=True,
                          state_table_name=state_table_name,
                          overrides=overrides,
                          api_key=api_key)

    # Example NLP Modules
    # The punctuation model is a simple Bert model, trained using Cornell movie corpus.
    punctuation = {
        'name': "punctuation",
        'class': PunctuationModule,
        'url': 'local'
    }
    cobot.upsert_module(punctuation)

    # The nounphrases module is a remote module that uses spacy along with an ignore list to extract the relevant noun
    # phrases from the current user utterance and bot response from the previous turn.
    
    noun_phrases = {
        'name': "nounphrases",
        'class': RemoteServiceModule,
        'url': ServiceURLLoader.get_url_for_module("nounphrases"),
        'context_manager_keys': ['text', 'response'],
        'history_turns': 1
    }
    cobot.upsert_module(noun_phrases)

    # The coref module is a remote module that uses neuralcoref to extract the coreference clusters from the previous
    # and current turn.
    # coref = {
    #     'name': "coref",
    #     'class': RemoteServiceModule,
    #     'url': ServiceURLLoader.get_url_for_module("coref"),
    #     'context_manager_keys': ['text', 'response'],
    #     'history_turns': 1
    # }
    # cobot.upsert_module(coref)

    # The intent classification module is a remote module that uses neural model to classify the current user input utterance
    neuralintent = {
        'name': "neuralintent",
        'class': RemoteServiceModule,
        'url': ServiceURLLoader.get_url_for_module("neuralintent"),
        'context_manager_keys': ['text'],
        'history_turns': 1
    }
    cobot.upsert_module(neuralintent)

    asrerror = {
        'name': "asrerror",
        'class': RemoteServiceModule,
        'url': ServiceURLLoader.get_url_for_module("asrerror"),
        'context_manager_keys': ['text'],
        'history_turns': 1
    }
    cobot.upsert_module(asrerror)

    task_search = {
        'name': "tasksearch",
        'class': RemoteServiceModule,
        'url': ServiceURLLoader.get_url_for_module("tasksearch"),
        'context_manager_keys': ['text'],
        'input_user_attributes_keys': ['proposed_tasks', 'selected_task', 'task_started'],
        'history_turns': 1,
        'timeout_in_millis': 2000,
    }
    cobot.upsert_module(task_search)

    recipe_search = {
        'name': "recipesearch",
        'class': RemoteServiceModule,
        'url': ServiceURLLoader.get_url_for_module("recipesearch"),
        'context_manager_keys': ['text'],
        'input_user_attributes_keys': ['proposed_tasks', 'selected_task', 'task_started', 'taco_state', 'search_request'],
        'history_turns': 1,
        'timeout_in_millis': 2500,
    }
    cobot.upsert_module(recipe_search)

    docparse = {
        'name': "docparse",
        'class': RemoteServiceModule,
        'url': ServiceURLLoader.get_url_for_module("docparse"),
        'context_manager_keys': ['text'],
        'input_user_attributes_keys': ['query_result', 'list_item_selected', 'is_wikihow', 'current_task_docparse'],
        'history_turns': 1
    }
    cobot.upsert_module(docparse)

    task_type = {
        'name': "tasktype",
        'class': RemoteServiceModule,
        'url': ServiceURLLoader.get_url_for_module("tasktype"),
        'context_manager_keys': ['text'],
        'history_turns': 1
    }
    cobot.upsert_module(task_type)

    question_type = {
        'name': "questiontype",
        'class': RemoteServiceModule,
        'url': ServiceURLLoader.get_url_for_module("questiontype"),
        'context_manager_keys': ['text'],
        'input_user_attributes_keys': ['current_step_details'],
        'history_turns': 1
    }
    cobot.upsert_module(question_type)

    nlp_def = [
        ["nounphrases", "punctuation", "neuralintent",  "tasktype", "asrerror", "tasksearch", "recipesearch", "docparse", "questiontype"]
    ]
    cobot.create_nlp_pipeline(nlp_def)

    launch_responder = {
        'name': "LAUNCH_RESPONDER",
        'class': TacoLaunch,
        'url': 'local'
    }

    timer_management_responder = {
        'name': "TIMER_MANAGEMENT_RESPONDER",
        'class': TacoTimerManagement,
        'url': 'local'
    }

    list_management_responder = {
        'name': "LIST_MANAGEMENT_RESPONDER",
        'class': TacoListManagement,
        'url': 'local'
    }

    choice_responder = {
        'name': "CHOICE_RESPONDER",
        'class': TacoChoice,
        'url': 'local'
    }

    execution_responder = {
        'name': "EXECUTION_RESPONDER",
        'class': TacoExecution,
        'url': 'local'
    }

    sensitive_responder = {
        'name': "SENSITIVE_RESPONDER",
        'class': ResponseGeneratorSensitive,
        'url': 'local'
    }

    error_responder = {
        'name': "ERROR_RESPONDER",
        'class': TacoError,
        'url': 'local'
    }
    
    preparation_responder = {
        'name': "PREPARATION_RESPONDER",
        'class': TacoPreparation,
        'url': 'local'
    }

    halt_responder = {
        'name': "HALT_RESPONDER",
        'class': TacoHalt,
        'url': 'local'
    }

    repeat_responder = {
        'name': "REPEAT_RESPONDER",
        'class': TacoRepeat,
        'url': 'local'
    }

    evi_responder = {
        'name': "EVI_RESPONDER",
        'class': TacoEVI,
        'url': 'local'
    }

    idk_responder = {
        'name': "IDK_RESPONDER",
        'class': TacoIDK,
        'url': 'local'
    }

    help_responder = {
        'name': "HELP_RESPONDER",
        'class': TacoHelp,
        'url': 'local'
    }

    bad_task_responder = {
        'name': "BAD_TASK_RESPONDER",
        'class': TacoBadTask,
        'url': 'local'
    }

    ingredient_qa_responder = {
        'name': "INGREDIENT_QA_RESPONDER",
        'class': ResponseGeneratorIngredientQA,
        'url': 'local'
    }

    step_qa_responder = {
        'name': "STEP_QA_RESPONDER",
        'class': TacoStepQA,
        'url': 'local'
    }

    substitute_qa_responder = {
        'name': "SUB_QA_RESPONDER",
        'class': TacoSubstituteQA,
        'url': 'local'
    }

    stop_responder = {
        'name': "STOP_RESPONDER",
        'class': TacoStop,
        'url': 'local'
    }

    # chat_responder = {
        # 'name': "chatbot",
        # 'class': RemoteServiceModule,
        # 'context_manager_keys': ['text', 'response'],
        # 'url': ServiceURLLoader.get_url_for_module("chatbot"),
        # 'history_turns': 3,
        # 'timeout_in_millis': 3000,
    # }
    # cobot.upsert_module(chat_responder)

    mrc_responder = {
        'name': "mrc",
        'class': RemoteServiceModule,
        'url': ServiceURLLoader.get_url_for_module("mrc"),
        'context_manager_keys': ['text'],
        'input_user_attributes_keys': ['current_step_details', 'current_step_speak', 'is_wikihow', 'taco_state', 'last_taco_state'],
        'history_turns': 1
    }
    cobot.upsert_module(mrc_responder)


    faq_responder = {
        'name': "faq",
        'class': RemoteServiceModule,
        'url': ServiceURLLoader.get_url_for_module("faq"),
        'context_manager_keys': ['text'],
        'history_turns': 1
    }
    cobot.upsert_module(faq_responder)
    
    #inappropriate_responder = {
    #    'name': "taskfilter",
    #    'class': RemoteServiceModule,
    #    'url': ServiceURLLoader.get_url_for_module("taskfilter"),
    #    'context_manager_keys': ['text'],
    #    'history_turns': 1,
    #    'timeout_in_millis': 3000,
    #}
    #cobot.upsert_module(inappropriate_responder)

    cobot.add_response_generators([launch_responder, 
                                   timer_management_responder, 
                                   list_management_responder, 
                                   choice_responder, 
                                   execution_responder,
                                   sensitive_responder,
                                   preparation_responder,
                                   halt_responder,
                                   stop_responder,
                                   mrc_responder,
                                   repeat_responder,
                                   error_responder,
                                   #inappropriate_responder,
                                   evi_responder,
                                   idk_responder,
                                   help_responder,
                                   bad_task_responder,
                                   ingredient_qa_responder,
                                   step_qa_responder,
                                   substitute_qa_responder,
                                   faq_responder])
    
    return cobot.execute()

# if __name__ == '__main__':
#     lambda_handler(event=event, context={})