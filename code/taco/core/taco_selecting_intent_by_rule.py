#%%
import re
import inflect
from text_to_num import alpha2digit

STOP_PATTERN = r'stop|quit'
# (\d+ )?(to )?((the )?last )?step
STEP_OR_METHOD_WITH_NUM_PATTERN1 = r'(\d+)?(st|nd|rd|th)? (to )?((the )?(last|final) )?\b(step|method|part)\b'
STEP_OR_METHOD_WITH_NUM_PATTERN2 = r'(step|method|part) (the )?(\d+)?(st|nd|rd|th)? *(to )?((the )?(last|final|part))?'
STEPS_WITH_NUM_PATTERN = r'(\d+) (more )?step[s]?'
NAVI_TO_STEP_OR_METHOD_PATTERN = r"[ \w]*(show|go|move|jump|what (is|was)|what's|check|review|take me|repeat|(continue|proceed) to)[ \w]*(step|method|part)\b[ \w]*"
NAVI_NEXT_PATTERN = r'[ \w]*(next|go on|carry on|continue|keep going|move on|proceed|i\'m done|(what|anything) else)[ \w]*'
NAVI_PREVIOUS_PATTERN = r'[ \w]*((go )?back|previous)[ \w]*'
NAVI_FORWARD_STEP_PATTERN = r'[ \w]*(ahead|skip|forward|(go |move )forward|more step)[ \w]*'
NAVI_BACK_STEP_PATTERN = r'[ \w]*(go back|move back|backward)[ \w]*'
RESUME_PATTERN = r'\bresume\b'
# COMPLETE_PATTERN = r'complete|finish'
ALEXA_COMMAND_PATTERN = r"\b(music|album|song|movie|volume|turn on)\b|^(\w+ )?(can you )?(play|call|put on|talk to|sing|chat|let's chat)" #"turn off" is a stop skill command
TASK_REQUEST_PATTERN = r'[ \w]*recommend[ \w]*(recipe|task)[ \w]*'
START_COOKING_PATTERN = r'\b(start cooking|start(ed)?|skip[ \w]*ingredient[s]?)\b'
REPEAT_PATTERN = r'\b(repeat|(say|read)[ \w]*again)\b'
LIST_MANAGE_PATTERN = r'[ \w]*(add|send|put|and) (the|all|every|those|these)?[ \w]*(ingredient(s)?|them)? (to|into|in) ([ \w]+)? list' # 'and' here as a patch for ASR Errors
READ_INGREDIENTS_STRICT = r'[ \w]*(what|read|say|tell|list|show)[ \w]*(ingredient[s]?|them)[ \w]*'
INGREDIENT_QUESTION_PATTERN = r'(what|how) (many|much)'

# regex based on context
READ_INGREDIENTS_CONTEXT = [
    ['TaskPrepConfirmation', r'read|say|tell|list|show|ingredient[s]?'],
]
START_TASK_CONTEXT = [
    ['TaskPrepConfirmation', r"\b(let's )?(rock and roll|rock|start the party|let's party|get the party on|party start(ed)?)\b"],
    ['TaskPrepConfirmation', r"\b(let's )?(boogie|start the party|let's party|get the party on|party start(ed)?)\b"],
    ['TaskPrepConfirmation', r"\b(roll(ed)? up)\b"],
    ['TaskPrepConfirmation', r"\b(i am|we are|we should|we shall|we can|ready)\b"]
]


INGREDIENT_MATCH_STOP_WORDS = ['what', 'how', 'much', 'many', 'i', 'a', 'an', 'the', 'it', 'them', 'they', 'need', 'require', 'list', 'and', 'or', 'for', 'of']

COMMANDS = {
    "RecommendIntent": [
        "recommend", "recipes", "tasks", 
        "recipe", "task", "food", 
        "diy", "d. i. y.", "D. I. Y.", "cooking",
        "recommend recipes", "recommend tasks", 
        "recommend recipe", "recommend task",
        "recommend d. i. y. task", "recommend d. i. y. tasks",
        "favorite", "favorites", 
        "favorite recipes", "favorite tasks", 
        "favorite recipe", "favorite task", 
        "my recommendation", "my recommendations"
    ],
    "NaviNextIntent": ["next", "more tips"],
    "NaviPreviousIntent": ["previous"],
    "TaskCompleteIntent": ["complete", "finish"],
    "AcknowledgeIntent": ["cool"],
    'GoBackIntent': ["go back"],
    'RepeatIntent': ['what'],
    'MoreChoiceIntent': ['what else', 'something else', 'anything else']
} 

class TacoIntentByRule:
    
    rStopIntent = re.compile(STOP_PATTERN)
    rNavi2StepOrMethodIntent = re.compile(NAVI_TO_STEP_OR_METHOD_PATTERN)
    rNaviPreviousIntent = re.compile(NAVI_PREVIOUS_PATTERN)
    rNaviNextIntent = re.compile(NAVI_NEXT_PATTERN)
    rNaviBackStepIntent = re.compile(NAVI_BACK_STEP_PATTERN)
    rNaviForwardStepIntent = re.compile(NAVI_FORWARD_STEP_PATTERN)
    rStepOrMethodWithNum1 = re.compile(STEP_OR_METHOD_WITH_NUM_PATTERN1)    
    rStepOrMethodWithNum2 = re.compile(STEP_OR_METHOD_WITH_NUM_PATTERN2)
    rStepsWithNum = re.compile(STEPS_WITH_NUM_PATTERN)
    rResume = re.compile(RESUME_PATTERN)
    # rComplete = re.compile(COMPLETE_PATTERN)
    rAlexaCommand = re.compile(ALEXA_COMMAND_PATTERN)
    rTaskRequest = re.compile(TASK_REQUEST_PATTERN)
    rStartCooking = re.compile(START_COOKING_PATTERN)
    rRepeat = re.compile(REPEAT_PATTERN)
    rListManage = re.compile(LIST_MANAGE_PATTERN)
    rReadIngredientsStrict = re.compile(READ_INGREDIENTS_STRICT)
    rIngredientQuestion = re.compile(INGREDIENT_QUESTION_PATTERN)
    
    # regex based on context
    rReadIngredientsContext = [[context, re.compile(pattern)] for context, pattern in READ_INGREDIENTS_CONTEXT]
    rStartTaskContext = [[context, re.compile(pattern)] for context, pattern in START_TASK_CONTEXT]

    
    def _regex_match(regex, text):
        if regex.search(text):
            return True
        return False
    
    def _context_regex_match(context_regex, current_status, text):
        if any([regex.search(text) and context in current_status for context, regex in context_regex]):
            return True
        return False
    
    @staticmethod
    def parse_strict_matching(text):
        """
        Intent classification via strict string matching.

        Args:
            text: (str) Input user utterance.
        Returns:
            intent: (str) The parsed intent.
        """
        for intent in COMMANDS:
            for s in COMMANDS[intent]:
                if text == s:
                    return intent
        return None
    
    @staticmethod
    def parse_regex_intents(text, total_steps, all_total_steps, current_status):
        """
        Intent parsing using regex, as supplement to neural model.

        Args: 
            text: (str) Input user utterance.
            total_steps: (int) #steps of the current method/part
            all_total_steps: (List(int)) #steps of all steps/parts
        
        Returns:
            intent: (str) The parsed intent. 
        """
        if all_total_steps:
            navi_intent, step_num, method_num = TacoIntentByRule.parse_navi_intents(text, total_steps, all_total_steps)
        else:
            navi_intent = None
        
        if TacoIntentByRule._regex_match(TacoIntentByRule.rResume, text):
            return "ResumeIntent"
        # elif TacoIntentByRule._regex_match(TacoIntentByRule.rComplete, text):
            # return "CompleteIntent"
        elif TacoIntentByRule._regex_match(TacoIntentByRule.rAlexaCommand, text):
            return "AlexaCommandIntent"
        elif TacoIntentByRule._regex_match(TacoIntentByRule.rTaskRequest, text):
            return "TaskRequestIntent"
        elif TacoIntentByRule._regex_match(TacoIntentByRule.rRepeat, text) and not navi_intent:
            return "RepeatIntent"
        elif TacoIntentByRule._regex_match(TacoIntentByRule.rListManage, text):
            return "ListManageIntent"
        elif TacoIntentByRule._regex_match(TacoIntentByRule.rReadIngredientsStrict, text) or TacoIntentByRule._context_regex_match(TacoIntentByRule.rReadIngredientsContext, current_status, text):
            return "ReadIngredientIntent"
        elif TacoIntentByRule._regex_match(TacoIntentByRule.rIngredientQuestion, text):
            return "QuestionIntent"
        elif navi_intent:
            if navi_intent != "Navi2StepIntent" or (step_num >= 0 or method_num >= 0):
                return navi_intent
        elif TacoIntentByRule._context_regex_match(TacoIntentByRule.rStartTaskContext, current_status, text):
            return "AcknowledgeIntent"
        return None
    
    @staticmethod
    def parse_navi_intents(text, current_total_steps, all_total_steps):
        """
        Fine-grained parsing for NavigationIntent.

        Args: 
            text: (str) Input user utterance, which is classified as NavigationIntent
        
        Returns:
            intent: (str) Fine-grained navigation intent. One of ["NaviPreviousIntent", "NaviNextIntent", "Navi2StepIntent", "NaviForwardStepsIntent","NaviBackStepsIntent"]
            
            step_num: (int) Either step index or number of steps. -1 if not applicable.

            method_num: (int) Method index. -1 if not applicable.
            
        """
        step_num, method_num = TacoIntentByRule._parse_step_and_method_num(text, current_total_steps, all_total_steps)
        steps_num =TacoIntentByRule._parse_steps_num(text)

        if TacoIntentByRule._regex_match(TacoIntentByRule.rNaviForwardStepIntent, text) and steps_num != -1:
            if 'skip' in text:
                steps_num += 1
            return "NaviForwardStepsIntent", steps_num, -1
        elif TacoIntentByRule._regex_match(TacoIntentByRule.rNaviBackStepIntent, text) and steps_num != -1:
            return "NaviBackStepsIntent", steps_num, -1
        elif TacoIntentByRule._regex_match(TacoIntentByRule.rNaviPreviousIntent, text):
            if any(['method' in text, 'part' in text]):
                return 'NaviPreviousMethodIntent', -1, -1
            return "NaviPreviousIntent", -1, -1
        elif TacoIntentByRule._regex_match(TacoIntentByRule.rNaviNextIntent, text):
            if any(['method' in text, 'part' in text]):
                return 'NaviNextMethodIntent', -1, -1
            return "NaviNextIntent", -1, -1
        elif TacoIntentByRule._regex_match(TacoIntentByRule.rNavi2StepOrMethodIntent, text) or step_num > 0 or method_num > 0:
            # the second condition maches simple commands like "step 12", "the second step".
            return "Navi2StepIntent", step_num, method_num
        else:
            return None, step_num, -1 # if utterance is not covered by regex but contains a number, we treat it as step index
    
    @staticmethod
    def parse_list_intents(text, ingredients):
        """
        Fine-grained parsing for ListManageIntent

        Args:
            text: (str)  Input user utterance, which is classified as ListManageIntent
        
        Returns:
            is_all: (Boolean) Whether the utterance requests adding ALL items to a list.
            list_name: (str) The name of the desired list.

        """
        match = TacoIntentByRule.rListManage.search(text)
        # if match:
            # print("==== Match Group ====")
            # print(match.group(1))
            # print(match.group(2))
            # print(match.group(3))
            # print(match.group(4))
            # print(match.group(5))
            # print(match.group(6))
        #     print("==== Match Group ====")
        is_all = False
        list_name = None
        matched_ingredients = []
        if match.group(2) or match.group(3):
            is_all = True
        # else:
        matched_ingredients, _ = TacoIntentByRule.match_ingredients(text, ingredients, is_all)
        if match.group(6):
            # print(match.group(5).split(' ')[-1])
            list_name = match.group(6).split(' ')[-1]
            if list_name in[None, 'shopping', 'an', 'a', 'the']:
                list_name = 'Alexa shopping list'
        return is_all, matched_ingredients, list_name

    @staticmethod
    def _parse_steps_num(text):
        # Parse nominal step numbers
        # alpha2digit doesn't work for 'one'...
        text = re.sub(r'\ba\b', '1', text)
        text = re.sub(r'\bone\b', '1', text) 

        text = alpha2digit(text, 'en')
        match = TacoIntentByRule.rStepsWithNum.search(text)
        if match:
            if match.group(1):
                return int(match.group(1))
        return -1
    
    @staticmethod
    def _parse_step_and_method_num(text, current_total_steps, all_total_steps):
        '''
        Arguments:
            text: (str) Navigation command given by the user
            current_total_steps: (int) #steps of the current method
            all_total_steps: (List(int)) #steps for all methods
        
        Returns:
            step_num (int): 1-indexed step number, -1 if not mentioned
            method_num (int): 1-indexed method number, -1 if not mentioned
        '''
        # Parse ordinal step numbers
        # alpha2digit doesn't work for 1st, 2nd, and 3rd...
        text = re.sub(r'\bfirst\b', '1', text)
        text = re.sub(r'\bsecond\b', '2', text)
        text = re.sub(r'\bthird\b', '3', text)
        text = re.sub(r'\bone\b', '1', text) # alpha2digit doesn't work for 'one'...
        text = re.sub(r'\binitial\b', '1', text) # support 'initial step'
        text = alpha2digit(text, 'en')
        match1 = TacoIntentByRule.rStepOrMethodWithNum1.findall(text)
        match2 = TacoIntentByRule.rStepOrMethodWithNum2.findall(text)
        N_methods = len(all_total_steps)

        step_num = None
        method_num = -1

        if match1:
            for match in match1:
                if match[0] != '' or match[3] != '': 
                    if match[0] != '': # match "XX step" or "XX last step", e.g. go to the third step & third to last step
                        if match[3] != '':
                            if match[6] == 'step':
                                step_num = - int(match[0]) + 1
                            else:
                                method_num = N_methods - int(match[0]) + 1
                        else:
                            if match[6] == 'step':
                                step_num = int(match[0])
                            else:
                                method_num = int(match[0])
                    else:
                        if match[6] == 'step':
                            step_num = 0
                        else:
                            method_num = N_methods

        if match2: 
            for match in match2:
                if match[2] != '' or match[5] != '':
                    if match[2] != '': #match "XX step/method/part" or "XX last step/method/part", e.g. go to the third step/method/part
                        if match[5] != '':
                            if match[0] == 'step':
                                step_num = - int(match[2]) + 1
                            else:
                                method_num = N_methods - int(match[2]) + 1
                        else:
                            if match[0] == 'step':
                                step_num = int(match[2])
                            else:
                                method_num = int(match[2])
                    elif match[5] != '':
                        if match[0] == 'step':
                            step_num = 0
                        else:
                            method_num = N_methods
        
        if step_num != None:
            if step_num <= 0:
                if method_num > 0:
                    if method_num <= len(all_total_steps):
                        step_num += all_total_steps[method_num - 1]
                    else:
                        step_num = -1
                else:
                    step_num += current_total_steps
        else:
            step_num = -1
        
        return step_num, method_num                                

    def match_ingredients(text, ingredients, is_all, fallback_all=False):
        ingredient_list = TacoIntentByRule._get_ingredient_list(ingredients)
        ingredient_list.sort(key=lambda x:len(x[1]), reverse=True)
        matched_list = []
        matched_list_root = []
        all_list = []
        for ingredient in ingredient_list:
            all_list.append(ingredient[0])
            if ingredient[1] in text:
                text = text.replace(ingredient[1], '')
                matched_list.append(ingredient[0])
                matched_list_root.append(ingredient[1])
                ingredient_list.remove(ingredient)
        if is_all:
            return all_list
        for token in text.split():
            if token not in INGREDIENT_MATCH_STOP_WORDS:
                for ingredient in ingredient_list:
                    for word in ingredient[1].split():
                        if token in word and ingredient[0] not in matched_list:
                            matched_list.append(ingredient[0])
                            matched_list_root.append(ingredient[1])
                            break
        if fallback_all and matched_list == []:
            return all_list, matched_list_root

        return matched_list, matched_list_root
        

    def _get_ingredient_list(ingredients):
        eng = inflect.engine()
        ing_list = []
        for ingredient in ingredients:
            # We only care about the first part
            text = ingredient['displayText'].split(',')[0].lower() 
            # remove ()s, mostly (x sticks).
            text = re.sub(r' \([\w ]*\)', '', text) 
            # Get rid of unicode chars, e.g. 1/2, 3/4 ...
            text = text.encode("ascii", "ignore")
            text = text.decode()

            if text[0].isdigit():
                text = ' '.join(text.split(' ')[1:])
            unit = ingredient['unit'].lower()

            if ingredient['quantity']>1:
                unit = eng.plural_noun(unit)
            if unit:
                text = text.replace(unit, '')

            if ingredient['unit']:
                text.replace(ingredient['unit'],'')
            # units from https://en.wikipedia.org/wiki/Cooking_weights_and_measures
            text = re.sub(r'\b(ounce|lb|of|fl|oz|tbsp|tsp|wgf|tcf|pt|qt|gal)\b', '', text).strip() # filter 'of' and other units 
            text = re.sub(r'\bas needed\b', '', text)
            text = re.sub(r'\s\s+', ' ', text)
            ing_list.append((ingredient['displayText'].lower().split(',')[0], text))


        return ing_list
    
    def parse_step_nums(current_state: str):
        '''
        Parse numbers from state names in Execution
        
        Arguments:
            current_state: name of the current taco_state
        Returns:
            Current method number: int 0-indexed
            Total number of method: int
            Total number of steps: int
            Current step number: int 0-indexed
        '''
        
        pattern = r'MethodNo([0-9]+)of([0-9]+)w([0-9]+)steps_StepAt([0-9]+)'
        match = re.search(pattern, current_state)
        if match:
            return int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
        return -1, -1, -1, -1

