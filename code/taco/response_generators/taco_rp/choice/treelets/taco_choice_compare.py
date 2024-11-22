from taco.response_generators.taco_rp import recipe_helpers


def taco_wikihow_compare(current_state, last_state, user_attributes):
    wikihow_query_result = getattr(user_attributes, 'query_result', None)
    choice_start_idx = getattr(user_attributes, 'choice_start_idx', 0)
    num_results = len(wikihow_query_result)

    current_choices, views, ratings = get_wikihow_info(wikihow_query_result, choice_start_idx, num_results)
    idx_max_views = views.index(max(views))
    max_view_task = current_choices[idx_max_views]["_source"]["articleTitle"]
    idx_max_ratings = ratings.index(max(ratings))
    max_rating_task = current_choices[idx_max_ratings]["_source"]["articleTitle"]

    out = ''
    if max(views) > 0 and max(ratings) > 0:
        if idx_max_views == idx_max_ratings:
            out = (
                f"I recommend the <say-as interpret-as=\"ordinal\"> {idx_max_views + 1} </say-as> task, {max_view_task}! " +
                "It has the highest rating and is the most popular. Do you want to choose it? "
            )
            setattr(user_attributes, 'list_item_rec', idx_max_views)
        else:
            out = (
                f"The <say-as interpret-as=\"ordinal\"> {idx_max_ratings + 1} </say-as> task, {max_rating_task}, has the highest rating. " + 
                f"The <say-as interpret-as=\"ordinal\"> {idx_max_views + 1} </say-as> task, {max_view_task}, is the most popular. " +
                f"Do you want the <say-as interpret-as=\"ordinal\"> {idx_max_ratings + 1} </say-as> or the <say-as interpret-as=\"ordinal\"> {idx_max_views + 1} </say-as> task? " 
            )
    elif max(views) > 0:
        out = f"I recommend the <say-as interpret-as=\"ordinal\"> {idx_max_views + 1} </say-as> task, {max_view_task}! It is the most popular. "
        out += 'Do you want to choose it? '
        setattr(user_attributes, 'list_item_rec', idx_max_views)
    elif max(ratings) > 0:
        out = f"I recommend the <say-as interpret-as=\"ordinal\"> {idx_max_ratings + 1} </say-as> task, {max_rating_task}! It has the highest rating. "
        out += 'Do you want to choose it? '
        setattr(user_attributes, 'list_item_rec', idx_max_ratings)
    else:
        first_task = current_choices[0]["_source"]["articleTitle"]
        out = f"I recommend the first task, {first_task}. It is the most relevant task I found. Do you want to choose it? "
        setattr(user_attributes, 'list_item_rec', 0)
    
    return {'response': out, 'shouldEndSession': False}


def get_wikihow_info(wikihow_query_result, choice_start_idx, num_results):
    if choice_start_idx + 3 <= num_results:
        current_choices = wikihow_query_result[choice_start_idx : choice_start_idx + 3]
    else:
        current_choices = wikihow_query_result[choice_start_idx : num_results]
    
    views = [(int(i["_source"]['views']) if i["_source"]['views'] else 0) for i in current_choices ]
    ratings = [ (int(i["_source"]['rating']) if i["_source"]['rating'] else 0) for i in current_choices]
    return current_choices, views, ratings 


def taco_recipe_compare(current_state, last_state, user_attributes):
    recipe_query_result = getattr(user_attributes, 'query_result', None)
    choice_start_idx = getattr(user_attributes, 'choice_start_idx', 0)
    
#     print('recipe_query_result recipe_query_result recipe_query_result = ', recipe_query_result)
    recipes = recipe_helpers.query_to_recipes(recipe_query_result)
#     tmp 20221002
#     recipes = recipe_query_result
    num_results = len(recipes)

    current_choices, ratings, diff = get_recipe_info(recipes, choice_start_idx, num_results)
    idx_min_diff = diff.index(min(diff))
    min_diff_task = current_choices[idx_min_diff].title
    idx_max_ratings = ratings.index(max(ratings))
    max_rating_task = current_choices[idx_max_ratings].title

    out = ''
    if min(diff) < 3 and max(ratings) > 0:
        if idx_min_diff == idx_max_ratings:
            out = (
                f"I recommend the <say-as interpret-as=\"ordinal\"> {idx_min_diff + 1} </say-as> recipe, {min_diff_task}! " + 
                "It is the easiest and has the highest rating. Do you want to choose it? "
            )
            setattr(user_attributes, 'list_item_rec', idx_min_diff)
        else:
            out = (
                f"The <say-as interpret-as=\"ordinal\"> {idx_max_ratings + 1} </say-as> recipe, {max_rating_task}, has the highest rating. " + 
                f"The <say-as interpret-as=\"ordinal\"> {idx_min_diff + 1} </say-as> recipe, {min_diff_task}, is the easiest recipe. " +
                f"Do you want the <say-as interpret-as=\"ordinal\"> {idx_max_ratings + 1} </say-as> or the <say-as interpret-as=\"ordinal\"> {idx_min_diff + 1} </say-as> recipe? "
            )
    elif min(diff) < 3:
        out = f"I recommend the <say-as interpret-as=\"ordinal\"> {idx_min_diff + 1} </say-as> recipe, {min_diff_task}! It is the easiest. "
        out += 'Do you want to choose it? '
        setattr(user_attributes, 'list_item_rec', idx_min_diff)
    elif max(ratings) > 0:
        out = f"I recommend the <say-as interpret-as=\"ordinal\"> {idx_max_ratings + 1} </say-as> recipe, {max_rating_task}! It has the highest rating. "
        out += 'Do you want to choose it? '
        setattr(user_attributes, 'list_item_rec', idx_max_ratings)
    else:
        first_task = current_choices[0].title
        out = f"I recommend the first task, {first_task}. It is the most relevant task I found. Do you want to choose it? "
        setattr(user_attributes, 'list_item_rec', 0)
    
    return {'response': out, 'shouldEndSession': False} 


def get_recipe_info(recipes, choice_start_idx, num_results):
    if choice_start_idx + 3 <= num_results:    
        current_choices = recipes[choice_start_idx : choice_start_idx + 3]
    else:
        current_choices = recipes[choice_start_idx : num_results]
    
    ratings = [(recipe.rating if recipe.rating else 0) for recipe in current_choices]
    diff = [(recipe.difficulty if isinstance(recipe.difficulty, int) else 3) for recipe in current_choices]
    return current_choices, ratings, diff 