# new added

import re
import json
import logging
from text_to_num import alpha2digit
# from taco_logger import LoggerFactory
from taco_intent_by_rule import TacoIntentByRule

REFLEXIVE_TRIGGERS = ['AlexaCommandIntent', 'StopIntent', 'RepeatIntent', 'IngoreIntent', 'ReadIngredientIntent', 'HelpIntent']

ASK_ERRORS = ['continue']  # ->AMAZON.ResumeIntent 

logger = logging.getLogger('tacologger')

more_choice_pattern = re.compile(r'\b(more|next|what else|something else|anything else)\b')
less_choice_pattern = re.compile(r'\b(back|previous)\b')
info_pattern = re.compile(r'\bcompare|comparison|difference(s)?|suggest|recommend|recommendation(s)\b')
info_pattern_strict = re.compile(r'\b(((recommend|suggest)( something)?( for me)?$)|compare|comparison|difference(s)?|(which .*to choose))\b')

# NOTE mrc and faq links to remote_qa_internt and it will select by using question type

TACO2RP = {
    'LAUNCH_RESPONDER':       ['WELCOME', 'welcome_Treelet'],
    'ERROR_RESPONDER':        ['exception_INTERNT', 'Taco_excet_error_Treelet'],
    'BAD_TASK_RESPONDER':     ['exception_INTERNT', 'Taco_excet_bad_Treelet'],
    'HELP_RESPONDER':         ['exception_INTERNT', 'Taco_excet_help_Treelet'],
    'CHOICE_RESPONDER':       ['choice_INTERNT', 'Taco_choice_Treelet'],
    'PREPARATION_RESPONDER':  ['preparation_INTERNT', 'Taco_Prepration_Treelet'],
    'EXECUTION_RESPONDER':    ['execution_INTERNT', 'Taco_execution_Treelet'],
    'IDK_RESPONDER':          ['QA_INTERNT', 'IDK_qa_treelet'],
    'INGREDIENT_QA_RESPONDER':['INGREDIENT', 'ingredient_type_treelet'],
    'SUB_QA_RESPONDER':       ['INGREDIENT', 'ingredient_Substitute_treelet'],
    'mrc':                    ['Remote_QA_INTERNT', 'MRC_qa_treelet'],
    'faq':                    ['Remote_QA_INTERNT', 'FAQ_qa_treelet'],
    'ooc':                    ['Remote_QA_INTERNT', 'OOC_qa_treelet'],
    'EVI_RESPONDER':          ['Remote_QA_INTERNT', ''],
    'REPEAT_RESPONDER':       ['utils_intent', 'TacoRepeat_Treelet'],
    'HALT_RESPONDER':         ['halt_INTERNT', 'Taco_halt_Treelet'],
    'NEURAL_CHAT':            ['NEURAL_CHAT', ''],
    'NEURAL_FALLBACK':        ['NEURAL_FALLBACK', ''],
    "FALLBACK":               ['FALLBACK', ''],
    "CATEGORIES":             ['CATEGORIES', ''],
    "FOOD":                   ['FOOD', ''],
    "WIKI":                   ['WIKI', ''],
    "ALIENS":                 ['ALIENS', ''],
    "ACKNOWLEDGMENT":         ['ACKNOWLEDGMENT', ''],
    "TRANSITION":             ['TRANSITION', '']
}

RP2TACO = {}
for taco_rp in TACO2RP:
    rp_name, rp_treelet = TACO2RP[taco_rp]
    if rp_name not in RP2TACO:
        RP2TACO[rp_name] = {}
    RP2TACO[rp_name][rp_treelet] = taco_rp



def flush_slot_values(current_state, user_attributes):
    """
    Store slot values that would be used later into user table.
    Use ASK as backup for our custom tasktype and taskname modules
    """
    taskname_recipe = ''
    taskname_wikihow = ''
    tasktype = ''

    # logger.taco_merge(f'current_state.recipesearch = {current_state.recipesearch}')

    if ('recipesearch' in current_state.__dict__ and current_state.recipesearch and 'recipename' in current_state.recipesearch and 
        'raw_extraction' in current_state.recipesearch['recipename']):
        taskname_recipe = current_state.recipesearch['recipename']['raw_extraction']


    # logger.taco_merge(f'current_state.recipesearch = {current_state.tasksearch}')

    
    if ('tasksearch' in current_state.__dict__ and current_state.tasksearch and 'taskname' in current_state.tasksearch and 
        'raw_extraction' in current_state.tasksearch['taskname']):
        taskname_wikihow = current_state.tasksearch['taskname']['raw_extraction']

    # logger.taco_merge(f'current_state.recipesearch = {current_state.tasktype}')
    # input()


    if 'tasktype' in current_state.__dict__ and 'tasktype' in current_state.tasktype:
        tasktype = current_state.tasktype['tasktype']
    
    # print('taskname recipe : ', taskname_recipe)
    # print('taskname wikihow: ', taskname_wikihow)
    # print('task type: ', tasktype)
    
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


def get_task_choice(features, text, user_attributes):
    new_intent = None
    task_selection = -1
    tokens = text.split()
    if 'tasksearch' in features.__dict__ and features.tasksearch and 'task_selection' in features.tasksearch:
        task_selection = features.tasksearch['task_selection'][0]

    if task_selection > -1:
        choice_start_idx = getattr(user_attributes, 'choice_start_idx', 0)
        user_attributes.list_item_selected = task_selection + choice_start_idx
        new_intent = 'ChoiceIntent'
    else:
        if 'nounphrases' in features.__dict__:
            noun_in_input = getattr(features.nounphrases, 'user_input_noun_phrases', None)
            noun_in_input = {token.lower() for noun in noun_in_input for token in noun.split()} if noun_in_input else set()

            if any(['first' in tokens, 'second' in tokens, 'third' in tokens, 
                        'two' in tokens, 'three' in tokens,
                        'initial' in tokens, 'last' in tokens, 'left' in tokens, 'right' in tokens, 'middle' in tokens]) or re.search(r'\b(?<!which )(?<!what )one\b', text):
                if len(noun_in_input-np_ignore_list)==0:
                    new_intent = 'ChoiceIntent'
                elif re.search(r'\b(first|second|third|initial|last|left|right|middle) (one|recipe|choice)\b', text):
                    new_intent = 'ChoiceIntent'

    return new_intent

def choice_intent_keywords(text, tokens, current_state):
    text = text.lower()
    new_intent = None

    if info_pattern.search(text):
        noun_in_input = getattr(current_state.nounphrases, 'user_input_noun_phrases', None)
        # current_state.get('nounphrases', {"user_input_noun_phrases": None}).get("user_input_noun_phrases", None)
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


def transform_text_prep(text):
    '''
    Transform text to handle method/part selection by voice.
    e.g. 'the first one' to '1 method', which is further handled by advanced_navi
    '''
    _text = re.sub(r'\bfirst\b', '1', text)
    _text = re.sub(r'\bsecond\b', '2', _text)
    _text = re.sub(r'\bthird\b', '3', _text)
    _text = re.sub(r'\bone\b', '1', _text) # alpha2digit doesn't work for 'one'...
    _text = re.sub(r'\binitial\b', '1', _text) # support 'initial step'
    _text = alpha2digit(_text, 'en')
    m = re.search(r'\b\d+\b', _text)
    if m:
        _text = f'{m.group(0)} method'
        return _text, 'Navi2StepIntent'
    else:
        return text, None

def Is_start_task(current_state, user_attributes):
    recipe_query_result = getattr(user_attributes, 'recipe_query_result', None)
    if recipe_query_result:
        # For recipes, match commands for 'start cooking'.
        text = getattr(current_state, 'text', None)
        return TacoIntentByRule._regex_match(TacoIntentByRule.rStartCooking, text)
    else:
        # For WikiHow, Ack would do.
        return True

def Is_launch_resume(current_state, user_attributes):
    resume_task = getattr(current_state, 'resume_task', False)
    current_task = getattr(user_attributes, 'current_task_docparse', None)
    if resume_task and current_task: return True
    return False

def Is_launch_resume_prep(current_state, user_attributes):
    resume_task = getattr(current_state, 'resume_task', False)
    if resume_task: 
        list_item_selected = getattr(user_attributes, 'list_item_selected', -1)         
        return (list_item_selected >= 0) #and current_task is not None
    return False


def handle_method_selection(current_state, user_attributes):
    arguments = current_state.user_event.get('arguments', [])
    if arguments and arguments[0] in ['MethodSelected', 'PartSelected']:
        all_total_steps = getattr(user_attributes, 'all_total_steps')
        item_selected = arguments[1] if len(arguments) > 1 else -1
        if item_selected > 0:
            to_state_touch = f'TaskExecution_MethodNo{item_selected-1}of{len(all_total_steps)}w{all_total_steps[item_selected-1]}steps_StepAt0_Instruction'
            return to_state_touch
    return None


def Only_one_query_result(current_state, user_attributes):
    list_item_rec = getattr(user_attributes, 'list_item_rec', -1)
    print('[sm li_rec]: ', list_item_rec)
    return list_item_rec >= 0

def has_clarification_question(current_state, user_attributes):
    # return False # disable for now
    if 'tasktype' in current_state.__dict__ and 'tasktype' in current_state.tasktype:
        tasktype = current_state.tasktype['tasktype']
        if tasktype == 'cooking' and 'attributes_to_clarify' in current_state.recipesearch \
            and current_state.recipesearch['attributes_to_clarify'] is not None:
            return True
    return False

def Is_confirmed_complete(current_state, user_attributes):
    complete_confirmation = getattr(user_attributes, 'confirmed_complete', False)
    if complete_confirmation:
        return True
    else:
        method_idx, N_methods, total_steps, current_step_num = TacoIntentByRule.parse_step_nums(current_state.status)
        has_parts = getattr(user_attributes, 'has_parts', False)
        return current_step_num == total_steps-1 and (not has_parts or (has_parts and method_idx == N_methods-1 ))


def get_article(current_state, user_attributes):
    current_task_docparse = getattr(user_attributes, 'current_task_docparse', None)

    if current_task_docparse:
        return current_task_docparse
    elif current_state.docparse:
        if 'docparse' in current_state.docparse and not current_state.docparse['is_batch']:
            current_task_docparse = current_state.docparse['docparse']
            # print('query_result = ', user_attributes.query_result)
            # input()

            setattr(user_attributes, 'current_task_docparse', current_task_docparse)
            return current_task_docparse
    else:
        return None


np_ignore_list = {
    "'s",
    "i",
    "me",
    "my",
    "myself",
    "we",
    "our",
    "ours",
    "ourselves",
    "you",
    "you're",
    "you've",
    "you'll",
    "you'd",
    "your",
    "yours",
    "yourself",
    "yourselves",
    "he",
    "him",
    "his",
    "himself",
    "she",
    "she's",
    "her",
    "hers",
    "herself",
    "it",
    "it's",
    "its",
    "itself",
    "they",
    "them",
    "their",
    "theirs",
    "themselves",
    "what",
    "which",
    "who",
    "whom",
    "this",
    "that",
    "that'll",
    "these",
    "those",
    "am",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "having",
    "do",
    "does",
    "did",
    "doing",
    "a",
    "an",
    "the",
    "and",
    "but",
    "if",
    "or",
    "because",
    "as",
    "until",
    "while",
    "of",
    "at",
    "by",
    "for",
    "with",
    "about",
    "against",
    "between",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "to",
    "from",
    "up",
    "down",
    "in",
    "out",
    "on",
    "off",
    "over",
    "under",
    "again",
    "further",
    "then",
    "once",
    "here",
    "there",
    "when",
    "where",
    "why",
    "how",
    "all",
    "any",
    "both",
    "each",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "no",
    "nor",
    "not",
    "only",
    "own",
    "same",
    "so",
    "than",
    "too",
    "very",
    "s",
    "t",
    "can",
    "will",
    "just",
    "don",
    "don't",
    "should",
    "should've",
    "now",
    "d",
    "ll",
    "m",
    "o",
    "re",
    "ve",
    "y",
    "ain",
    "aren",
    "aren't",
    "couldn",
    "couldn't",
    "didn",
    "didn't",
    "doesn",
    "doesn't",
    "hadn",
    "hadn't",
    "hasn",
    "hasn't",
    "haven",
    "haven't",
    "isn",
    "isn't",
    "ma",
    "mightn",
    "mightn't",
    "mustn",
    "mustn't",
    "needn",
    "needn't",
    "shan",
    "shan't",
    "shouldn",
    "shouldn't",
    "wasn",
    "wasn't",
    "weren",
    "weren't",
    "won",
    "won't",
    "wouldn",
    "wouldn't",
    "my name",
    "your name",
    "wow",
    "yeah",
    "yes",
    "ya",
    "cool",
    "okay",
    "more",
    "some more",
    " a lot",
    "a bit",
    "another one",
    "something else",
    "something",
    "anything",
    "someone",
    "anyone",
    "play",
    "mean",
    "a lot",
    "a little",
    "a little bit",
    "option",
    "options",
    'choice',
    'choices',
    'recipe',
    'recipes',
    'task',
    'tasks',
    'one',
    'two',
    'three',
    'first',
    'second',
    'third',
    'initial',
    'left',
    'right',
    'last',
    'middle',
    'difference',
    'differences',
    'recommendations',
    'recommendation',
    "take",
    "choose"
}