"""
This module uses spacy along with an ignore list to extract the relevant noun phrases from the current user utterance
and bot response from the previous turn.
"""
import spacy
import re
from opensearchpy import OpenSearch

import concurrent.futures

import splitter

from transformers import AutoTokenizer, AutoModelForQuestionAnswering
from transformers import AutoModel, AutoConfig
from transformers.models.roberta.modeling_roberta import RobertaPreTrainedModel
from transformers.modeling_outputs import SequenceClassifierOutput
import torch
import os
import json
import numpy as np
from torch import nn
import torch.nn.functional as F
import pickle
import re
import copy

from cobot_common.service_client import get_client
from reranker.model import SearchQueryRanker

from time import perf_counter

# Client object
client = get_client(api_key='zwh6kpQgQC4RHqefVdP3n8cwmpSaWzPT7A1OxgFO', timeout_in_millis=2000)

required_context = ['text']
nlp = spacy.load('en_core_web_sm')
stopwords = nlp.Defaults.stop_words
stopwords |= {'one', 'two', 'three', 'first', 'second', 'third'}
stopwords |= {'suggest', 'suggestions', 'suggestion', 'recommendation', 'recommendations', 'recommend', 'search' ,'like', 'want', \
        'a', 'about', 'let', 'need', 'prefer', 'try', 'an', 'favourites', 'favorites', 'favourite', 'favorite', 'may', 'be', 'maybe', \
        'yourself', 'myself', \
        'tips', 'tip', 'prepare','recipes', 'recipe', 'task', 'tasks', 'diy', 'ingredients', 'ingredient', 'cook', 'cooking', 'make', 'instruction', 'instructions', 'project', 'projects', \
        'something', 'thing', 'things', 'anything', 'else', 'different', 'other', 'another', 'special'}

recipe_keywords = {'recipe', 'recipes', 'cook', 'cooking'}


def clean_utterance(utterance, for_cls=False):
    utterance = utterance.lower()
    for noise in ['actually', 'hmm', 'oh', 'uh', 'uhhh', 'well', "please", "alexa", "echo"]:
#         utterance = utterance.replace(noise, " ")
        utterance = re.sub(r"\b"+noise+r"\b", '', utterance)
    utterance = re.sub(r'\bd\.*\s*i\.*\s*y\.*', 'diy', utterance)
    if for_cls:
        for noise in ['a', 'an', 'my', 'your', 'the']:
    #         utterance = utterance.replace(noise, " ")
            utterance = re.sub(r"\b"+noise+r"\b", '', utterance)
    utterance = re.sub(r'\s+', " ",utterance)
    return utterance.strip().strip('?.,')

def get_required_context():
    return required_context

def handle_message(msg):
    initial_start = perf_counter()
    total_time = extraction_time = search_time = local_search_time = rerank_time = 0
    
    taskname = {
        'raw_extraction': '',
        'tokenized_extraction': '',
        'lemma_expansion': '',
        'split_expansion': ''
    }
    request = {
        "dishName": '',
        "dietaryFilters": [],
        "cuisines": [],
        "mealType": '',
        'extra_nouns_searched': [],
        'simplified_query': ''
    }
    selection = [-1, 0.0]
    ranked_tasks = {'documents': []}
    error = []
    search_errors = []
    attributes_to_clarify = None
    satisfied_constraints = None
    
    extraction_start = perf_counter()
    # checks if any noun phrases are in the ignore list
    # most recent user utterance
    input_text = clean_utterance(msg['text'][0])
    taco_state = msg.get('taco_state', None)
    candidate_tasks = []

    if len(input_text) > 0:
        input_doc = nlp(input_text)
        if taco_state is not None and 'TaskClarification' in taco_state:
            # search_start = perf_counter()

            request = msg.get('search_request', None)
            if request:
                try:
                    candidate_tasks, request, constraints_found, search_time, local_search_time, search_errors = search_with_clarification(request, input_doc)
                except:
                    error.append('recipe clarification search error')
                    candidate_tasks = []
            # search_time = perf_counter() - search_start

            if len(candidate_tasks) > 0:
                satisfied_constraints = constraints_found
        else:
            # no need to execute every time
            if not msg.get('task_started', False):
                try:
                    taskname = taskname_extraction(input_text, input_doc)
                except:
                    error.append('task extraction error')
                    taskname = {
                            'raw_extraction': '',
                            'tokenized_extraction': '',
                            'lemma_expansion': '',
                            'split_expansion': '',
                            'simplified_query': '',
                            'recipe_attributes': {},
                            'recipe_nouns': [],
                            'attribute_free_extraction': '',
                        }
                extraction_time = perf_counter() - extraction_start
                # search_start = perf_counter()
                
                if taskname['raw_extraction']:
                    try:
                        candidate_tasks, request, search_time, local_search_time, search_errors = search(taskname)
                    except:
                        error.append('recipe search error')
                        
                    # search_time = perf_counter() - search_start
    
        rerank_start = perf_counter()
        if len(candidate_tasks) > 0:
            try:
                scores = rerank(taskname['lemma_expansion'], candidate_tasks)
                ranked_tasks['documents'] = sorted(candidate_tasks, key=lambda task:scores[candidate_tasks.index(task)], reverse=True)
            except:
                error.append('rerank error')
                ranked_tasks['documents'] = candidate_tasks

            # only return top 10
            if len(ranked_tasks['documents']) > 9:
                ranked_tasks['documents'] = ranked_tasks['documents'][:9]

        rerank_time = perf_counter()-rerank_start

        if 'TaskClarification' not in taco_state and len(request['dietaryFilters']) == 0 and len(request['cuisines']) == 0:
            cuisines, diets = get_clarification_attrs(ranked_tasks['documents'])
            # The condition of determining whether trigger clarification or not; 
            # If trigger, ask diet constraint or cuisine
            attribute, sample_values = diet_or_cuisine(diets, cuisines)
            if attribute and sample_values and (attribute == 'diets' or attribute == 'cuisines'):
                attributes_to_clarify = {attribute: sample_values}
                
        # if msg.get('selected_task', None) is None and msg.get('proposed_tasks', None) is not None and msg.get('proposed_tasks', None):
            
        #     selection_start = perf_counter()
            
        #     try:
        #         if len(msg['proposed_tasks'])>0:
        #             selection = task_selection(input_doc, [re.sub(r'\bhow to\b','',task['title'].lower().strip('?.')) for task in msg['proposed_tasks']])
        #         else:
        #             selection = [-1, 0.0]
        #     except:
        #         selection = [-1, 0.0]
        #         error.append('selection error')
            
        #     selection_time = perf_counter() - selection_start
            
    total_time = perf_counter() - initial_start
    error += search_errors

    return {
        'recipename': taskname, 
        'request': request,
        'recipe_selection': selection, 
        'ranked_recipes': ranked_tasks, 
        'attributes_to_clarify': attributes_to_clarify,
        'satisfied_constraints': satisfied_constraints,
        'module_error': '; '.join(error) if len(error) > 0 else '', 
        'profiling': [total_time, extraction_time, search_time, local_search_time, rerank_time] #, selection_time]
    }


with open('/deploy/app/data/cleaned_cooking_verbs.json', 'r') as f:
    cooking_verbs = set(json.load(f))
with open('/deploy/app/data/cleaned_cooking_nouns.json', 'r') as f:
    cooking_nouns = {i:set(nouns) for i,nouns in json.load(f).items()}

print("loading extraction model")

tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
device = 'cuda' if torch.cuda.is_available() else 'cpu'

# checkpoint = "/deploy/app/checkpoint/diy_extractor_checkpoint"
# diy_extraction_model = AutoModelForQuestionAnswering.from_pretrained(checkpoint, config=AutoConfig.from_pretrained(checkpoint)).to(device)
# diy_extraction_model.eval()

checkpoint = "/deploy/app/checkpoint/pos_recipe_cpt"
recipe_extraction_model = AutoModelForQuestionAnswering.from_pretrained(checkpoint, config=AutoConfig.from_pretrained(checkpoint)).to(device)
recipe_extraction_model.eval()
print("extraction model loaded")

# rerank_model = SearchQueryRanker().to(device)
# if device == 'cpu':
#     rerank_model.load_state_dict(torch.load("checkpoint/diy_reranker.pt",  map_location=torch.device('cpu')))
# else:
#     rerank_model.load_state_dict(torch.load("checkpoint/diy_reranker.pt"))
# rerank_model.eval()
# print("reranking model loaded")

attributes = {
    'diets': {
        'whole30': ['whole30'],
        'fish free': ['fish free', 'fish-free'],
        'alcohol free': ['alcohol free', 'alcohol-free'],
        'healthy': ['healthy'],
        'tree nut free': ['tree nut free', 'tree nut-free'],
        'pescatarian': ['pescatarian'],
        'sugar free': ['sugar free', 'sugar-free'],
        'peanut free': ['peanut free', 'peanut-free'],
        'sugar conscious': ['sugar conscious'],
        'dairy free': ['dairy free', 'dairy-free'],
        'red meat free': ['red meat free', 'red_meat_free'],
        'kidney friendly': ['kidney friendly', 'kidney_friendly'],
        'fat free': ['fat free', 'fat-free'],
        'nut free': ['nut free', 'nut-free'],
        'keto': ['keto'],
        'gluten free': ['gluten free', 'gluten-free'],
        'raw': ['raw'],
        'light': ['light'],
        'low fat': ['low fat', 'low-fat'],
        'meatless': ['meatless', 'do not eat meat', "don't eat meat"],
        'low carb': ['low carb', 'low-carb'],
        'wheat free': ['wheat free', 'wheat-free'],
        'paleo friendly': ['paleo friendly'],
        'egg free': ['egg free', 'egg-free'],
        'vegetarian': ['vegetarian'],
        'tomato free': ['tomato free', 'tomato-free'],
        'keto friendly': ['keto friendly'],
        'grain free': ['grain free', 'grain-free'],
        'low sodium': ['low sodium', 'low-sodium'],
        'pork free': ['pork free', 'pork-free'],
        'health starts here': ['health starts here'],
        'shellfish free': ['shellfish free', 'shellfish-free'],
        'lactose free': ['lactose free', 'lactose-free'],
        'no added sugar': ['no added sugar'],
        'high fiber': ['high fiber'],
        'soy free': ['soy free', 'soy-free'],
        'paleo': ['paleo'],
        'low potassium': ['low potassium', 'low_potassium', 'low-potassium'],
        'vegan': ['vegan'],
        'sesame free': ['sesame free', 'sesame_free', 'sesame-free'],
        'mollusk free': ['mollusk free', 'mollusk_free', 'mollusk-free']
        },
    'cuisines': {
        'Korean': ['korean'],
        'Turkish': ['turkish'],
        'Japanese': ['japanese'],
        'New Orleans, Southern': ['new orleans'],
        'Global': ['global'],
        'Mexican': ['mexican'],
        'Cuban': ['cuban'],
        'Italian': ['italian'],
        'Caesar': ['caesar'],
        'Asian': ['asian'],
        'Vietnamese': ['vietnamese'],
        'Mexican and Tex-Mex': ['mexican and tex-mex', 'mexican', 'tex-mex'],
        'Baked': ['baked'],
        'Hungarian': ['hungarian'],
        'Indian': ['indian'],
        'Thai': ['thai'],
        'British': ['british'],
        'Tex-Mex': ['tex-mex'],
        'French': ['french'],
        'Filipino': ['filipino'],
        'Mediterranean': ['mediterranean'],
        'Easter': ['easter'],
        'Southern': ['southern'],
        'German': ['german'],
        'Chinese': ['chinese'],
        'Cajun, Creole': ['cajun', 'creole'],
        'Beyond Curry': ['beyond curry'],
        'Basque': ['basque'],
        'Greek': ['greek'],
        'European': ['european'],
        'Southeast Asian': ['southeast asian'],
        'Southwestern': ['southwestern'],
        'Middle Eastern': ['middle eastern'],
        'Irish': ['irish'],
        'American': ['american'],
        'Central/South American': ['central american', 'central south american','south american', 'southern american'],
        'Russian': ['russian'],
        'Cajun, Southern': ['cajun, southern', 'southern cajun', 'south cajun'],
        'Caribbean': ['caribbean'],
        'Southern American': ['southern american', 'south american'],
        'Jewish': ['jewish'],
        'African': ['african'],
        'Spanish': ['spanish']
        },
    'mealType': {
        'brunch': ['brunch'],
        'starter': ['starter'],
        'dinner': ['dinner'],
        'appetizers': ['appetizers'],
        'side': ['side'],
        'sandwiches': ['sandwiches'],
        'breakfast and brunch': ['breakfast and brunch', 'breakfast', 'brunch'],
        'snacks': ['snacks'],
        'desserts': ['desserts'],
        'main': ['main'],
        'appetizer': ['appetizer'],
        'beverage': ['beverage'],
        'salads': ['salads'],
        'dessert': ['dessert'],
        'desserts or baked goods': ['dessert', 'baked'],
        'dressings, sauces and condiments': ['dressing', 'sauce', 'condiment'],
        'breakfast': ['breakfast'],
        'soups and stews': ['soup', 'stew'],
        'side dishes': ['side dishes'],
        'drinks': ['drinks'],
        'breads and muffins': ['bread', 'muffin'],
        'lunch': ['lunch'],
        'main dishes': ['main dishes']
        }
}

from spacy.matcher import PhraseMatcher

attribute_matcher = PhraseMatcher(nlp.vocab, attr="LEMMA")
for attribute, kvs in attributes.items():
    for k, vs in kvs.items():
        patterns = [nlp(v) for v in vs]
        attribute_matcher.add(f"{attribute}_{k}", patterns)
        
with open('/deploy/app/data/common_food_recipes.json', 'r') as f:
    common_food_recipes = json.load(f)
with open('/deploy/app/data/common_food_name_to_id.json', 'r') as f:
    common_food_name_to_id = json.load(f)
print("common food database loaded")
    
noun_matcher = PhraseMatcher(nlp.vocab, attr="LEMMA")
for noun, noun_doc in zip(common_food_name_to_id.keys(), nlp.pipe(list(common_food_name_to_id.keys()))):
    patterns = [noun_doc]
    noun_matcher.add(noun, patterns)

def taskname_extraction(utterance, utterance_doc):
    model = recipe_extraction_model
        
    question = "task name"
    inputs = tokenizer.encode_plus(question, utterance, return_tensors = "pt").to(device)

    with torch.no_grad():
        answer_start_scores, answer_end_scores = model(**inputs, return_dict = False)      
        answer_start_scores = answer_start_scores.exp()
        answer_end_scores = answer_end_scores.exp()
        answer_scores = answer_start_scores.transpose(0,1) + answer_end_scores
        answer_scores *= inputs['token_type_ids']
        answer_scores = torch.triu(answer_scores)-torch.triu(answer_scores,diagonal=30)
        max_p, answer_loc = torch.max(answer_scores.reshape(-1), dim=-1)
        answer_start = torch.floor(answer_loc.float()/answer_scores.shape[-1]).int()
        answer_end = torch.remainder(answer_loc, answer_scores.shape[-1]).int()+1
    

    extraction = tokenizer.convert_tokens_to_string(tokenizer.convert_ids_to_tokens(inputs["input_ids"][0][answer_start:answer_end])).replace('[SEP]', '').strip()
    extraction = re.sub(r'\brecipe[s]?|style|type\b', '', extraction).rstrip()
    extraction = re.sub(r'\[.*?\]', '', extraction)
    doc_extraction = nlp(extraction)
    tokenized_extraction = ' '.join([token.text for token in doc_extraction])
    lemma_extraction = [token.lemma_ for token in doc_extraction if token.text not in stopwords and token.lemma_ not in stopwords]
    
    extraction_expansion = expand_query(doc_extraction)
    
    #if type=='recipe':
    extra_lemmas = []
    extra_split_words = []
    for token in utterance_doc:
        if token.pos_=='VERB' and token.lemma_ in cooking_verbs and token.lemma_ not in {'make', 'cook', 'eat'} and token.text not in extraction:
            extraction = token.lemma_ + ' ' + extraction
            tokenized_extraction = token.lemma_ + ' ' + tokenized_extraction
            extra_lemmas.append(token.lemma_)
            split_word = splitter.split(token.text)
            if isinstance(split_word, list) and (len(split_word) > 1 or split_word[0]!=token.text):
                extra_split_words.extend(split_word)
    if len(extra_lemmas) > 0:
        extraction_expansion['lemmas'].extend(extra_lemmas)
    if len(extra_split_words) > 0:
        extraction_expansion['split'].extend(extra_split_words)
    
    query_attributes = {}
    attribute_free_extraction = extraction
    for match_id, start, end in attribute_matcher(utterance_doc):
        attribute, key = nlp.vocab.strings[match_id].split('_')
        attribute_free_extraction = attribute_free_extraction.replace(utterance_doc[start:end].text, '')
        if attribute not in query_attributes:
            query_attributes[attribute] = [key]
        else:
            query_attributes[attribute].append(key)
    attribute_free_extraction = re.sub(r'\s+', ' ', attribute_free_extraction)
    nouns_in_query = []
    for match_id, start, end in noun_matcher(doc_extraction):
        noun = nlp.vocab.strings[match_id]
        nouns_in_query.append(noun)
    
    
    if len(lemma_extraction)>0:
        return {
            'raw_extraction': extraction,
            'tokenized_extraction': tokenized_extraction,
            'lemma_expansion': ' '.join(extraction_expansion['lemmas']),
            'split_expansion': ' '.join(extraction_expansion['split']),
            'recipe_attributes': query_attributes,
            'recipe_nouns': nouns_in_query,
            'attribute_free_extraction': attribute_free_extraction,
            'simplified_query': extraction_expansion['simplified_query']
        }
    else:
        return {
            'raw_extraction': '',
            'tokenized_extraction': '',
            'lemma_expansion': '',
            'split_expansion': '',
            'recipe_attributes': query_attributes,
            'recipe_nouns': nouns_in_query,
            'attribute_free_extraction': attribute_free_extraction,
            'simplified_query': ''
        }
        
def expand_query(doc_extraction):
    lemmas = []
    split_words = []
    nouns = []
    for token in doc_extraction:
        if token.pos_ in ['NOUN', 'PROPN']:
            nouns.append(token.text)
        elif token.pos_ in ['VERB', 'ADJ', 'NOUN', 'PROPN']:
            lemmas.append(token.lemma_)
            split_word = splitter.split(token.text)
            if isinstance(split_word, list) and (len(split_word) > 1 or split_word[0]!=token.text):
                split_words.extend(split_word)
    return {'lemmas': lemmas, 'split': split_words, 'simplified_query': ' '.join(nouns[-2:])}
        
def rerank(query, candidates):
    scores = []
    tokens = set(query.split())
    recipe_docs = [json.loads(item) for item in candidates]

    for recipe in recipe_docs:
        lexcial_score = 0.0
        if len(tokens) > 0:
            recipe_name_doc = nlp(recipe["recipe"]["displayName"].lower())
            recipe_name_lemma = set(
                [
                    token.lemma_ for token in recipe_name_doc 
                    if token.text not in stopwords and token.lemma_ not in stopwords
                ]
            )
            lexcial_score = len(recipe_name_lemma.intersection(tokens)) / len(tokens)
        

        rating_score = 0.0
        if "rating" in recipe and recipe["rating"]:
            rating_dct = recipe["rating"]
            if "ratingValue" in rating_dct and isinstance(
                rating_dct["ratingValue"], float
            ):
                rating_score += rating_dct["ratingValue"]
            
            if ("ratingCount" in rating_dct and 
                isinstance(rating_dct["ratingCount"], int) and
                rating_dct["ratingCount"] > 0
            ):
                rating_score -= (1 / (rating_dct["ratingCount"] + 1))

        source_score = 0.0
        if 'foodnetwork' in recipe['recipeId'] or 'allrecipes' in recipe['recipeId']:
            source_score -= 1.0
        elif 'sidechef' in recipe['recipeId'] or 'kitchenstories' in recipe['recipeId']:
            source_score += 0.5

        image_score = 0.0
        if "images" in recipe and len(recipe["images"]) > 0:
            if "stepImages" in recipe["recipe"]["instructions"] and len(recipe["recipe"]["instructions"]["stepImages"]) > 0:
                image_score += 0.5
        else:
            image_score -= 1.0

        scores.append(3 * lexcial_score + rating_score / 5 + source_score + image_score)

    return scores

def search_with_common_food(extra_nouns_to_search, attributes = None):
    recipe_ids = {recipe_id for noun in extra_nouns_to_search for recipe_id in common_food_name_to_id[noun]}
    recipes = [common_food_recipes[recipe_id] for recipe_id in recipe_ids]
    if attributes is not None:
        diets = attributes.get("dietaryFilters", [])
        cuisines = attributes.get("cuisines", [])
        meal = attributes.get("mealType", "")
        filtered_recipes = []
        for recipe in recipes:
            parsed_recipe = json.loads(recipe)
            recipe_diets = parsed_recipe.get('recipe').get('diets', [])
            recipe_diets = [x.lower() for x in recipe_diets] if recipe_diets else []
            recipe_cuisines = parsed_recipe.get('recipe').get('cuisines', [])
            recipe_cuisines = [x.lower() for x in recipe_cuisines] if recipe_cuisines else []
            recipe_meals = parsed_recipe.get('recipe').get('meals', [])
            recipe_meals = [x.lower() for x in recipe_meals] if recipe_meals else []
            if (diets and any([x.lower() not in recipe_diets for x in diets])) or (cuisines and any([x.lower() not in recipe_cuisines for x in cuisines])) or (meal and meal.lower() not in recipe_meals):
                continue
            else:
                filtered_recipes.append(recipe)
        recipes = filtered_recipes
    return recipes

def search(expanded_query):
    search_time = local_search_time = 0.0
    recipe_query_result = []
    errors = []
    
    # try:
    #     recipe_query_result += client.search_recipes({
    #         'dishName': expanded_query['raw_extraction']
    #         }).get('documents', [])
    # except:
    #     pass
    
    # # only search when attributes are detected and searching with dishname returns less than 3 results
    # if len(expanded_query['recipe_attributes'])!=0 and len(recipe_query_result)<3:

    request = {
        "dishName": expanded_query['attribute_free_extraction'],
        "dietaryFilters": expanded_query['recipe_attributes'].get('diets', []),
        "cuisines": expanded_query['recipe_attributes'].get('cuisines', []),
        "mealType": expanded_query['recipe_attributes'].get('mealType', [""])[0],
    }
    
    simplified_request = {
        "dishName": expanded_query['simplified_query'],
        "dietaryFilters": [],
        "cuisines": [],
        "mealType": "",
    }
    
    search_start = perf_counter()
    try:
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_results = {}
            future_results[executor.submit(client.search_recipes, request)] = 'original'
            if simplified_request['dishName']!=request['dishName'] or request['dietaryFilters'] or request['cuisines'] or request['mealType']:
                future_results[executor.submit(client.search_recipes, simplified_request)] = 'simplified'
            try:
                for future in concurrent.futures.as_completed(future_results, timeout=1):
                    results[future_results[future]] = future.result().get('documents', [])
            except:
                pass
            if 'original' in results:
                recipe_query_result += results.get('original', [])
            else:
                errors.append('original search timeout')
            if 'simplified' in results:
                recipe_query_result += results.get('simplified', [])
            elif len(future_results)>1:
                errors.append('simplified search timeout')
        # recipe_query_result = client.search_recipes(request).get('documents', []) # + recipe_query_result
    except:
        pass
    search_time = perf_counter() - search_start
    
    local_search_start = perf_counter()
    if len(recipe_query_result) <= 3 and expanded_query.get('recipe_nouns', []):
        extra_nouns_to_search = expanded_query.get('recipe_nouns', [])
        try:
            recipe_query_result += search_with_common_food(extra_nouns_to_search, None)
            request['extra_nouns_searched'] = extra_nouns_to_search
        except:
            pass
    local_search_time = perf_counter() - local_search_start
    request['simplified_query'] = expanded_query['simplified_query']
        

    # list of json strings
    return list(set(recipe_query_result)), request, search_time, local_search_time, errors #{'documents': recipe_query_result}


def search_with_clarification(request, utterance_doc):
    search_time = local_search_time = 0.0
    recipe_query_result = []
    
    errors = []
    
    query_attributes = {}
    attribute_free_extraction = utterance_doc.text
    for match_id, start, end in attribute_matcher(utterance_doc):
        attribute, key = nlp.vocab.strings[match_id].split('_')
        attribute_free_extraction = attribute_free_extraction.replace(utterance_doc[start:end].text, '')
        if attribute not in query_attributes:
            query_attributes[attribute] = [key]
        else:
            query_attributes[attribute].append(key)

    tokens = attribute_free_extraction.split()
    negation_words = ['no', 'not', 'nope', "dont", 'none']
    
    extra_nouns_searched = request.pop('extra_nouns_searched', [])
    simplified_query = request.pop('simplified_query', "")
    simplified_request = {
        "dishName": simplified_query,
        "dietaryFilters": [],
        "cuisines": [],
        "mealType": "",
    }

    if len(query_attributes) > 0 and not any(word in negation_words for word in tokens):
        if "dietaryFilters" in request:
            request["dietaryFilters"] += query_attributes.get('diets', [])
            simplified_request["dietaryFilters"] += query_attributes.get('diets', [])
        elif 'diets' in query_attributes:
            request["dietaryFilters"] = query_attributes.get('diets', [])
            simplified_request["dietaryFilters"] = query_attributes.get('diets', [])

        if "cuisines" in request:
            request["cuisines"] += query_attributes.get('cuisines', [])
            simplified_request["cuisines"] += query_attributes.get('cuisines', [])
        elif 'cuisines' in query_attributes:
            request["cuisines"] = query_attributes.get('cuisines', [])
            simplified_request["cuisines"] = query_attributes.get('cuisines', [])

        if 'mealType' in query_attributes:
            request["mealType"] = query_attributes.get('mealType', [""])[0]
            simplified_request["mealType"] = query_attributes.get('mealType', [""])[0]

        search_start = perf_counter()
        try:
            results = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_results = {}
                future_results[executor.submit(client.search_recipes, request)] = 'original'
                if simplified_request['dishName']!=request['dishName'] or request['dietaryFilters'] or request['cuisines'] or request['mealType']:
                    future_results[executor.submit(client.search_recipes, simplified_request)] = 'simplified'
                try:
                    for future in concurrent.futures.as_completed(future_results, timeout=1):
                        results[future_results[future]] = future.result().get('documents', [])
                except:
                    pass
                if 'original' in results:
                    recipe_query_result += results.get('original', [])
                else:
                    errors.append('original search timeout')
                if 'simplified' in results:
                    recipe_query_result += results.get('simplified', [])
                elif len(future_results)>1:
                    errors.append('simplified search timeout')
            # recipe_query_result = client.search_recipes(request).get('documents', [])
        except:
            pass
        search_time = perf_counter() - search_start
        
        local_search_start = perf_counter()
        if len(recipe_query_result) <= 3 and extra_nouns_searched:
            try:
                recipe_query_result += search_with_common_food(extra_nouns_searched, simplified_request)
            except:
                pass
        local_search_time = perf_counter() - local_search_start
        
        request['extra_nouns_searched'] = extra_nouns_searched
        request['simplified_query'] = simplified_query

        return list(set(recipe_query_result)), request, query_attributes, search_time, local_search_time, errors
    else:
        request['extra_nouns_searched'] = extra_nouns_searched
        request['simplified_query'] = simplified_query
        return recipe_query_result, request, None, search_time, local_search_time, errors


def get_clarification_attrs(results):
    cuisines = []
    diets = []
    for x in results:
        x = x.replace(':null', ':None').replace(':false', ':False').replace(':true', ':True')
        x = eval(x)
        cuisines.append(x['recipe']['cuisines'])
        diets.append(x['recipe']['diets'])
    return cuisines, diets

def diet_or_cuisine(diets, cuisines): # decide which clarification to ask

    diet_dic = {}

    block_constraints = ['pescatarian', 'tree nut free', 'tree nut-free', 'dairy free', 'dairy-free', 'egg free', 'egg-free', 'nut free', 'nut-free']

    for item1 in diets:
        if item1:
            for item2 in item1:
                item2 = item2.lower()
                if item2 not in block_constraints:
                    if item2 not in diet_dic:
                        diet_dic[item2] = 1
                    else:
                        diet_dic[item2] += 1

    diet_sort = sorted(diet_dic.items(), key=lambda x:x[1], reverse=True)

    cuisine_dic = {}
    filter_list = ['other']

    for item1 in cuisines:
        if item1: 
            capital_check = [x[0].isupper() for x in item1] # handle weird cuisine values
            if False in capital_check:
                continue
            for item2 in item1:
                item2 = item2.lower()
                if item2 in filter_list:
                    break
                if item2 not in cuisine_dic:
                    cuisine_dic[item2] = 1
                else:
                    cuisine_dic[item2] += 1

    cuisine_sort = sorted(cuisine_dic.items(), key=lambda x:x[1], reverse=True)

    diet_count = sum([ x[1] for x in diet_sort[0:3] ])
    cuisine_count = sum([ x[1] for x in cuisine_sort[0:3] ])

    if len(diet_sort) < 2 and len(cuisine_sort) < 2:
        attribute = None
        sample_values = None
    else:
        if diet_count >= cuisine_count:
            attribute = 'diets'
            sample_values = [ x[0] for x in diet_sort[0:3] ]
        else:
            attribute = 'cuisines'
            sample_values = [ x[0] for x in cuisine_sort[0:3] ]

    return attribute, sample_values

# task selection
# Dynamic programming implementation of LCS problem
  
# Returns length of LCS for X[0..m-1], Y[0..n-1] 
def lcs(X, Y, m, n):
    L = [[0 for x in range(n+1)] for x in range(m+1)]
  
    # Following steps build L[m+1][n+1] in bottom up fashion. Note
    # that L[i][j] contains length of LCS of X[0..i-1] and Y[0..j-1] 
    for i in range(m+1):
        for j in range(n+1):
            if i == 0 or j == 0:
                L[i][j] = 0
            elif X[i-1] == Y[j-1]:
                L[i][j] = L[i-1][j-1] + 1
            else:
                L[i][j] = max(L[i-1][j], L[i][j-1])
  
    # Following code is used to print LCS
    index = L[m][n]
  
    # Create a character array to store the lcs string
    lcs = [-1] * (index+1)
    lcs[index] = -1
  
    # Start from the right-most-bottom-most corner and
    # one by one store characters in lcs[]
    i = m
    j = n
    while i > 0 and j > 0:
  
        # If current character in X[] and Y are same, then
        # current character is part of LCS
        if X[i-1] == Y[j-1]:
            lcs[index-1] = i-1
            i-=1
            j-=1
            index-=1
  
        # If not same, then find the larger of two and
        # go in the direction of larger value
        elif L[i-1][j] > L[i][j-1]:
            i-=1
        else:
            j-=1
  
    return [idx for idx in lcs if idx!=-1]
  
# # Driver program
# # This code is contributed by BHAVYA JAIN

from strsimpy.longest_common_subsequence import LongestCommonSubsequence
lcs_fast = LongestCommonSubsequence()
from nltk.stem import *
stemmer = PorterStemmer()
def task_selection(input_doc, candidates, debug=False):
    # if 'first' in input_text:
    #     return [0, 1.0]
    # elif 'second' in input_text:
    #     return [1, 1.0]
    # elif 'third' in input_text:
    #     return [2, 1.0]
    # else:
    # try match with candidate titles
    token_input_lemma = [token.lemma_ for token in input_doc if token.text not in stopwords]
    token_input_stem = [stemmer.stem(token) for token in token_input_lemma]
    set_token_input_lemma = set(token_input_lemma)
    set_token_input_stem = set(token_input_stem)
    if len(token_input_lemma)==0:
        return [-1, 0.0]
    if debug:
        print(token_input_lemma)
    # if len(token_input)==1:
    #     if 'one' in token_input:
    #         return [0, 1.0]
    #     elif 'two' in token_input:
    #         return [1, 1.0]
    #     elif 'three' in token_input:
    #         return [2, 1.0]
    input_to_candidate_lcs_lemma = []
    input_to_candidate_set_overlap_lemma = []
    input_to_candidate_lcs_stem = []
    input_to_candidate_set_overlap_stem = []
    parsed_candidates = []
    for i, candidate_task in enumerate(candidates):
        doc_candidate = nlp(candidate_task)
        token_candidate_lemma = [token.lemma_ for token in doc_candidate if token.text not in stopwords]
        token_candidate_stem = [stemmer.stem(token) for token in token_candidate_lemma]
        if debug:
            print(token_candidate_lemma)
        distance = lcs_fast.distance(token_input_lemma, token_candidate_lemma)
        distance = (len(token_input_lemma)+len(token_candidate_lemma)-distance)/2
        input_to_candidate_lcs_lemma.append([distance,i])
        input_to_candidate_set_overlap_lemma.append([len(set(token_candidate_lemma)&set_token_input_lemma), i])
        
        distance = lcs_fast.distance(token_input_stem, token_candidate_stem)
        distance = (len(token_input_stem)+len(token_candidate_stem)-distance)/2
        input_to_candidate_lcs_stem.append([distance,i])
        input_to_candidate_set_overlap_stem.append([len(set(token_candidate_stem)&set_token_input_stem), i])
        
        parsed_candidates.append([doc_candidate, token_candidate_stem])
    input_to_candidate_lcs_lemma.sort(key=lambda x:x[0], reverse=True)
    input_to_candidate_set_overlap_lemma.sort(key=lambda x:x[0], reverse=True)
    input_to_candidate_lcs_stem.sort(key=lambda x:x[0], reverse=True)
    input_to_candidate_set_overlap_stem.sort(key=lambda x:x[0], reverse=True)
    if (len(input_to_candidate_lcs_lemma)==1 or input_to_candidate_lcs_lemma[0][0]!=input_to_candidate_lcs_lemma[1][0]) and input_to_candidate_lcs_lemma[0][0] == len(token_input_lemma):
        return [input_to_candidate_lcs_lemma[0][1], input_to_candidate_lcs_lemma[0][0]/len(token_input_lemma)]
    elif (len(input_to_candidate_lcs_stem)==1 or input_to_candidate_lcs_stem[0][0]!=input_to_candidate_lcs_stem[1][0]) and input_to_candidate_lcs_stem[0][0] == len(token_input_stem):
        return [input_to_candidate_lcs_stem[0][1], input_to_candidate_lcs_stem[0][0]/len(token_input_stem)]
    elif (len(input_to_candidate_set_overlap_lemma)==1 or input_to_candidate_set_overlap_lemma[0][0]!=input_to_candidate_set_overlap_lemma[1][0]) and input_to_candidate_set_overlap_lemma[0][0] == len(set_token_input_lemma):
        return [input_to_candidate_set_overlap_lemma[0][1], input_to_candidate_set_overlap_lemma[0][0]/len(set_token_input_lemma)]
    elif (len(input_to_candidate_set_overlap_stem)==1 or input_to_candidate_set_overlap_stem[0][0]!=input_to_candidate_set_overlap_stem[1][0]) and input_to_candidate_set_overlap_stem[0][0] == len(set_token_input_stem):
        return [input_to_candidate_set_overlap_stem[0][1], input_to_candidate_set_overlap_stem[0][0]/len(set_token_input_stem)]
    else:
        # if len(token_input)<=2:
        #     if 'three' in token_input or 'right' in token_input:
        #         return [2, 1.0]
        #     elif 'two' in token_input or 'middle' in token_input:
        #         return [1, 1.0]
        #     elif 'one' in token_input or 'left' in token_input:
        #         return [0, 1.0]
        #     else:
        #         return [-1, 0.0]
        # else:
        return [-1, 0.0]
