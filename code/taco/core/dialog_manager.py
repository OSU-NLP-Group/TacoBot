import json
import copy
import logging
import time
from typing import Dict, List, Optional

from taco.core.callables import run_multithreaded, ResponseGenerators
from taco.core.state_manager import StateManager
from taco.core.priority_ranking_strategy import PriorityRankingStrategy
from taco.core.flags import use_timeouts, inf_timeout
from taco.core.priority_ranking_strategy import RankedResults
from taco.core.response_generator_datatypes import ResponseGeneratorResult, PromptResult, UpdateEntity, CONTINUING_ANSWER_TYPES, is_killed
from taco.core.util import print_dict_linebyline, sentence_join, taco_RP_NAME
from taco.core.offensive_classifier.offensive_classifier import contains_offensive
from taco.response_generators.closing_confirmation.closing_confirmation_response_generator import CLOSING_CONFIRMATION_STOP
from taco.core.latency import measure

import sys
import os
sys.path.insert(0, os.getcwd()+'/taco/core/')

# from taco_selecting_strategy import TacoSelectingStrategy
from taco.core.taco_selecting_strategy import TacoSelectingStrategy
from taco.core.taco_ranking_strategy import TacoRankingStrategy


logger = logging.getLogger('tacologger')

class DialogManager:
    # These timeouts are in seconds
    INIT_STATE_TIMEOUT = 1 if use_timeouts else inf_timeout
    GET_ENTITY_TIMEOUT = 1 if use_timeouts else inf_timeout
    GET_RESPONSE_TIMEOUT = 20 if use_timeouts else inf_timeout
    GET_PROMPT_TIMEOUT = 20 if use_timeouts else inf_timeout
    UPDATE_STATE_TIMEOUT = None  # timeout for update_state_if_chosen and update_state_if_not_chosen fns
    # OFFENSIVE_TIMEOUT = 2 if use_timeouts else inf_timeout

    def __init__(self,
                 state_manager: StateManager,
                 response_generators: ResponseGenerators,
                 selecting_strategy: TacoSelectingStrategy,
                 prompt_ranking_strategy: PriorityRankingStrategy,
                 ranking_strategy: TacoRankingStrategy
                 # TODO add response_generators as constructor argument
                 ) -> None:

        self.state_manager = state_manager
        self.ranking_strategy = ranking_strategy
        self.prompt_ranking_strategy = prompt_ranking_strategy
        self.selecting_strategy = selecting_strategy
        self.response_generators = response_generators

    @measure
    def execute_turn(self) -> (str, str, bool):
        """
        Execute one turn of dialogue.

        Returns:
            utterance: string (cannot be empty or None).
            should_end_session: bool. Currently this is always False, but we might want to change it in the future
                e.g. if the user is being persistently offensive, talking about topics we aren't able to deal with,
                or the conversation is going really badly.
        """

        should_end_session = False
        logger.primary_info('Current state:\n{}'.format(print_dict_linebyline(self.state_manager.current_state.__dict__)),
                            extra={'color_lines_by_component': True})

        self.init_rg_states()  # Get RG states from last turn (or on first turn, run RGs' init_state fns)

        # Update the entity tracker state using the entity linker results
        self.update_entity_tracker_state()  # Update entity tracker's state


        if not hasattr(self.state_manager.current_state, 'turns_since_last_active'):
            turns_since_last_active = {rg_name: 34 for rg_name in self.response_generators.name_to_class}
            setattr(self.state_manager.current_state, 'turns_since_last_active', turns_since_last_active)
        try:
            for rg_name in self.response_generators.name_to_class:
                if rg_name not in self.state_manager.current_state.turns_since_last_active:
                    self.state_manager.current_state.turns_since_last_active[rg_name] = 34
                self.state_manager.current_state.turns_since_last_active[rg_name] += 1
        except Exception as e:
            logger.error(f"Error in incrementing the turns_since_last_active field! Error is {e}")

        # save turns_since_last_active state in User Table. only start saving after initial launch phase verifies
        # whether we recognize the user
        if len(self.state_manager.current_state.history) >= 6:
            setattr(self.state_manager.user_attributes, 'turns_since_last_active',
                    self.state_manager.current_state.turns_since_last_active)


        print('check_current_entities = ', self.state_manager.current_state.entity_tracker.check_current_entities())
        # input()
        # Get response (and possibly prompt)
        selected_response_rg, selected_response, selected_prompt_rg, selected_prompt = self.get_response_and_prompt()
        try:
            self.state_manager.current_state.turns_since_last_active[selected_response_rg] = 0
            if selected_prompt_rg is not None:
                self.state_manager.current_state.turns_since_last_active[selected_prompt_rg] = 0
        except Exception as e:
            logger.error(f"Error in populating the turns_since_last_active field! Error is {e}")

        # If selected_response_rg is 'CLOSING_CONFIRMATION' and the response is empty, stop immediately
        # NOTE: can't create a response with priority diff than NO if the text is None
        if selected_response_rg == 'CLOSING_CONFIRMATION' and selected_response.text == CLOSING_CONFIRMATION_STOP:
            return None, None, True

        # Record the final response and prompt RGs
        setattr(self.state_manager.current_state, 'selected_response_rg', selected_response_rg)
        setattr(self.state_manager.current_state, 'selected_prompt_rg', selected_prompt_rg)

        # Get the utterance
        if selected_prompt_rg is None:
            utterance = selected_response.text
        else:
            utterance = sentence_join(selected_response.text, selected_prompt.text)
        
        should_end_session = selected_response.should_end_session

        # Log final RG states
        logger.primary_info('Final RG states at the end of this turn:\n{}'.format(
            print_dict_linebyline(self.state_manager.current_state.response_generator_states)),
            extra={'color_lines_by_component': True})

        return utterance, should_end_session

    def update_entity_tracker_state(self):
        """
        If the last active RG's get_entity function has an updated entity, update the entity tracker's state with it
        Else update entity tracker's state using default logic in entity tracker
        """

        # Get update_entity_result from last_active_rg
        last_active_rg = self.state_manager.last_state_active_rg  # str or None
        # print('last_active_rg = ', last_active_rg)
        if last_active_rg:
            last_active_rg_state = copy.copy(self.state_manager.current_state.response_generator_states[last_active_rg])
            update_entity_results: Dict[str, UpdateEntity] = self.response_generators.run_multithreaded(
                rg_names=[last_active_rg],
                function_name='get_entity',
                args_list=[[last_active_rg_state, ]],
                timeout=DialogManager.GET_ENTITY_TIMEOUT)

            if update_entity_results and last_active_rg in update_entity_results:
                update_entity_result = update_entity_results[last_active_rg]
            else:
                logger.warning(
                    f"Failed or timed out while to running {last_active_rg}.get_entity. "
                    f"Skipping the RGs update to entity tracker")
                update_entity_result = UpdateEntity(False)
        else:
            update_entity_result = UpdateEntity(False)

        # Update the entity tracker, using update_entity_result if it has update=True
        if update_entity_result.update:
            logger.primary_info(f"Ran last_active_rg={last_active_rg}'s get_entity() function. It returned "
                                f"{update_entity_result}, so using this to update the entity tracker state",
                                extra={'color_msg_by_component': last_active_rg})
            self.state_manager.current_state.entity_tracker.update_from_rg(update_entity_result, last_active_rg, self.state_manager.current_state)
        else:
            if last_active_rg is not None:
                logger.primary_info(f"Ran last_active_rg={last_active_rg}'s get_entity() function. It returned "
                                    f"{update_entity_result}, so the entity tracker will update its state in the normal way",
                
                                    extra={'color_msg_by_component': last_active_rg})
            self.state_manager.current_state.entity_tracker.update_from_user(self.state_manager)
        # print('entity_initiated_on_turn = ', self.state_manager.current_state.entity_tracker.entity_initiated_on_turn)
        # input()

    def get_response_and_prompt(self)  -> (str, ResponseGeneratorResult, Optional[str], Optional[PromptResult]):
        """
        Gets response and possibly prompt (both checked for offensiveness).

        Returns:
            selected_response_rg: string
            selected_response: ResponseGeneratorResult
            selected_prompt_rg: string or None
            selected_prompt: PromptResult or None
        """

        # Get responses from RGs, ranked by priority
        logger.primary_info(f'Getting responses from RGs...')
        ranked_responses = self.run_rgs_and_rank('response')

        # Check that the top response isn't offensive (and remove it if it is)
        # ranked_responses = self.remove_offensive(ranked_responses)

        # Choose the top response
        selected_response, selected_response_rg = ranked_responses.top_result, ranked_responses.top_rg
        logger.primary_info(f'Selected response from {selected_response_rg}: {selected_response}',
                            extra={'color_msg_by_component': selected_response_rg})

        # If the responding RG gave a smooth_handoff identifier, put it in current_state
        setattr(self.state_manager.current_state, 'smooth_handoff', selected_response.smooth_handoff)
        if selected_response.smooth_handoff is not None:
            logger.primary_info(f"Setting current_state.smooth_handoff to {selected_response.smooth_handoff} provided "
                                f"by selected_response_rg={selected_response_rg}",
                                extra={'color_msg_by_component': selected_response_rg})

        # Update the RG states
        self.update_rg_states(ranked_responses, selected_response_rg)


        # Update the entity tracker with the response

        # taco_state = getattr(self.state_manager.current_state, 'status', None)
        # if 'PAK' in taco_state or 'chat' in taco_state:
        self.state_manager.current_state.entity_tracker.update_from_rg(selected_response, selected_response_rg, self.state_manager.current_state)

        logger.primary_info(f'selected_response = {repr(selected_response)[:100]}')

        # If the response needs a prompt, get prompts
        if selected_response.needs_prompt:

            # If we need a prompt, set the selected response RG in the state so that prompting RGs can condition on it
            setattr(self.state_manager.current_state, 'selected_response_rg', selected_response_rg)

            # Get prompts from RGs, ranked by priority
            # exclude_rgs = []
            # exclude_rgs = [selected_response_rg] if selected_response_rg != 'FALLBACK' else []  # don't run responding RG, unless it's FALLBACK
            logger.primary_info(f'Getting prompts from RGs...')
            ranked_prompts = self.run_rgs_and_rank('prompt')

            # Check that the top prompt isn't offensive (and remove it if it is)
            # ranked_prompts = self.remove_offensive(ranked_prompts)

            # Choose the top prompt
            selected_prompt, selected_prompt_rg = ranked_prompts.top_result, ranked_prompts.top_rg
            logger.debug('Selected prompt from {}: {}'.format(selected_prompt_rg, selected_prompt),
                                extra={'color_msg_by_component': selected_prompt_rg})

            # Update the RG states
            self.update_rg_states(ranked_prompts, selected_prompt_rg)

            # Update the entity tracker with the prompt
            # if 'PAK' in taco_state or 'chat' in taco_state:
            self.state_manager.current_state.entity_tracker.update_from_rg(selected_prompt, selected_prompt_rg, self.state_manager.current_state)

        else:
            selected_prompt, selected_prompt_rg = None, None

        return selected_response_rg, selected_response, selected_prompt_rg, selected_prompt


    def init_rg_states(self):
        """
        Initializes self.state_manager.current_state.response_generator_states, a dict from rg_name (str) to RG state.
        If it's the first turn of the conversation, run RGs' init_state fns.
        Otherwise get RG states from state_manager.last_state.
        """

        # If it's not the first turn, get RG states from last_state
        if self.state_manager.last_state:
            rg_states = copy.copy(self.state_manager.last_state.response_generator_states)
            logger.taco_merge('Loaded these RG states from last_state:\n{}'.format(
                print_dict_linebyline(rg_states)), extra={'color_lines_by_component': True})

            # Check for any RGs that don't have a state. Could be because their state became stale due to timeouts
            rgs_without_state = [rg_name for rg_name in self.response_generators.name_to_class if
                                 rg_name not in rg_states]

            # If so, run init_state for those RGs. This seems like the best possible graceful degradation.
            if len(rgs_without_state) > 0:
                logger.warning('These RG states do not exist in last_state:\n{}'.format(rgs_without_state))
                new_rg_states = self.response_generators.run_multithreaded(
                    rg_names=rgs_without_state,
                    function_name='init_state',
                    timeout=DialogManager.INIT_STATE_TIMEOUT)
                logger.primary_info('Ran init_state fns for RGs with missing states; got these states:\n{}'.format(
                    print_dict_linebyline(new_rg_states)), extra={'color_lines_by_component': True})
                for rg in new_rg_states:
                    rg_states[rg] = new_rg_states[rg]

        # If it's the first turn, run RGs' init_state() fns
        else:
            rg_states = self.response_generators.run_multithreaded(rg_names=self.response_generators.name_to_class.keys(),
                                          function_name='init_state',
                                          timeout=DialogManager.INIT_STATE_TIMEOUT)
            logger.primary_info("Ran RGs' init_state functions and got these states:\n{}".format(
                print_dict_linebyline(rg_states)), extra={'color_lines_by_component': True})

        # Put in current_state
        setattr(self.state_manager.current_state, 'response_generator_states', rg_states)
        logger.info(f"Current rg states are {rg_states}")


    def update_rg_states(self, results: RankedResults, selected_rg: str):
        """
        Run update_state_if_chosen fn for selected_rg, and update_state_if_not_chosen for all other RGs.
        Then update self.state_manager.current_state.response_generator_states with the new RG states.

        Inputs:
            results: RankedResults. contains the results from all RGs.
            selected_rg: str, one of the RGs in results. The chosen RG
        """
        rg_states = self.state_manager.current_state.response_generator_states

        # Get the args needed for the update_state_if_chosen fn. That's (state, conditional_state) for selected_rg
        args_list = [[rg_states[selected_rg], results[selected_rg].conditional_state]]

        # Run update_state_if_chosen for selected_rg
        logger.info(f'Starting to run update_state_if_chosen for {selected_rg}...')
        output = self.response_generators.run_multithreaded(rg_names=[selected_rg],
                                                            function_name='update_state_if_chosen',
                                                    args_list=args_list, timeout=DialogManager.UPDATE_STATE_TIMEOUT)

        if selected_rg not in output:
            # logger.error('Tried to run {}\'s update_state_if_chosen function with conditional_state={} but there was '
            #              'an error or timeout, so no update was made'.format(selected_rg, results[selected_rg].conditional_state))
            logger.error('Tried to run {}\'s update_state_if_chosen function with conditional_state but there was '
                         'an error or timeout, so no update was made'.format(selected_rg))
        else:
            rg_states[selected_rg] = output[selected_rg]
            logger.primary_info('Ran {}\'s update_state_if_chosen function with:\nconditional_state={}.\nGot new state={}'.format(
                selected_rg, results[selected_rg].conditional_state, output[selected_rg]), extra={'color_msg_by_component': selected_rg})

        # Get the args needed for the update_state_if_not_chosen fn. That's (state, conditional_state) for all RGs except selected_rg
        other_rgs = [rg for rg in results.keys() if rg != selected_rg and not is_killed(results[rg])]
        logger.info(f"now, current states are {rg_states}")
        args_list = [[rg_states[rg], results[rg].conditional_state] for rg in other_rgs]

        # Run update_state_if_not_chosen for other RGs
        logger.info(f'Starting to run update_state_if_not_chosen for {other_rgs}...')
        output = self.response_generators.run_multithreaded(rg_names=other_rgs, function_name='update_state_if_not_chosen',
                                                    args_list=args_list, timeout=DialogManager.UPDATE_STATE_TIMEOUT)

        # Save the updated states in rg_states
        for rg in other_rgs:
            if rg not in output:
                logger.error('Tried to run {}\'s update_state_if_not_chosen function with conditional_state={} but there was an '
                             'error or timeout, so no update was made'.format(rg, results[rg].conditional_state))
            else:
                rg_states[rg] = output[rg]
                logger.info('Ran {}\'s update_state_if_not_chosen function with:\nconditional_state={}\nGot new state={}'.format(
                    rg, results[rg].conditional_state, output[rg]), extra={'color_msg_by_component': rg})


    def rg_state_setting(self, phase, exclude_rgs):
        rg_states = self.state_manager.current_state.response_generator_states

        # Get list of RGs to run (all except exclude_rgs, and any that don't have a state due to an earlier error)


        if phase == 'response':
            rgs_list = self.selecting_strategy.select_response_mode()
        else:
            taco_state = getattr(self.state_manager.current_state, 'status', None)
            if 'Instruction' in taco_state:
                # only do one time people ask question
                 # we ask one pak question if user interests and we would go to PAK and allows user to chitchat
                rgs_list = ['exception_INTERNT', 'execution_INTERNT'] 
            elif 'PAK' in taco_state or 'chat' in taco_state:
                # if PAK always chitchat
                rgs_list = taco_RP_NAME 
                # ['NEURAL_CHAT', 'NEURAL_FALLBACK']

        # Get the states for the RGs we'll run, which we'll use as input to the get_response/get_prompt fn
        logger.debug('Copying RG states to use as input...')
        input_rg_states = copy.copy([rg_states[rg] for rg in rgs_list])  # list of dicts

        # Get results from the RGs in parallel, running either get_response or get_prompt.
        # results_dict is a dict mapping from RG name to a ResponseGeneratorResult/PromptResult
        timeout = DialogManager.GET_RESPONSE_TIMEOUT if phase == 'response' else DialogManager.GET_PROMPT_TIMEOUT
        last_state_active_rg = self.state_manager.last_state_active_rg
        # if last_state_active_rg and self.state_manager.last_state_response.answer_type in CONTINUING_ANSWER_TYPES:
        #     priority_modules = [last_state_active_rg]
        # else:
        priority_modules = []
                
        return rg_states, rgs_list, timeout, input_rg_states, priority_modules
                
                
    def run_rgs_and_rank(self, phase: str, exclude_rgs : List[str] = []) -> RankedResults:
        """
        Run RGs' get_response/get_prompt (depending on phase).
        Save RG states that are returned in the ResponseGeneratorResults/PromptResults.
        Sort the results by priority.

        Arguments:
            phase: 'response' or 'prompt'; the phase you want to run
            exclude_rgs: list of RGs that you DON'T want to run

        Returns:
            ranked_results: RankedResults, ordered by descending priority.
        """
                
        def correct_results(phase, results_dict):
            # Check results are correct type
            correct_result_type = ResponseGeneratorResult if phase == 'response' else PromptResult
            for rg in list(results_dict.keys()):
                result = results_dict[rg]
                if not isinstance(result, correct_result_type):
                    logger.error('{} returned a {} of type {} instead of {}. Removing it from results.'.format(
                        rg, phase, type(result), correct_result_type))
                    del results_dict[rg]

                
        assert phase in ['response', 'prompt'], "phase={} not one of 'response' or 'prompt'".format(phase)


        start_time = time.time()
        rg_states, rgs_list, timeout, input_rg_states, priority_modules = self.rg_state_setting(phase, exclude_rgs)
        logger.time_track(f'Finished run_rgs_and_rank - {phase} rg_state_setting: {time.time() - start_time}')
        
        start_time = time.time()
        results_dict = self.response_generators.run_multithreaded(rg_names=rgs_list,
                                         function_name=f'get_{phase}',
                                         timeout=timeout,
                                         args_list=[[state] for state in input_rg_states],
                                         priority_modules=priority_modules)

        logger.time_track(f'Finished run_rgs_and_rank - get_{phase}: {time.time() - start_time}')

        # Log the initial results
        logger.taco_merge('RG {} results:\n{}'.format(phase, print_dict_linebyline(results_dict)), extra={'color_lines_by_component': True})
                
        correct_results(phase, results_dict)

        # Put results_dict in current_state
        setattr(self.state_manager.current_state, f'{phase}_results', results_dict)

        for kkk in results_dict:
            logger.taco_merge(f'responser name =  {kkk}')
            logger.taco_merge(f'response =  {results_dict[kkk].text}')

        # Update rg_states with the new RG states given in the ResponseGeneratorResults/PromptResults.
        # Since the response_generator_runner can time out, not all RGs would return results.
        # in which case their internal state would be inconsistent and cannot be used subsequently
        # for example, its internal tracking of the state machine would now be incorrect.
        # It is safest to remove this RG from all subsequent turns
        # Keeping only valid states in rg_states achieves this purpose
        for rg in list(rg_states.keys()):
            if rg in rgs_list:  # If the rg's phase function was run
                if rg in results_dict:
                    if is_killed(results_dict[rg]):
                        logger.primary_info(f'{rg} was killed during get_{phase}, so its state will be retained.')
                    else:
                        rg_states[rg] = results_dict[rg].state

                else:  # If it gave an error or timed out, delete the state as it will be inconsistent
                    logger.warning(f'{rg} had an error or timed out during get_{phase}, so its state is no longer correct. '
                                   'Deleting its state from self.state_manager.current_state.response_generator_states')
                    del rg_states[rg]

        # Sort results using priority ranking strategy

        start_time = time.time()

        if phase == 'response':
            taco_state = getattr(self.state_manager.current_state, 'status', None)
            if 'PAK' in taco_state or 'chat' in taco_state:
                ranked_results = self.prompt_ranking_strategy.rank_responses(results_dict)
            else:
                ranked_results = self.ranking_strategy.rank_advanced(results_dict)
                ranked_results = RankedResults(ranked_results)

            # RankedResults(priority_sorted_responses)
        else:
            # never exeute RankedResults => need prompt false
 

            turns_since_last_active = None
            if hasattr(self.state_manager.current_state, 'turns_since_last_active'):
                turns_since_last_active = self.state_manager.current_state.turns_since_last_active
            ranked_results = self.prompt_ranking_strategy.rank_prompts(results_dict, turns_since_last_active) # type: ignore

        logger.time_track(f'Finished run_rgs_and_rank - {phase} rank results: {time.time() - start_time}')
        # Log the results, sorted by priority
#         logger.primary_info('RG {} results (highest priority first):\n{}'.format(phase, print_dict_linebyline(ranked_results)), extra={'color_lines_by_component': True})

        return ranked_results


    @measure
    def remove_offensive(self, ranked_results: RankedResults) -> RankedResults:
        """
        Check the top-ranked response/prompt in ranked_results for offensiveness. If it's inoffensive, do nothing.
        If it's offensive, remove it from ranked_results, and start again by checking the second-ranked response/prompt.

        Arguments:
            ranked_results: RankedResults (responses or prompts from RGs).

        Returns:
            ranked_results, potentially with some results removed, so that the top result is guaranteed to be
            inoffensive.
        """
        top_result = ranked_results.top_result
        top_rg = ranked_results.top_rg

        # print('top_result = ', top_result)
        # input()
        logger.info(f'Checking top-priority {type(top_result).__name__} from {top_rg} for offensiveness: "{top_result.text}"')
        if contains_offensive(top_result.text):
            logger.error(f'{top_rg} gave an offensive result (i.e. the contains_offensive function returned True). '
                         f'This should be caught inside the RG! Offensive text: "{top_result.text}"')
            ranked_results.remove_result(top_rg)
            return self.remove_offensive(ranked_results)  # start again, checking the new top result
        else:
            return ranked_results
