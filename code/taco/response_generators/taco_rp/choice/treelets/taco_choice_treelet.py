import logging
import copy
from taco.core.regex.regex_template import RegexTemplate
from taco.response_generators.food.regex_templates import DoubtfulTemplate
from taco.core.response_generator_datatypes import PromptType, ResponseGeneratorResult, PromptResult, AnswerType
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.entity_linker.entity_groups import ENTITY_GROUPS_FOR_EXPECTED_TYPE
from taco.core.response_generator import Treelet
from taco.core.entity_linker.entity_groups import EntityGroupsForExpectedType
from taco.core.util import infl
from cobot_core.service_module import ToolkitServiceModule

from taco.response_generators.taco_rp.taco_intent_by_rule import TacoIntentByRule
import json

import random

from taco.core.state import State as Cur_State
from taco.core.user_attributes import UserAttributes as Cur_UserAttributes

from taco.response_generators.taco_rp.choice.treelets import template_manager
from taco.response_generators.taco_rp.choice.treelets.taco_choice_compare import taco_recipe_compare, taco_wikihow_compare
from taco.response_generators.taco_rp.choice.treelets.taco_data_manager import manage_search_data
from taco.response_generators.taco_rp.choice.treelets.taco_wikihow_choice import taco_wikihow_choice
from taco.response_generators.taco_rp.choice.treelets.taco_recipe_choice import taco_recipe_choice
from taco.response_generators.taco_rp.choice.treelets.utils.general import get_and_list_prompt

from taco.response_generators.taco_rp.choice.state import *

logger = logging.getLogger('tacologger')

def get_choice_compare_response(current_state, last_state, user_attributes, toolkit_service_client):
	is_wikihow = getattr(user_attributes, 'is_wikihow', None)

	if is_wikihow:
		return taco_wikihow_compare(current_state, last_state, user_attributes, toolkit_service_client)
	else:
		return taco_recipe_compare(current_state, last_state, user_attributes, toolkit_service_client)


def get_choice_catalog_response(current_state, last_state, user_attributes, toolkit_service_client):
	is_wikihow = getattr(user_attributes, 'is_wikihow', None)

	if is_wikihow:
		return taco_wikihow_choice(current_state, last_state, user_attributes, toolkit_service_client)
	else:
		return taco_recipe_choice(current_state, last_state, user_attributes, toolkit_service_client)


def get_clarification_question_response(current_state, last_state, user_attributes, toolkit_service_client):
	query = getattr(user_attributes, 'query', '')
	recipesearch = getattr(current_state, 'recipesearch', None)
	attributes_to_clarify = recipesearch['attributes_to_clarify']
	request_dict = recipesearch['request']
	setattr(user_attributes, 'search_request', request_dict)

	speakout = template_manager.help_with_query(recipe=True, has_query=bool(query)).substitute(query=query)
	# if 'diets' in attributes_to_clarify:
	#     attr_str = get_and_list_prompt(attributes_to_clarify['diets'])
	#     speakout += 'Do you have any diet constraints? Such as ' + attr_str + '. '
	# else:
	#     attr_str = get_and_list_prompt(attributes_to_clarify['cuisines'])
	#     speakout += 'Do you have any preference on cuisines? Such as ' + attr_str + '. '

	if attributes_to_clarify:
		nutrition = list(attributes_to_clarify.keys())[0]
		levels = attributes_to_clarify[nutrition]

		prompt_text = ""
		for i, level in enumerate(levels):
			if i != len(levels) - 1:
				prompt_text += level + ', '
			else:
				prompt_text += 'or ' + level
		
		speakout += "What level of %s in the recipe would you prefer, %s?"%(nutrition, prompt_text)


	return {'response': speakout, 'shouldEndSession': False}


def select_choice_response(current_state, last_state, user_attributes, toolkit_service_client):
	intent = getattr(current_state, 'parsed_intent', None)
	query_result = getattr(user_attributes, 'query_result', None)

	# logger.taco_merge(f'intent = {intent}, query_result = {query_result}')

	if intent in ['TaskRequestIntent', 'RecommendIntent', 'UserEvent', 'ClarifyIntent'] or query_result is None:
#       print('manage_search_data')
		manage_search_data(current_state, last_state, user_attributes, toolkit_service_client)

	if 'Comparison' in current_state.status:
		return get_choice_compare_response(current_state, last_state, user_attributes, toolkit_service_client)
	elif 'Catalog' in current_state.status:
		return get_choice_catalog_response(current_state, last_state, user_attributes, toolkit_service_client)
	elif 'Clarification' in current_state.status:
		return get_clarification_question_response(current_state, last_state, user_attributes, toolkit_service_client)



class Taco_choice_Treelet(Treelet):
	name = "Taco_choice_Treelet"

	def classify_user_response(self):
		assert False, "This should never be called."


	def get_response(self, state_manager, priority=ResponsePriority.CAN_START, **kwargs) -> ResponseGeneratorResult:
		""" Returns the response. """
		
		state, utterance, response_types = self.get_state_utterance_response_types()

		name_ToolkitServiceModule = ToolkitServiceModule
		
		current_state = state_manager.current_state
		last_state = state_manager.last_state
		user_attributes = state_manager.user_attributes
		toolkit_service_client = name_ToolkitServiceModule.toolkit_service_client
		conditionalState = ConditionalState()

		n_current_state = Cur_State.deserialize(current_state.serialize(logger_print=False))
		n_user_attributes = Cur_UserAttributes.deserialize(user_attributes.serialize(logger_print=False))

		response_state = select_choice_response(
			n_current_state, 
			last_state, 
			n_user_attributes,
			toolkit_service_client
		)
		
		response = response_state['response']

		return ResponseGeneratorResult(text=response, priority=priority,
									   needs_prompt=False, state=state, cur_entity=None,
									   conditional_state=ConditionalState(
										   prev_treelet_str=self.name,
										   n_current_state=n_current_state,
										   n_user_attributes=n_user_attributes
										   ))
		

	def treet_update_current_state(self, state_manager, conditional_state):
		assert state_manager is not None, "state_manager should not be None for updating the current state"
		assert conditional_state is not None, "conditional_state should not be None if the response/prompt was chosen"

		logger.taco_merge(f'choice treet_update_current_state and user_attributes')
		# print('conditional_state.n_user_attributes = ', repr(getattr(conditional_state.n_user_attributes, 'query_result', ''))[:100])
		# print('cstate_manager.user_attributes = ', repr(getattr(state_manager.user_attributes, 'query_result', ''))[:100])
		# state_manager.current_state   = conditional_state.n_current_state
		# state_manager.user_attributes = conditional_state.n_user_attributes

		# current_state
		for k in ['recipe_rec_cat', 'clarify', 'is_rec', 'search_timeout', 'no_result']:
			v = getattr(conditional_state.n_current_state, k, None)
			if v != None:
				setattr(state_manager.current_state, k, v)
		# user_attributes
		for k in ['search_request', 'list_item_rec', 'wikihow_summary', 'is_wikihow', 'first_visit', 'cont_reqs', 'query_result', 'current_task', 'current_step', 'current_step_details', 'current_part', 'current_task_docparse', 'list_item_selected', 'started_cooking', 'choice_start_idx', 'proposed_tasks' ]:
			v = getattr(conditional_state.n_user_attributes, k, None)
			if v != None:
				setattr(state_manager.user_attributes, k, v)

		conditional_state.n_current_state = None
		conditional_state.n_user_attributes = None

		# setattr(current_state, 'recipe_rec_cat', category)
		# setattr(current_state, 'clarify', True)
		# setattr(current_state, 'is_rec', True)
		# setattr(current_state, 'search_timeout', True)
		# setattr(current_state, 'no_result', True)

		# setattr(user_attributes, 'first_visit', False)
		# setattr(user_attributes, 'cont_reqs', 0)
		# setattr(user_attributes, 'list_item_rec', idx_max_views)
		# setattr(user_attributes, 'wikihow_summary', '')
		# setattr(user_attributes, 'is_wikihow', False)
		# setattr(user_attributes, 'current_task', None)
		# setattr(user_attributes, 'current_step', None)
		# setattr(user_attributes, 'current_step_details', [])
		# setattr(user_attributes, 'current_part', None)
		# setattr(user_attributes, 'current_task_docparse', None)
		# setattr(user_attributes, 'list_item_selected', -1)
		# setattr(user_attributes, 'started_cooking', None)
		# setattr(user_attributes, 'choice_start_idx', 0)
		# setattr(user_attributes, 'proposed_tasks', [])
		# setattr(user_attributes, 'list_item_rec', -1)
