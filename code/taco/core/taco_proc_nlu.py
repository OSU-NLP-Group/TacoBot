from collections import OrderedDict

from text_to_num import alpha2digit
from taco_intent_by_rule import TacoIntentByRule

import re
import pdb

from taco_stop_word import np_ignore_list 

# Error cases of ASK built-in intents
ASK_ERRORS = [
    'continue' # ->AMAZON.ResumeIntent
    ]
def parse_intent(text, intent, current_state, allowed_intents, current_taco_state, user_attributes):
    """
    We parse most user intents using our custom intent classification model, while
    some ASK intents are preserved. Some heuristics are used to compensate for 
    errors of intent classification.

    Args:
        intent: Intent produced by ASK.
        current_state: The current_state argument passed to select_response_model.
        allowed_intents: Legal intents based on state transitions.
        current_taco_state: current taco_state

    Returns:
        intent: (str or None) parsed intent.
        guess_intent: (str or None) when neural NLU is not confident enough, used for fallbacks.

    Exactly one of these two return values will be None, the other will be
    a string.
    """

    # Keep some ASK intents
    if intent in ["LaunchRequestIntent", "AMAZON.RepeatIntent", "AMAZON.ResumeIntent", "AMAZON.ScrollDownIntent","AMAZON.ScrollUpIntent","AMAZON.ScrollLeftIntent","AMAZON.ScrollRightIntent", "AMAZON.CancelIntent", "AMAZON.StopIntent", "UserEvent"] and text not in ASK_ERRORS:
        parsed_intent = intent.split('.')[-1]
        return parsed_intent, parsed_intent
    set_timer_pattern = re.compile(r'\bset\b.*\b(alarm|timer)\b.*\bfor\b')
    if re.search(set_timer_pattern, text.lower()):
        intent = 'SetTimerIntent'
    if intent in ["SetTimerIntent"] and ('timer' in text or 'alarm' in text):
        return intent, intent
    
    tokens = text.split()
    
    print('current_state = ', current_state.neuralintent)
    guess_intent = None
    if "neuralintent" in current_state.__dict__ and current_state.neuralintent:
        custom_intent, guess_intent = process_custom_intent(current_state, allowed_intents, current_taco_state) 
        intent = custom_intent
        print("custom intent ======> ", custom_intent)
    # Should still allow rule-based if neural module has an exception e.g. timeout
    # else:
    #     return None, None

    # SelfIntroIntent is only used for Certification (required for changes to ASK interaction model).
    if intent == "SelfIntroIntent":
        intent = "IgnoreIntent"
    
    method_idx, N_methods, N_steps, current_step_num = TacoIntentByRule.parse_step_nums(current_taco_state)
    all_total_steps = getattr(user_attributes, 'all_total_steps', None)
    regex_intent = TacoIntentByRule.parse_regex_intents(text, N_steps, all_total_steps = all_total_steps, current_taco_state = current_taco_state)

    if 'TaskPreparation' in current_taco_state and len(all_total_steps) > 1:
        _text, _intent = _transform_text_prep(text)
        if _intent is not None:
            regex_intent = _intent
            text = _text
            current_state.text = _text
            print('[dm transform]: text => ', _text)
    elif 'Detail' in current_taco_state and regex_intent == 'NaviNextIntent' and 'step' in text:
            # escape from tips by 'next STEP'
            return 'ResumeIntent', guess_intent

    print("regex intent ==========> ", regex_intent)
    if regex_intent in ['ListManageIntent', 'ReadIngredientIntent']:
        list_item_selected = getattr(user_attributes, 'list_item_selected', -1)
        is_wikihow = getattr(user_attributes, 'is_wikihow', True)
        if list_item_selected > -1 and (not is_wikihow) and ('step' not in text):
            return regex_intent, guess_intent
    elif (
        ('TaskPrepConfirmation' in current_taco_state and regex_intent == 'IngredientQuestionIntent') or 
        ('TaskPrepConfirmation' in current_taco_state and regex_intent == 'AcknowledgeIntent') or 
        (('TaskExecution' in current_taco_state or 'TaskPrep' in current_taco_state) and regex_intent != None and  'Navi' in regex_intent) or
        (('TaskChoice' in current_taco_state) and regex_intent == 'RepeatIntent')
        ):
        return regex_intent, guess_intent 
    elif intent is None and regex_intent:
        intent = regex_intent

    strict_matched_intent = TacoIntentByRule.parse_strict_matching(text)
    if strict_matched_intent:
        if strict_matched_intent == 'TaskCompleteIntent' and not('Execution' in current_taco_state):
            print("strict match intent ===> ", strict_matched_intent)
            intent = 'IgnoreIntent'
        else:
            print("strict match intent ===> ", strict_matched_intent)
            intent =  strict_matched_intent
    
    if ('cancel' in tokens and 'timer' not in tokens) or ('start over' in text):
        intent = 'CancelIntent'

    if current_taco_state == "Welcome" or 'Catalog' in current_taco_state or 'TaskComparison' in current_taco_state:
        if (intent not in ["AlexaCommandIntent", "UserEvent"] and 
            ('favorite' in tokens or 'favorites' in tokens)):
            intent = 'RecommendIntent'
    #TODO
    if 'TaskChoice' in current_taco_state:
        new_intent = get_task_choice(current_state, tokens, text, user_attributes)
        if new_intent is not None:
            intent = new_intent
        else:
            new_intent = choice_intent_keywords(text, tokens, current_state)
            if new_intent is not None:
                intent = new_intent
        if intent == 'NegativeAcknowledgeIntent' and 'Catalog' in current_taco_state:
            list_item_rec = getattr(user_attributes, 'list_item_rec', -1)
            if list_item_rec < 0:
                intent = 'MoreChoiceIntent' # Treat Nak as MoreChoice in TaskChoice_TaskCatalog
    #TODO
    elif 'TaskPreparation' in current_taco_state and TacoIntentByRule._regex_match(TacoIntentByRule.rStartCooking, text):
        # This will be further processed by conditional transition
        return "AcknowledgeIntent", "AcknowledgeIntent"
    #TODO
    elif "TaskExecution" in current_taco_state:

        # navi_intent, _ =  TacoIntentByRule.parse_navi_intents(text, total_steps)
        # print('navi:', navi_intent)
        # if intent in ["AMAZON.NextIntent", "AMAZON.PreviousIntent"] or navi_intent:
            # return "NavigationIntent", "NavigationIntent"
        if intent == 'AMAZON.NextIntent':
            return 'NaviNextIntent', 'NaviNextIntent'
        elif intent == 'AMAZON.PreviousIntent':
            return 'NaviPreviousIntent', 'NaviPreviousIntent'
        elif intent == 'TaskRequestIntent':
            # TEMP
            if current_state['punctuation'] and '?' in current_state['punctuation']:
                intent = 'QuestionIntent'
    
    #TODO
    if 'back' in tokens:
        if 'TaskCatalog' in current_taco_state and getattr(user_attributes, 'choice_start_idx', 0) == 0:
            intent = 'GoBackIntent'
        elif 'TaskPrep' in current_taco_state:
            intent = 'GoBackIntent'

    if text == 'help' or ('help' in tokens and intent not in allowed_intents):
        intent = 'HelpIntent'

    return intent, guess_intent




def flush_slot_values(current_state, user_attributes):
    """
    Store slot values that would be used later into user table.
    Use ASK as backup for our custom tasktype and taskname modules
    """
    taskname_recipe = ''
    taskname_wikihow = ''
    tasktype = ''

    print('current_state.recipesearch = ', current_state.recipesearch)

    if ('recipesearch' in current_state.__dict__ and current_state.recipesearch and 'recipename' in current_state.recipesearch and 
        'raw_extraction' in current_state.recipesearch['recipename']):
        taskname_recipe = current_state.recipesearch['recipename']['raw_extraction']


    print('current_state.tasksearch = ', current_state.tasksearch)
    
    if ('tasksearch' in current_state.__dict__ and current_state.tasksearch and 'taskname' in current_state.tasksearch and 
        'raw_extraction' in current_state.tasksearch['taskname']):
        taskname_wikihow = current_state.tasksearch['taskname']['raw_extraction']

    print('current_state.tasktype = ', current_state.tasktype)

    if 'tasktype' in current_state.__dict__ and 'tasktype' in current_state.tasktype:
        tasktype = current_state.tasktype['tasktype']
    
    print('taskname recipe : ', taskname_recipe)
    print('taskname wikihow: ', taskname_wikihow)
    print('task type: ', tasktype)
    
    # taskname and search result independent now, 
    # rules can be less strict to allow data reading and prevent timeout
    if tasktype == 'diy':
        user_attributes.is_wikihow = True
        if taskname_wikihow != '':
            user_attributes.query = taskname_wikihow
        elif taskname_recipe != '':
            user_attributes.query = taskname_recipe
    elif tasktype == 'cooking':
        user_attributes.is_wikihow = False
        #cleaning
        taskname_wikihow = re.sub(
            r"(search)?\s*for", "", 
            taskname_wikihow.lstrip()
        ) 

        if taskname_recipe != '':
            user_attributes.query = taskname_recipe
        elif taskname_wikihow != '':
            user_attributes.query = taskname_wikihow
    else:
        user_attributes.query = ''


def process_custom_intent(current_state, allowed_intents, current_taco_state):
    """
    Process the output of our custom intent module.
    Log the sorted scores and final result to the state table.

    Args:
        current_state: (dict) the current_state argument passed to select_response_model.
        allowed_intents: (list) allowed intents based on the current state of the state machine.

    Returns:
        intent: (str) the output intent of NLU module.
    """

    print('current_state.neuralintent = ', current_state.neuralintent)
    intent_scores = current_state.neuralintent['intent_scores']
    # The score of these three intents are obtained via softmax.
    polarity_scores = {
        'NeutralIntent': intent_scores['NeutralIntent'],
        'AcknowledgeIntent': intent_scores['AcknowledgeIntent'],
        'NegativeAcknowledgeIntent': intent_scores['NegativeAcknowledgeIntent']
    }

    # The score of these intents are obtained via sigmoid, with threshold 0.5.
    sorted_polarity_scores = sorted(polarity_scores, key=polarity_scores.get, reverse=True)
    polarity_result = sorted_polarity_scores[0]
    # print()
    # for i in allowed_intents:
        # print('-->', i)
    # print()
    other_scores = {}
    for k, v in intent_scores.items():
        if not (k in ['NeutralIntent', 'AcknowledgeIntent', 'NegativeAcknowledgeIntent']) and k in allowed_intents:
            if k in ['QuestionIntent', 'TaskRequestIntent']:
                other_scores[k] = max(intent_scores['QuestionIntent'], intent_scores['TaskRequestIntent']) # alleviate problems caused by the ambiguity between these two
            else:
                other_scores[k] = v
    sorted_other_scores = sorted(other_scores, key=other_scores.get, reverse=True)

    if len(sorted_other_scores) > 0:
        if 'Instruction' in current_taco_state and other_scores['DetailRequestIntent'] > 0.95:
            other_result = 'DetailRequestIntent'
        elif 'Execution' in current_taco_state and  other_scores['HelpIntent'] > 0.95:
            other_result = 'HelpIntent'
        else: other_result = sorted_other_scores[0]
    else:
        other_result = None
    
    if other_result and other_scores[other_result] > 0.5:
        intent = other_result
    elif polarity_result != 'NeutralIntent':
        intent = polarity_result
    else:
        intent = None
    
    if len(sorted_other_scores) > 0 and other_scores[sorted_other_scores[0]] > 0.3:
        other_result = sorted_other_scores[0]
    return intent, other_result


def get_task_choice(current_state, tokens, text, user_attributes):
    new_intent = None
    task_selection = -1
    
    if 'tasksearch' in current_state and current_state['tasksearch'] and 'task_selection' in current_state['tasksearch']:
        task_selection = current_state['tasksearch']['task_selection'][0]
    # task selection and recipe selection are the same thing
    # elif task_selection < 0 and 'recipesearch' in current_state and current_state['recipesearch'] and 'recipe_selection' in current_state['recipesearch']:
    #     task_selection = current_state['recipesearch']['recipe_selection'][0]
    
    if task_selection > -1:
        choice_start_idx = getattr(user_attributes, 'choice_start_idx', 0)
        user_attributes.list_item_selected = task_selection + choice_start_idx
        new_intent = 'ChoiceIntent'
    else:
        noun_in_input = current_state.get('nounphrases', {"user_input_noun_phrases": None}).get("user_input_noun_phrases", None)
        noun_in_input = {token.lower() for noun in noun_in_input for token in noun.split()} if noun_in_input else set()
        if any(['first' in tokens, 'second' in tokens, 'third' in tokens, 
                    'two' in tokens, 'three' in tokens,
                    'initial' in tokens, 'last' in tokens, 'left' in tokens, 'right' in tokens, 'middle' in tokens]) or re.search(r'\b(?<!which )(?<!what )one\b', text):
            if len(noun_in_input-np_ignore_list)==0:
                new_intent = 'ChoiceIntent'
            elif re.search(r'\b(first|second|third|initial|last|left|right|middle) (one|recipe|choice)\b', text):
                new_intent = 'ChoiceIntent'

    return new_intent


more_choice_pattern = re.compile(r'\b(more|next|what else|something else|anything else)\b')
less_choice_pattern = re.compile(r'\b(back|previous)\b')
info_pattern = re.compile(r'\bcompare|comparison|difference(s)?|suggest|recommend|recommendation(s)\b')
info_pattern_strict = re.compile(r'\b(((recommend|suggest)( something)?( for me)?$)|compare|comparison|difference(s)?|(which .*to choose))\b')
def choice_intent_keywords(text, tokens, current_state):
    text = text.lower()
    new_intent = None
    # info_keyword = [
    #     'compare',
    #     'comparison'
    # ]
    
    

    if info_pattern.search(text):
        noun_in_input = current_state.get('nounphrases', {"user_input_noun_phrases": None}).get("user_input_noun_phrases", None)
        noun_in_input = {token.lower() for noun in noun_in_input for token in noun.split()} if noun_in_input else set()
        if len(noun_in_input-np_ignore_list)==0:
            new_intent = 'InfoRequestIntent'
        elif info_pattern_strict.search(text):
            new_intent = 'InfoRequestIntent'

    if 'none' in tokens:
        new_intent = 'NegativeAcknowledgeIntent'

    if more_choice_pattern.search(text):
        new_intent = 'MoreChoiceIntent'
        
    if less_choice_pattern.search(text):
        new_intent = 'LessChoiceIntent'

    return new_intent


def expand_wikihow_query(current_state):
    '''
    Construct expanded queries.
    '''
    task_names = current_state['taskname']['taskname']
    expanded_query = ' '.join([task_names['raw_extraction'], task_names['tokenized_extraction'],task_names['lemma_expansion'],task_names['split_expansion']])
    expanded_query = ' '.join(OrderedDict.fromkeys(expanded_query.split())) # remove duplicate tokens
    return expanded_query
