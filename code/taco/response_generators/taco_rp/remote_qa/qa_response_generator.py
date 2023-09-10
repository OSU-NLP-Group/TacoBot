import logging
from typing import Optional

from taco.core.response_generator import ResponseGenerator
from taco.core.response_priority import ResponsePriority, PromptType
from taco.core.response_generator_datatypes import emptyResult, ResponseGeneratorResult, PromptResult, emptyPrompt, \
    UpdateEntity, AnswerType
from taco.core.regex.regex_template import RegexTemplate
from taco.core.regex.response_lists import RESPONSE_TO_THATS, RESPONSE_TO_DIDNT_KNOW
from taco.response_generators.food.regex_templates import *
from taco.core.regex.util import OPTIONAL_TEXT_PRE, OPTIONAL_TEXT_POST

# treelets
from taco.response_generators.taco_rp.remote_qa.treelets.faq_qa_treelet import FAQ_qa_Treelet
from taco.response_generators.taco_rp.remote_qa.treelets.mrc_qa_treelet import MRC_qa_Treelet
from taco.response_generators.taco_rp.remote_qa.treelets.ooc_qa_treelet import OOC_qa_Treelet

# treelets
from taco.core.offensive_classifier.offensive_classifier import OffensiveClassifier
from taco.core.response_generator.response_type import add_response_types, ResponseType

from taco.response_generators.taco_rp.remote_qa.state import *


# response type
ADDITIONAL_RESPONSE_TYPES = ['NEEDED_remoteQA']
ResponseType = add_response_types(ResponseType, ADDITIONAL_RESPONSE_TYPES)
        
logger = logging.getLogger('tacologger')


class Remote_QA_Generator(ResponseGenerator):
    name='Remote_QA_INTERNT'

    def __init__(self, state_manager) -> None:

        self.faq_treelet = FAQ_qa_Treelet(self)
        self.mrc_treelet = MRC_qa_Treelet(self)
        self.ooc_treelet = OOC_qa_Treelet(self)
        
        treelets = {
            treelet.name: treelet for treelet in [self.faq_treelet, self.mrc_treelet, self.ooc_treelet]
        }
        super().__init__(state_manager, treelets=treelets, intent_templates=[], can_give_prompts=True,
                         state_constructor=State,
                         conditional_state_constructor=ConditionalState,
                         trigger_words=["preparation_response"])

    def handle_default_post_checks(self) -> Optional[ResponseGeneratorResult]:
        
        question_types = getattr(self.state_manager.current_state, 'questiontype', None)

        faq_response = self.treelets['FAQ_qa_treelet'].get_response(self.state_manager)
        mrc_response = self.treelets['MRC_qa_treelet'].get_response(self.state_manager)
        ooc_response = self.treelets['OOC_qa_treelet'].get_response(self.state_manager)

        print('faq_response = ', faq_response)
        print('mrc_response = ', mrc_response)
        print('ooc_response = ', ooc_response)
        print('question_types = ', question_types['question_types'])
        
        for rp in question_types['question_types']:
            if rp == 'MRC' and mrc_response.text != '' and "Sorry, I can't find the good answer" not in mrc_response.text:
                self.state_manager.current_state.response_generator_states[self.name].cur_treelet_str = 'MRC_qa_treelet'
                return mrc_response

            if rp == 'FAQ' and faq_response.text != ''  and "Sorry, I can't find the good answer" not in  faq_response.text:
                self.state_manager.current_state.response_generator_states[self.name].cur_treelet_str = 'FAQ_qa_treelet'
                return faq_response

            if rp == 'EVI' and ooc_response.text != ''  and "Sorry, I can't find the good answer" not in  ooc_response.text:
                self.state_manager.current_state.response_generator_states[self.name].cur_treelet_str = 'OOC_qa_treelet'
                return ooc_response

        return mrc_response

    def identify_response_types(self, utterance):
        response_types = super().identify_response_types(utterance)
        response_types.add(ResponseType.NEEDED_remoteQA)
        return response_types
