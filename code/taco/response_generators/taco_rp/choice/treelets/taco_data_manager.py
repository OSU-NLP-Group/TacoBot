from taco.response_generators.taco_rp.choice.treelets.utils.general import get_constraints, set_query_user_attributes
from taco.response_generators.taco_rp.choice.state import *
import json
import random
import logging
from profanity_check import predict
# pip install alt-profanity-check

logger = logging.getLogger('tacologger')

def manage_search_data(current_state, last_state, user_attributes):
	text = getattr(current_state, 'text', '')
	intent = getattr(current_state, 'parsed_intent', '')
	query = getattr(user_attributes, 'query', '')
	is_wikihow = getattr(user_attributes, 'is_wikihow', None)
	if intent == 'ClarifyIntent':
		constraint = get_constraints(current_state)
		if constraint is None:
			return None


	query_result = None
	if not query or intent == 'RecommendIntent':
		setattr(current_state, 'is_rec', True)
		if any(kwd in text for kwd in ['recipe', 'cook', 'food']):
			query_result = select_recipe_recommendation(current_state, user_attributes)
			setattr(user_attributes, 'is_wikihow', False)
		elif not text:
			# Touch User Event. Roll a dice. 
			if random.random() < 0.5:
				query_result = select_recipe_recommendation(current_state, user_attributes)
				setattr(user_attributes, 'is_wikihow', False)
			else:
				query_result = get_task_recommendation()
				setattr(user_attributes, 'is_wikihow', True)
		else:
			query_result = get_task_recommendation()
			setattr(user_attributes, 'is_wikihow', True)
	else:
		wikihow_search = getattr(current_state, 'tasksearch', None)
		recipe_search = getattr(current_state, 'recipesearch', None)


		wikihow_query_result, recipe_query_result = read_search_results(
			wikihow_search, 
			recipe_search
		)

		if is_wikihow:
			if len(wikihow_query_result) > 0:
				query_result = wikihow_query_result
			else:
				query_result = get_task_recommendation()
				setattr(current_state, 'is_rec', True)
				setattr(current_state, 'search_timeout', True)

		else:
			if len(recipe_query_result['documents']) > 0:
				query_result = recipe_query_result
				if intent == 'ClarifyIntent':
					setattr(current_state, 'clarify', True)
				else:
					setattr(current_state, 'clarify', False)
					store_wikihow_summary(wikihow_query_result, user_attributes)
			# recipe queries can check wikihow results, but not vice versa
			elif intent != 'ClarifyIntent':
				if len(wikihow_query_result) > 0:
					print('[data management] Recipe failed, use WikiHow as backup!')
					query_result = wikihow_query_result
					setattr(user_attributes, 'is_wikihow', True)
				else:
					query_result = select_recipe_recommendation(current_state, user_attributes)
					setattr(current_state, 'is_rec', True)
					setattr(current_state, 'search_timeout', True)


#     print('query_result = ', query_result)
	setattr(user_attributes, 'first_visit', True)
	set_query_user_attributes(query_result, user_attributes, is_new_search=True)

	# logger.taco_merge(f'1 user_attributes.query_result = {repr(user_attributes.query_result)[:200]}')


def read_search_results(wikihow_search, recipe_search):
	wikihow_query_result = []
	recipe_query_result = {'documents': []}
		
	if (wikihow_search is not None and
			'ranked_tasks' in wikihow_search and
			len(wikihow_search['ranked_tasks']) > 0
	):
		wikihow_query_result = filter_bad_results(
				wikihow_search['ranked_tasks']
			)
		
	if (recipe_search is not None and
			'ranked_recipes' in recipe_search and
			len(recipe_search['ranked_recipes']['documents']) > 0
	):
		recipe_query_result = recipe_search['ranked_recipes']

	return wikihow_query_result, recipe_query_result


def store_wikihow_summary(wikihow_query_result, user_attributes):
	if len(wikihow_query_result) > 0:
		if wikihow_query_result[0]["_source"]["hasSummary"]:
			setattr(
				user_attributes, 
				'wikihow_summary', 
				wikihow_query_result[0]["_source"]["summaryText"]
			)
		else:
			setattr(user_attributes, 'wikihow_summary', '')
	else:
		setattr(user_attributes, 'wikihow_summary', '')

def get_task_recommendation():

	cache = json.load(open('taco/response_generators/taco_rp/choice/data/example_cache.json'))
	recommend_tasks = cache['recommend_tasks']
	random.shuffle(recommend_tasks)
	return recommend_tasks



def select_recipe_recommendation(current_state, user_attributes):
	cache = json.load(open('taco/response_generators/taco_rp/choice/data/example_cache.json'))
	recommend_recipes = cache['recommend_recipes']

	hour = getattr(user_attributes, "hour_of_day", 0)
	category = get_recipe_category(hour)

	query_result = recommend_recipes[category]
	random.shuffle(query_result['documents'])
	setattr(current_state, 'recipe_rec_cat', category)
	return query_result

def get_recipe_category(hour):
	if hour in [7, 8]:
		return 'breakfast'
	elif hour in [9, 10]:
		return 'brunch'
	elif hour in [11, 12]:
		return 'lunch'
	elif hour in [18, 19]:
		return 'dinner'
	else:
		return random.choice(['dessert', 'snack', 'smoothie'])


def filter_bad_results(wikihow_query_result):
	titles = [result["_source"]["articleTitle"] for result in wikihow_query_result]
	filtered_results = []
	need_filter = []

	try:
		need_filter = list(predict(titles))
		filtered_results = [
			wikihow_query_result[i] 
			for i in range(len(need_filter)) 
			if need_filter[i] == 0
		]
	except:
		filtered_results = wikihow_query_result
	
	return filtered_results
