from taco.core.response_generator.response_type import add_response_types, ResponseType
import logging
from taco.response_generators.wiki2.regex_templates import *
from taco.annotators.corenlp import Sentiment
from taco.response_generators.wiki2.response_templates.response_components import ERROR_ADMISSION, \
    APPRECIATION_DEFAULT_ACKNOWLEDGEMENTS, COMMISERATION_ACKNOWLEDGEMENTS
from typing import Optional, Tuple

logger = logging.getLogger('tacologger')

ADDITIONAL_RESPONSE_TYPES = ['CONFUSED', 'WHAT_ABOUT_YOU', 'HIGH_INITIATIVE', 'POS_SENTIMENT', 'NEG_SENTIMENT',
                             'NEUTRAL_SENTIMENT', 'KNOW_MORE', 'PERSONAL_DISCLOSURE', 'AGREEMENT', 'DISAGREEMENT',
                             'APPRECIATIVE', 'OPINION', 'STARTS_WITH_WHAT']

ResponseType = add_response_types(ResponseType, ADDITIONAL_RESPONSE_TYPES)

def user_is_confused(rg, utterance):
    return (ClarificationQuestionTemplate().execute(utterance) and not rg.get_navigational_intent_output().pos_intent) \
           or DoubtfulTemplate().execute(utterance)

def is_high_initiative(rg, utterance):
    corenlp_output = rg.state_manager.current_state.corenlp
    return not ((len(utterance) <= 4 and not corenlp_output['nouns'] and
                 not corenlp_output['proper_nouns']) or len(utterance) <= 3)

def is_pos_sentiment(rg, utterance):
    return rg.get_sentiment() in [Sentiment.POSITIVE, Sentiment.STRONG_POSITIVE]

def is_neg_sentiment(rg, utterance):
    return rg.get_sentiment() in [Sentiment.NEGATIVE, Sentiment.STRONG_NEGATIVE]

def is_neutral_sentiment(rg, utterance):
    return rg.get_sentiment() == Sentiment.NEUTRAL

def is_appreciative(rg, utterance):
    return rg.get_top_dialogact() == 'appreciation' or AppreciativeTemplate().execute(utterance) is not None

def starts_with_what(rg, utterance):
    tokens = list(utterance.split())
    return 'what' in tokens[:3]

def user_wants_to_know_more(rg, utterance):
    return KnowMoreTemplate().execute(utterance) is not None

FIRST_PERSON_WORDS = {
    "i", "i'd", "i've", "i'll", "i'm",
    "me", "my", "myself", "mine"
}

def contains_first_person_word(utterance):
    tokens = set(utterance.split())
    return not tokens.isdisjoint(FIRST_PERSON_WORDS)

def is_personal_disclosure(rg, utterance):
    return contains_first_person_word(utterance) and len(utterance.split()) >= 5

def is_opinion(rg, utterance):
    return utterance.startswith('because') or \
           'opinion' in (rg.state_manager.current_state.dialogact['top_1'], rg.state_manager.current_state.dialogact['top_2']) or \
           any([utterance.startswith(x) for x in ['i believe', 'i think', 'i feel']])

def is_no_to_sections(rg, utterance):
    state = rg.state
    tokens = set(utterance.split())
    if state and state.prev_treelet_str == rg.discuss_article_treelet.name:
        NO_WORDS = {'neither', 'else', 'nothing', 'none', "not"}
        return not tokens.isdisjoint(NO_WORDS)

# def is_yes_to_user_knowledge(rg, utterance):
#     state =

def user_agrees(rg, utterance):
    return AgreementTemplate().execute(utterance) is not None

def user_disagees(rg, utterance):
    return DisagreementTemplate().execute(utterance) is not None

def original_til_templates(apologize: bool, original_til: str):
    APOLOGIZE_THEN_ORIGINAL = \
        ["Sometimes I get things wrong. ",
         "Every so often I have trouble understanding what I read. ",
         "Let's see if I can read it again more clearly this time. ",
         "Oh, sorry, maybe I misremembered the details. " ,
         "Ah, sorry, maybe I said it wrong. "]
    THEN_ORIGINAL = [
        f"I'll quote the source. I've read on wikipedia that {original_til}.",
        f"Going back to the original version, it said {original_til}.",
        f"What I saw on Wikipedia was that {original_til}.",
        f"Let's see, I think the original version was that {original_til}.",
        F"I remember the original version on Wikipedia saying that {original_til}."
    ]

    if apologize:
        return [a+b for (a, b) in zip(APOLOGIZE_THEN_ORIGINAL, THEN_ORIGINAL)]
    else:
        return THEN_ORIGINAL


QUESTION_CONNECTORS = [
    "So ",
    "This is a little random but ",
    "There's actually something else I wanted to ask you about, ",
    "This is unrelated but I was just thinking, ",
    "So, I just thought of something. ",
    "Anyway, um, on another subject. ",
    "Hmm, so, on another topic. ",
    "Oh hey, I just remembered another thing I've been wondering about. ",
    "Anyway, there’s actually an unrelated thing I wanted to know. ",
    "This is a bit random, but I just remembered something I wanted to ask you. "
]

def get_user_initiated_entitiy(user_utterance, current_state) -> Tuple[Optional[str], bool]:
    """
    If the user utterance matches RegexTemplate, return the name of the category they're asking for.
    Otherwise return None.

    Returns:
        category: the category being activated
        posnav: whether the user has posnav
    """
    slots = CategoriesTemplate().execute(user_utterance)

    # Legacy code; not removing in case it breaks something
    # if slots is not None and slots["keyword"] in ACTIVATIONPHRASE2CATEGORYNAME:
    #     category_name = ACTIVATIONPHRASE2CATEGORYNAME[slots['keyword']]
    #     logger.primary_info(f'Detected categories intent for category_name={category_name} and slots={slots}.')
    #     return category_name, True

    # If any activation phrase is in the posnav slot, activate with force_start
    nav_intent = getattr(current_state, 'navigational_intent', None)
    if nav_intent and nav_intent.pos_intent and nav_intent.pos_topic_is_supplied:
        pos_topic = nav_intent.pos_topic[0]  # str
        for activation_phrase, category_name in ACTIVATIONPHRASE2CATEGORYNAME.items():
            if contains_phrase(pos_topic, {activation_phrase}, lowercase_text=False, lowercase_phrases=False, remove_punc_text=False, remove_punc_phrases=False):
                logger.primary_info(f"Detected categories activation phrase '{activation_phrase}' in posnav slot, so categories is activating with force_start")
                return category_name, True

    # If any activation phrase is in the user utterance, activate with can_start
    for activation_phrase, category_name in ACTIVATIONPHRASE2CATEGORYNAME.items():
        if contains_phrase(user_utterance, {activation_phrase}, lowercase_text=False, lowercase_phrases=False, remove_punc_text=False, remove_punc_phrases=False):
            logger.primary_info(f"Detected categories activation phrase '{activation_phrase}' in utterance (but not in a posnav slot), so categories is activating with can_start")
            return category_name, False

    return None, False