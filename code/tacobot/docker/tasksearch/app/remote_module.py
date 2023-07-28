"""
This module uses spacy along with an ignore list to extract the relevant noun phrases from the current user utterance
and bot response from the previous turn.
"""
import spacy
import re
from opensearchpy import OpenSearch

import concurrent.futures

import splitter
import copy

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

from cobot_common.service_client import get_client
from reranker.model import SearchQueryRanker

from time import perf_counter
 
# Client object
# API
client_cobot = get_client(api_key='zwh6kpQgQC4RHqefVdP3n8cwmpSaWzPT7A1OxgFO', timeout_in_millis=2000) 

host = 'search-wikihow-v3-sqeihzsk6k74s4qhgx7b3v5muq.us-east-1.es.amazonaws.com'
port = 443
auth = ('tacobot', 'Taco123#')
client_our = OpenSearch(
    hosts = [{'host': host, 'port': port}],
    http_compress = True,
    http_auth = auth,
    use_ssl = True,
    verify_certs = True,
    ssl_assert_hostname = False,
    ssl_show_warn = False
)

required_context = ['text']
nlp = spacy.load('en_core_web_sm')
stopwords = nlp.Defaults.stop_words
stopwords |= {'one', 'two', 'three', 'first', 'second', 'third'}
stopwords |= {'suggest', 'suggestions', 'suggestion', 'recommendation', 'recommendations', 'recommend', 'search' ,'like', 'want', \
        'a', 'about', 'let', 'need', 'prefer', 'try', 'an', 'favourites', 'favorites', 'favourite', 'favorite', 'may', 'be', 'maybe', \
        'yourself', 'myself', \
        'tips', 'tip', 'prepare','recipes', 'recipe', 'task', 'tasks', 'diy', 'ingredients', 'ingredient', 'cook', 'cooking', 'make', 'instruction', 'instructions', 'project', 'projects', \
        'something', 'thing', 'things', 'anything', 'else', 'different', 'other', 'another', 'special', 'option', 'choice', 'good', 'great', 'sound', 'look'}
stopwords |= {".",",",":",";","?","'","\"","_","-","(",")","/","!"}

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
    total_time = extraction_time = search_time = rerank_time = selection_time = 0
    
    taskname = {
        'raw_extraction': '',
        'tokenized_extraction': '',
        'lemma_expansion': '',
        'split_expansion': ''
    }
    selection = [-1, 0.0]
    ranked_tasks = []
    error = []
    search_errors = []
    
    extraction_start = perf_counter()
    # checks if any noun phrases are in the ignore list
    # most recent user utterance
    input_text = clean_utterance(msg['text'][0])
    top_k = int(msg.get("top_k", 25))
    if len(input_text) > 0:
        input_doc = nlp(input_text)

        # no need to execute every time
        if not msg.get('task_started', False):
            try:
                taskname = taskname_extraction(input_text, input_doc)
            except:
                error.append('task extraction error')
                
            extraction_time = perf_counter() - extraction_start
            search_start = perf_counter()
    
            if taskname['raw_extraction']:
                try:
                    candidate_tasks, search_errors = search(taskname, top_k=top_k)
                except:
                    error.append('wikihow search error')
                    candidate_tasks = []
                
                search_time = perf_counter() - search_start
                rerank_start = perf_counter()
                
                if len(candidate_tasks) > 0:
                    try:
                        scores = rerank(taskname['raw_extraction'], [task['_source']['articleTitle'] for task in candidate_tasks])
                        for i, task in enumerate(candidate_tasks):
                            task['original_rank'] = i
                            task['reranking_score'] = scores[i]
                        ranked_tasks = sorted(candidate_tasks, key=lambda task:task['reranking_score'], reverse=True)
                    except:
                        error.append('rerank error')
                        ranked_tasks = candidate_tasks

                    if len(ranked_tasks) > 9:
                        ranked_tasks = ranked_tasks[:9]
        
                rerank_time = perf_counter()-rerank_start
            
        if msg.get('selected_task', None) is None and msg.get('proposed_tasks', None) is not None and msg.get('proposed_tasks', None):
            
            selection_start = perf_counter()
            
            try:
                if len(msg['proposed_tasks'])>0:
                    selection = task_selection(input_doc, [re.sub(r'\bhow to\b','',task['title'].lower().strip('?.')) for task in msg['proposed_tasks']])
            except:
                error.append('selection error')
                
            selection_time = perf_counter() - selection_start
            
    total_time = perf_counter() - initial_start
    error += search_errors

    return {'taskname': taskname, 'task_selection': selection, 'ranked_tasks': ranked_tasks, 'module_error': '; '.join(error) if len(error) > 0 else '', 'profiling': [total_time, extraction_time, search_time, rerank_time, selection_time]}

# with open('/deploy/app/data/cleaned_cooking_verbs.json', 'r') as f:
#     cooking_verbs = set(json.load(f))
# with open('/deploy/app/data/cleaned_cooking_nouns.json', 'r') as f:
#     cooking_nouns = {i:set(nouns) for i,nouns in json.load(f).items()}

print("loading extraction model")

checkpoint = "/deploy/app/checkpoint/diy_extractor_checkpoint"
device = 'cuda' if torch.cuda.is_available() else 'cpu'
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
diy_extraction_model = AutoModelForQuestionAnswering.from_pretrained(checkpoint, config=AutoConfig.from_pretrained(checkpoint)).to(device)
diy_extraction_model.eval()
# recipe_extraction_model = AutoModelForQuestionAnswering.from_pretrained("checkpoint/pos_recipe_cpt").to(device)
# recipe_extraction_model.eval()
print("extraction model loaded")

rerank_tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased')
rerank_model = SearchQueryRanker().to(device)
if device == 'cpu':
    rerank_model.load_state_dict(torch.load("/deploy/app/checkpoint/diy_reranker.pt",  map_location=torch.device('cpu')))
else:
    rerank_model.load_state_dict(torch.load("/deploy/app/checkpoint/diy_reranker.pt"))
rerank_model.eval()
print("reranking model loaded")

def taskname_extraction(utterance, utterance_doc):
    model = diy_extraction_model
        
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
    extraction = re.sub(r'recipe[s]?', '', extraction).rstrip()
    extraction = re.sub(r'\[.*?\]', '', extraction)
    doc_extraction = nlp(extraction)
    tokenized_extraction = ' '.join([token.text for token in doc_extraction])
    lemma_extraction = [token.lemma_ for token in doc_extraction if token.text not in stopwords and token.lemma_ not in stopwords]
    
    extraction_expansion = expand_query(doc_extraction)
    
    # if type=='recipe':
    #     extra_lemmas = []
    #     extra_split_words = []
    #     for token in utterance_doc:
    #         if token.pos_=='VERB' and token.lemma_ in cooking_verbs and token.lemma_ not in {'make', 'cook', 'eat'} and token.text not in extraction:
    #             extraction = token.lemma_ + ' ' + extraction
    #             tokenized_extraction = token.lemma_ + ' ' + tokenized_extraction
    #             extra_lemmas.append(token.lemma_)
    #             split_word = splitter.split(token.text)
    #             if len(split_word) > 1 or split_word[0]!=token.text:
    #                 extra_split_words.extend(split_word)
    #     if extra_lemmas:
    #         extraction_expansion['lemmas'].extend(extra_lemmas)
    #     if extra_split_words:
    #         extraction_expansion['split'].extend(extra_split_words)
    
    if len(lemma_extraction)>0:
        return {
            'raw_extraction': extraction,
            'tokenized_extraction': tokenized_extraction,
            'lemma_expansion': ' '.join(extraction_expansion['lemmas']),
            'split_expansion': ' '.join(extraction_expansion['split'])
        }
    else:
        return {
            'raw_extraction': '',
            'tokenized_extraction': '',
            'lemma_expansion': '',
            'split_expansion': ''
        }
        
def expand_query(doc_extraction):
    lemmas = []
    split_words = []
    for token in doc_extraction:
        if token.pos_ == 'VERB' or token.pos_ == 'NOUN':
            lemmas.append(token.lemma_)
            split_word = splitter.split(token.text)
            if isinstance(split_word, list) and (len(split_word) > 1 or split_word[0]!=token.text):
                split_words.extend(split_word)
    return {'lemmas': lemmas, 'split': split_words}
        
def rerank(query, candidates):
    list_query = [query]*len(candidates)
    inputs = rerank_tokenizer(list_query, candidates, padding=True, truncation=True, return_tensors="pt")
        
    with torch.no_grad():
        outputs = rerank_model(
            input_ids = inputs['input_ids'].to(device),
            attention_mask = inputs['attention_mask'].to(device),
            cand_size = len(candidates)
        )

    scores = outputs['prediction'].reshape(-1).cpu().detach().tolist()
    return scores

def search(expanded_query, top_k=25):
    errors = []
    expanded_query = ' '.join([expanded_query['raw_extraction'], expanded_query['tokenized_extraction'],expanded_query['lemma_expansion'],expanded_query['split_expansion']])
    expanded_query = ' '.join(set(expanded_query.split())) # remove duplicate tokens
    
    request = {
        "size": top_k,
        "query": {
            "bool": {
                "should": []
            }
        }
    }


    for token in expanded_query.split():
        request["query"]["bool"]["should"].append({
            "match": {
                "articleTitle": {
                    "query": token,
                    "fuzziness": "AUTO"
                }
            }
        })
    cobot_request = copy.deepcopy(request)
    cobot_request['size'] = 5
    wikihow_query_result = [set(), []]
    try:
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_results = {executor.submit(client_cobot.search_wikihow, cobot_request): 'cobot_api', executor.submit(client_our.search, body=request, index='wikihow-v3'): 'our_dump'}
            try:
                for future in concurrent.futures.as_completed(future_results, timeout=1):
                    results[future_results[future]] = future.result().get("hits", {}).get("hits", {})
            except:
                pass
            if 'cobot_api' not in results:
                errors.append('cobot api timeout')
            if 'our_dump' not in results:
                errors.append('our dump timeout')
            for task in results.get('our_dump', [])[:top_k] + results.get('cobot_api', [])[:5]:
                if task['_source']['articleTitle'] not in wikihow_query_result[0]:
                    wikihow_query_result[0].add(task['_source']['articleTitle'])
                    wikihow_query_result[1].append(task)
            
        # wikihow_query_result = client.search_wikihow(request).get("hits", {}).get("hits", {})
        # wikihow_query_result = client.search(
        #                 body = request,
        #                 index = 'wikihow-v3'
        #             ).get("hits", {}).get("hits", {})
    except:
        pass
    return wikihow_query_result[1], errors


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
    token_input_lemma = [token.lemma_ for token in input_doc if token.text not in stopwords and token.lemma_ not in stopwords]
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
        if distance == 0:
            distance = 999 # if exact match, then select
        else:
            distance = (len(token_input_lemma)+len(token_candidate_lemma)-distance)/2
        input_to_candidate_lcs_lemma.append([distance,i])
        input_to_candidate_set_overlap_lemma.append([len(set(token_candidate_lemma)&set_token_input_lemma), i])
        
        distance = lcs_fast.distance(token_input_stem, token_candidate_stem)
        if distance == 0:
            distance = 999 # if exact match, then select
        else:
            distance = (len(token_input_stem)+len(token_candidate_stem)-distance)/2
        input_to_candidate_lcs_stem.append([distance,i])
        input_to_candidate_set_overlap_stem.append([len(set(token_candidate_stem)&set_token_input_stem), i])
        
        parsed_candidates.append([doc_candidate, token_candidate_stem])
    input_to_candidate_lcs_lemma.sort(key=lambda x:x[0], reverse=True)
    input_to_candidate_set_overlap_lemma.sort(key=lambda x:x[0], reverse=True)
    input_to_candidate_lcs_stem.sort(key=lambda x:x[0], reverse=True)
    input_to_candidate_set_overlap_stem.sort(key=lambda x:x[0], reverse=True)
    # check lemma lcs
    if (len(input_to_candidate_lcs_lemma)==1 or input_to_candidate_lcs_lemma[0][0]!=input_to_candidate_lcs_lemma[1][0]) and (input_to_candidate_lcs_lemma[0][0] == 999 or input_to_candidate_lcs_lemma[0][0] == len(token_input_lemma)):
        return [input_to_candidate_lcs_lemma[0][1], input_to_candidate_lcs_lemma[0][0]/len(token_input_lemma)]
    # check stem lcs
    elif (len(input_to_candidate_lcs_stem)==1 or input_to_candidate_lcs_stem[0][0]!=input_to_candidate_lcs_stem[1][0]) and (input_to_candidate_lcs_stem[0][0] == 999 or input_to_candidate_lcs_stem[0][0] == len(token_input_stem)):
        return [input_to_candidate_lcs_stem[0][1], input_to_candidate_lcs_stem[0][0]/len(token_input_stem)]
    # check lemma set overlap
    elif (len(input_to_candidate_set_overlap_lemma)==1 or input_to_candidate_set_overlap_lemma[0][0]!=input_to_candidate_set_overlap_lemma[1][0]) and input_to_candidate_set_overlap_lemma[0][0] == len(set_token_input_lemma):
        return [input_to_candidate_set_overlap_lemma[0][1], input_to_candidate_set_overlap_lemma[0][0]/len(set_token_input_lemma)]
    # check stem set overlap
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


