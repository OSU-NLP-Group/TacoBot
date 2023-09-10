def set_query_user_attributes(query_result, user_attributes, is_new_search=False):
    setattr(user_attributes, 'query_result', query_result)
    setattr(user_attributes, 'current_task', None)
    setattr(user_attributes, 'current_step', None)
    setattr(user_attributes, 'current_step_details', [])
    setattr(user_attributes, 'current_part', None)
    setattr(user_attributes, 'current_task_docparse', None)
    setattr(user_attributes, 'list_item_selected', -1)
    setattr(user_attributes, 'started_cooking', None)
    if is_new_search:
        setattr(user_attributes, 'choice_start_idx', 0)
        setattr(user_attributes, 'proposed_tasks', [])
        setattr(user_attributes, 'list_item_rec', -1)


def check_exception(intent, num_results, user_attributes):
    choice_start_idx = getattr(user_attributes, 'choice_start_idx', 0)
    choice_start_idx = 0 if choice_start_idx is None else choice_start_idx

    speak_out = ''
    if intent == 'MoreChoiceIntent' and choice_start_idx + 3 >= num_results:
        speak_out = 'There are no more results. If you are not sure how to move on, say help. '
    elif intent == 'LessChoiceIntent' and choice_start_idx - 3 < 0:
        speak_out = 'The results I just read are already the first ones. If you are not sure what to try, say help. '

    return speak_out


def update_choice_idx(intent, user_attributes):
    choice_start_idx = getattr(user_attributes, 'choice_start_idx', 0)
    choice_start_idx = 0 if choice_start_idx is None else choice_start_idx
    if intent == 'MoreChoiceIntent':
        choice_start_idx += 3
    elif intent == 'LessChoiceIntent':
        choice_start_idx -= 3 
    choice_start_idx = 0 if choice_start_idx < 0 else choice_start_idx
    setattr(user_attributes, 'choice_start_idx', choice_start_idx)
    return choice_start_idx


def select_followup_template(num_results, choice_start_idx, first_visit):
    follow_up = ''
    
    if num_results == 1:
        follow_up = ""
    elif num_results == 2:
        follow_up = "Do you want the first one or the second one? "
    elif num_results == 3:
        follow_up = "Do you want the first, second, or third option? "
    elif choice_start_idx == 0:
        follow_up = "Do you want the first, second, or third option? "
        if first_visit:
            follow_up = "You can ask me to compare them or tell you more options. " + follow_up
    else:
        if num_results - choice_start_idx == 1:
            follow_up = ""
        elif num_results - choice_start_idx == 2:
            follow_up = "Do you want the first one or the second one? "
        else:
            follow_up = "Do you want the first, second, or third option? "   
        follow_up += 'Or you can say, go back, to review the previous options. ' 

    return follow_up


def get_current_choices(items, choice_start_idx):
    return items[choice_start_idx : choice_start_idx + 3]

def get_and_list_prompt(items:list):
    '''
    Convert a list of strs to a English str.
    !!! The returned string does not have punctuation or trailing white spaces. 
    '''
    if len(items) == 0:
        return ''
    if len(items) == 1:
        return items[0]
    else:
        return ', '.join(items[:-1]) + ' and ' + items[-1]

def get_constraints(current_state):
    recipesearch = getattr(current_state, 'recipesearch', None)
    satisfied_constraints = None
    if recipesearch and 'satisfied_constraints' in recipesearch:
        satisfied_constraints = recipesearch['satisfied_constraints']
        if satisfied_constraints:
            if 'diets' in satisfied_constraints:
                satisfied_constraints = satisfied_constraints['diets']
            elif 'cuisines' in satisfied_constraints:
                satisfied_constraints = satisfied_constraints['cuisines']
            print('[recipe choice] satisfied constraints: ', satisfied_constraints)
    return satisfied_constraints