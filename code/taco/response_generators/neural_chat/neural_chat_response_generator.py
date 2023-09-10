from typing import Optional
import logging
from datetime import datetime
import random

from taco.core.response_generator.response_type import *
from taco.core.response_generator import ResponseGenerator
from taco.core.response_generator_datatypes import ResponseGeneratorResult, emptyResult, PromptResult, emptyPrompt, PromptType, UpdateEntity
from taco.core.response_generator_datatypes import ResponsePriority, emptyResult_with_conditional_state, AnswerType
# from taco.core.response_generator_datatypes import ResponseGeneratorResult, PromptResult, emptyResult, \
    # emptyResult_with_conditional_state, emptyPrompt, UpdateEntity, AnswerType

from taco.response_generators.neural_chat.state import State, ConditionalState, UserLabel, BotLabel
from taco.response_generators.neural_chat.treelets.currentandrecentactivities_treelet import CurrentAndRecentActivitiesTreelet
from taco.response_generators.neural_chat.treelets.futureactivities_treelet import FutureActivitiesTreelet
from taco.response_generators.neural_chat.treelets.generalactivities_treelet import GeneralActivitiesTreelet
from taco.response_generators.neural_chat.treelets.emotions.emotions_treelet import EmotionsTreelet
from taco.response_generators.neural_chat.treelets.livingsituation_treelet import LivingSituationTreelet
from taco.response_generators.neural_chat.treelets.food_treelet import FoodTreelet
from taco.response_generators.neural_chat.treelets.familymember_treelets.familymember_treelets import OlderFamilyMembersTreelet, FriendsTreelet, SiblingsCousinsTreelet, PetsTreelet, KidsTreelet, PartnersTreelet
from taco.response_generators.neural_chat.treelets.icebreaker_treelet import IcebreakerTreelet
from taco.response_generators.neural_chat.treelets.go_back_treelet import GO_BACK_Treelet
from taco.core.smooth_handoffs import SmoothHandoff
from taco.response_generators.neural_chat.state import State, ConditionalState

logger = logging.getLogger('tacologger')

# dict mapping name (str) to Treelet class
NAME2TREELET = {treelet.__name__: treelet for treelet in [CurrentAndRecentActivitiesTreelet,
                                                          FutureActivitiesTreelet,
                                                          GeneralActivitiesTreelet, EmotionsTreelet,
                                                          LivingSituationTreelet, FoodTreelet,
                                                          OlderFamilyMembersTreelet, FriendsTreelet,
                                                          SiblingsCousinsTreelet,
                                                          PetsTreelet, KidsTreelet, PartnersTreelet,
                                                          GO_BACK_Treelet,
                                                          # IcebreakerTreelet,
                                                          ]}

# replace with this to test sports
# NAME2TREELET = {treelet.__name__: treelet for treelet in [CurrentAndRecentActivitiesTreelet]}

def get_test_args_treelet(current_state) -> Optional[str]:
    """If TestArgs specify a neural chat treelet, return it. Otherwise return None."""
    if hasattr(current_state, 'test_args') and \
        hasattr(current_state.test_args, 'neural_chat_args') and \
            'treelet' in current_state.test_args.neural_chat_args:
                test_args_treelet = current_state.test_args.neural_chat_args['treelet']
                return test_args_treelet
    return None





class NeuralChatResponseGenerator(ResponseGenerator):
    """
    This RG uses a conversational model to generate responses.
    """
    name='NEURAL_CHAT'
    def __init__(self, state_manager):

        super().__init__(state_manager, state_constructor=State, conditional_state_constructor=ConditionalState)
        self.killable = True

    def continue_conversation(self, response_types) -> Optional[ResponseGeneratorResult]:
        # TODO get rid of this once neural chat is refactored
        return None

    def choose_treelet_result(self, treeletname2result, current_state, use_test_args=True):
        """If a treelet is specified in test_args, choose that, otherwise randomly sample"""
        test_args_treelet = get_test_args_treelet(current_state)
        if test_args_treelet and use_test_args:
            sampled_treelet_name = test_args_treelet
            logger.taco_merge(f'According to test args, choosing {test_args_treelet} instead of starting with Food')
        else:
            started_with_food = self.get_user_attribute('started_with_food', False)
            if started_with_food:
                sampled_treelet_name = random.choice(list(treeletname2result.keys()))
                logger.taco_merge(f'Sampled treelet {sampled_treelet_name} from these: {treeletname2result.keys()}')
            else:
                sampled_treelet_name = 'FoodTreelet'
                self.set_user_attribute('started_with_food', True)
        sampled_response = treeletname2result[sampled_treelet_name]

        logger.taco_merge(f'choose_treelet_result = {sampled_treelet_name}')
        return sampled_response

    def handle_personal_issue(self, slots):
        if datetime.now() >= datetime(2021, 7, 1):
            return None
        else:
            name2initializedtreelet = {treelet_name: treelet_class(self) for treelet_name, treelet_class in NAME2TREELET.items()}
            logger.taco_merge("Personal issue handler invoked")
            next_treelet = name2initializedtreelet['CurrentAndRecentActivitiesTreelet']
            response = next_treelet.get_response(self.state, force=True)
            logger.taco_merge(f"Response is: {response}")
            return response

    def handle_user_want_stop(self, prefix='', main_text=None, suffix='',
                                  priority=ResponsePriority.STRONG_CONTINUE, needs_prompt=True,
                                  conditional_state=None, answer_type=AnswerType.ENDING):

        main_text = self.choose([
            "Alright.",
            "Okay no problem"])

        logger.primary_info(f"{self.name} received rejection response, so resetting state to null (currently) {self.state}")
        state = self.update_state_if_not_chosen(self.state, conditional_state if conditional_state else self._construct_no_update_conditional_state())
        n_conditional_state = conditional_state if conditional_state else self._construct_no_update_conditional_state()
        n_conditional_state.bot_labels += BotLabel.HANDOVER

        return ResponseGeneratorResult(
            text=f"{prefix} {main_text} {suffix}",
            priority=priority,
            needs_prompt=needs_prompt, state=state,
            cur_entity=None,
            no_transition=True,
            conditional_state=n_conditional_state,
            answer_type=answer_type
        )

    def handle_default_post_checks(self) -> Optional[ResponseGeneratorResult]:
        state = self.state
        # import pdb; pdb.set_trace()
        # Init all treelets
        name2initializedtreelet = {treelet_name: treelet_class(self) for treelet_name, treelet_class in NAME2TREELET.items()}

        response_types = self.identify_response_types(self.utterance)

        if ResponseType.REQUEST_STOP in response_types:
            response = self.handle_user_want_stop()
            if response:
                logger.primary_info(f"{self.name} received a response from")
                return self.possibly_augment_with_prompt(response)


        # Run update_state for all treelets
        for treelet in name2initializedtreelet.values():
            treelet.update_state(state)

        # If there is a next treelet to run, get response from it
        if state.next_treelet is not None:
            next_treelet = name2initializedtreelet[state.next_treelet]  # initialized treelet
            logger.taco_merge(f'Continuing neural conversation in {state.next_treelet}')
            # import pdb; pdb.set_trace()
            return next_treelet.get_response(state)

        # no entity tracker available
        # if self.state_manager.current_state.entity_tracker.is_personal_posnav:
        #     logger.taco_merge("Detected personal posnav...")
        #     next_treelet = name2initializedtreelet['CurrentAndRecentActivitiesTreelet']
        #     response = next_treelet.get_response(state, force=True)
        #     logger.taco_merge(f"Response is: {response}")
        #     return response

        # If any unused treelet has a starter question response, give it
        # unused_treelet_names = [treelet_name for treelet_name in name2initializedtreelet if not state.treelet_has_been_used(treelet_name)]  # list of treelet names
        # logger.taco_merge(f'Getting starter question responses from these unused treelets: {unused_treelet_names}')
        # treeletname2responseresult = {treelet_name: name2initializedtreelet[treelet_name].get_starter_question_response(state) for treelet_name in unused_treelet_names}
        # treeletname2responseresult = {treelet_name: response_result for treelet_name, response_result in treeletname2responseresult.items() if response_result is not None}
        # if len(treeletname2responseresult):
        #     logger.taco_merge("Got these starter questions from neural chat treelets:\n{}".format('\n'.join([f"{treelet_name}: {response_result}" for treelet_name, response_result in treeletname2responseresult.items()])))
        # else:
        #     logger.warning("Neural chat treelets returned no starter questions.")
        # if treeletname2responseresult:
        #     top_priority = max([response_result.priority for response_result in treeletname2responseresult.values()])
        #     treeletname2responseresult = {treelet_name: response_result for treelet_name, response_result in treeletname2responseresult.items() if response_result.priority == top_priority}
        #     logger.taco_merge(f"Restricting to just these results with top_priority={top_priority.name}: {treeletname2responseresult.keys()}")
        #     sampled_response = self.choose_treelet_result(treeletname2responseresult, self.state_manager.current_state, use_test_args=False)
        #     return sampled_response

        return emptyResult(state)


    def handle_rejection_response(self, *args, **kwargs):
        result = super().handle_rejection_response(*args, **kwargs)
        result.conditional_state.next_treelet = None
        return result



    def get_launch_prompt(self, name2initializedtreelet, state) -> Optional[PromptResult]:
        """Get a starter question prompt to be used as part of launch sequence"""
        treeletname2launchprompt = {treelet_name: treelet.get_prompt(state, for_launch=True) for treelet_name, treelet in name2initializedtreelet.items() if treelet.launch_appropriate}
        logger.taco_merge("LAUNCH is doing smooth handoff to NEURAL_CHAT. Got these launch-appropriate starter questions:\n{}".format('\n'.join([f"{treelet_name}: {prompt_result}" for treelet_name, prompt_result in treeletname2launchprompt.items()])))
        treeletname2launchprompt = {treelet_name: prompt_result for treelet_name, prompt_result in treeletname2launchprompt.items() if prompt_result is not None}
        if not treeletname2launchprompt:
            logger.error(f'LAUNCH is doing smooth handoff to NEURAL_CHAT, but no launch treelets are appropriate')
            return None
        else:
            prompt_result = self.choose_treelet_result(treeletname2launchprompt, self.state_manager.current_state)
            prompt_result.type = PromptType.FORCE_START
            return prompt_result


    def get_prompt(self, state: State) -> PromptResult:
        # Init all treelets
        name2initializedtreelet = {treelet_name: treelet_class(self) for treelet_name, treelet_class in NAME2TREELET.items()}

        # print('State = ', state)
        if state.should_go_back_instruction == True:
            print('state.should_go_back_instruction = ', state.should_go_back_instruction)

            response_types = self.identify_response_types(self.utterance)
            state.response_types = response_types
            
            selected_prompt =  name2initializedtreelet['GO_BACK_Treelet'].get_prompt(state)
            selected_prompt.conditional_state.next_treelet = None
            return selected_prompt
            # GO_BACK_Treelet


        # Complete a smooth handoff if required
        # if self.state_manager.current_state.smooth_handoff == SmoothHandoff.LAUNCH_TO_NEURALCHAT:
        #     launch_prompt_result = self.get_launch_prompt(name2initializedtreelet, state)
        #     if launch_prompt_result:
        #         return launch_prompt_result

        # Otherwise, get starter question prompts from all unused treelets
        unused_treelet_names = [treelet_name for treelet_name in name2initializedtreelet if not state.treelet_has_been_used(treelet_name)]  # list of treelet names
        logger.taco_merge(f'Getting starter question prompts from these unused treelets:\n{unused_treelet_names}')
        treeletname2promptresult = {treelet_name: name2initializedtreelet[treelet_name].get_prompt(state) for treelet_name in unused_treelet_names}
        treeletname2promptresult = {treelet_name: prompt_result for treelet_name, prompt_result in treeletname2promptresult.items() if prompt_result is not None}
        logger.taco_merge("Got these starter questions from neural chat treelets:\n{}".format('\n'.join([f"{treelet_name}: {prompt_result}" for treelet_name, prompt_result in treeletname2promptresult.items()])))

        # Sample one of highest priority and return
        if treeletname2promptresult:
            top_priority = max([prompt_result.type for prompt_result in treeletname2promptresult.values()])
            treeletname2promptresult = {treelet_name: prompt_result for treelet_name, prompt_result in treeletname2promptresult.items() if prompt_result.type==top_priority}
            logger.taco_merge(f"Restricting to just these results with top_priority={top_priority.name}: {treeletname2promptresult.keys()}")

            # If a treelet is specified by test args, choose that. Otherwise randomly sample.
            sampled_prompt = self.choose_treelet_result(treeletname2promptresult, self.state_manager.current_state, use_test_args=False)
            return sampled_prompt
        else:
            logger.taco_merge(f'Neural Chat has no more unused treelets left, so giving no prompt')
            return emptyPrompt(state)


    def update_state_if_chosen(self, state: State, conditional_state: Optional[ConditionalState]) -> State:
        assert conditional_state is not None, "conditional_state shouldn't be None if the response/prompt was chosen"

        print('neual chat conditional_state = ', conditional_state)
        state.update_if_chosen(conditional_state)
        return state

    def update_state_if_not_chosen(self, state: State, conditional_state: Optional[ConditionalState]) -> State:
        logger.taco_merge(f"Neural chat state is {state}")
        if conditional_state is not None:
            state.update_if_not_chosen(conditional_state)
        return state
