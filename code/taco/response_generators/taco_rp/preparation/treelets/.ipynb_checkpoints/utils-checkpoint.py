import re

from taco.response_generators.taco_rp.preparation.treelets.stop_word import np_ignore_list

def get_query_result_selected(is_apl_supported, current_state, last_state, user_attributes):
    """
    Gets the index of the currently selected item.
    """

    # For testing
    # is_apl_supported = False
    # For testing


    list_item_selected = getattr(user_attributes, "list_item_selected", -1)
    intent = current_state.final_intent

    if intent == "UserEvent":
        user_event = getattr(current_state, "user_event", {})
        arguments = user_event.get("arguments", [])
        touch_selected = arguments[1] if len(arguments) > 1 else -1
        if touch_selected > 0:
            list_item_selected = touch_selected - 1
    else:
        list_item_rec = getattr(user_attributes, "list_item_rec", -1)

        if list_item_selected < 0:
            if current_state.final_intent == "AcknowledgeIntent":
                list_item_selected = list_item_rec + getattr(
                    user_attributes, "choice_start_idx", 0
                )
            else:
                list_item_selected = get_list_item_selected(
                    is_apl_supported, current_state, user_attributes
                )

                choice_start_idx = getattr(user_attributes, "choice_start_idx", 0)
                
                last_state_dict = getattr(user_attributes, "last_state_dict", None)
                last_intent = None
                if last_state_dict:
                    if 'final_intent' in last_state_dict:
                        last_intent = last_state_dict['final_intent']
                else:
                    # Use StateTable as backup. NOTE It may be erroneous!        
                    last_intent = last_state["final_intent"] if last_state is not None and "final_intent" in last_state else ""
                                
                if (
                    is_apl_supported
                    and choice_start_idx > 0
                    and last_intent != "UserEvent"
                ):
                    list_item_selected += 1

    setattr(user_attributes, "list_item_selected", list_item_selected)

    return list_item_selected


def get_list_item_selected(is_apl_supported, current_state, user_attributes):
    """
    Returns the index of the list item selected by the user, with 0 as the first item index
    """
    tokens = current_state.text.split()
    text = current_state.text.lower()

    list_item_selected = -1
    if is_apl_supported:
        slots = getattr(current_state, "slots", {})
        try:
            if slots and "ListPosition" in slots:
                list_item_selected = int(slots.get("ListPosition", {}).get("value", -1))
        except:
            list_item_selected = -1

        if list_item_selected < 1:
            list_item_selected = _get_selection_from_str(tokens, text)
        # To figure out the right item in the list, find out what items in the list are displayed.
        # User could say, "select the 3rd item" after scrolling the list to the right,
        # so that item could actually be the 6th item in the list.
        list_items_displayed_on_screen = (
            getattr(current_state, "visible_components", {})
            .get("apl", {})
            .get("displayed_items", [])
        )
        count = 1
        for item in list_items_displayed_on_screen:
            if count == list_item_selected:
                list_item_selected = item.get("ordinal", -1)
                break
            count = count + 1
    else:
        choice_start_idx = getattr(user_attributes, "choice_start_idx", 0)
        slots = getattr(current_state, "slots", {})
        try:
            if slots and "ListPosition" in slots:
                list_item_selected = int(slots.get("ListPosition", {}).get("value", -1))
        except:
            list_item_selected = -1

        if list_item_selected < 1:
            list_item_selected = _get_selection_from_str(tokens, text)

        if list_item_selected >= 1:
            list_item_selected += choice_start_idx

    if list_item_selected >= 1:
        return list_item_selected - 1

    return 0

def _get_selection_from_str(tokens, text):
    list_item_selected = -1
    if ("first" in tokens) or ("initial" in tokens) or ("left" in tokens):
        list_item_selected = 1
    elif ("second" in tokens) or ("two" in tokens) or ("middle" in tokens):
        list_item_selected = 2
    elif ("third" in tokens) or ("three" in tokens) or ("last" in tokens) or ("right" in tokens):
        list_item_selected = 3
    elif re.search(r'\b(?<!which )(?<!what )one\b', text):
        list_item_selected = 1
    return list_item_selected


def should_include_headline(sent, query):
    tokens = sent.lower().split()
    useful_tokens = [t for t in tokens if t not in np_ignore_list]
    return (
        len(tokens) <= 20 and
        any(t in query for t in useful_tokens)
    )
