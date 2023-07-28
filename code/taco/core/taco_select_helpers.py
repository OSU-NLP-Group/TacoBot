from taco_intent_by_rule import TacoIntentByRule

def is_start_task(current_state, user_attributes, features):
    recipe_query_result = getattr(user_attributes, 'recipe_query_result', None)
    if recipe_query_result:
        # For recipes, match commands for 'start cooking'.
        text = getattr(current_state, 'text', None)
        return TacoIntentByRule._regex_match(TacoIntentByRule.rStartCooking, text)
    else:
        # For WikiHow, Ack would do.
        return True

def is_launch_resume(current_state, user_attributes, features):
    resume_task = getattr(current_state, 'resume_task', False)
    if resume_task:            
        current_task = getattr(user_attributes, 'current_task_docparse', None)
        if current_task is not None:
            return True
    return False

def is_launch_resume_prep(current_state, user_attributes, features):
    resume_task = getattr(current_state, 'resume_task', False)
    if resume_task: 
        list_item_selected = getattr(user_attributes, 'list_item_selected', -1)         
        #current_task = getattr(user_attributes, 'current_task', None)
        return (list_item_selected >= 0) #and current_task is not None
    return False
