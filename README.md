# TacoBot
Codebase for [TacoBot](https://sunlab-osu.github.io/tacobot/)

# Getting Started
- Check the code out, start [here](#how-the-code-is-organized)
- Check the datasets we collected, start [here](#datasets)


# How the code is organized
Under the `./code` folder:

`agent`: When you run tacobot, you will create an agent. Agents manage data storage, logging, user message input, bot message output, connections to remote modules, and calls to the handler. The agent is provided:
- `local_agent.py`: an agent that stores data and runs remote modules locally. 

`servers`: Contains the code needed to run tacobot servers
 - `servers/local/shell_chat.py`: script to build docker modules locally and run chat in a loop.
 - `servers/local/local_callable_manager.py` defines the LocalCallableManager class, which is used to run docker containers locally
 - `servers/local/local_callable_config.json` defines the ports, dockerfiles, and urls associated with each container

`taco`: This directory contains the bot’s response generators, remote modules, and dialog management. The core logic of the bot is here. Code in this directory is invariant of agent specifications.

`taco/annotators` When a user utterance is input, all annotators are run on it and their results are stored in state, so that they can be used by the response generators. Annotations include dialog act and user emotion, among others.

`taco/core` The bot’s core logic components. Highlighted files are:
 - `taco_dialog_manager.py`: this contains the function `get_response_and_prompt`, which runs all response generators, ranks their responses, and returns the highest ranking response and prompt, and the function `execute_turn` which loads the rg states from the previous turn, updates the state based on the response and prompt chosen by `get_response_and_prompt` and then returns the bot’s next utterance
 - `taco_handler.py` deserializes the state, runs the NLP pipeline, updates the state based on it, calls dialog manager’s `execute_turn`, and then serializes the state
 - `taco_ranking_strategy.py` Logic for ranking responses and prompts
- `taco_state.py`: The State class defines what should be stored in each state and contains functions for serializing/deserializing the state.
- `taco_user_attributes.py`: The UserAttributes class defines which user attributes should be recorded and contains functions for serializing/deserializing user attributes.
- `regex`: the regex directory contains code for creating and testing regular expressions that can be used by the bot. New regexes should be added to `templates.py`

`taco/response_generators`: Contains all response generators used by the bot. More detail can be found in the Creating a Response Generator<link> section

`docker`: This is where the dockerfiles, configs, and lambda functions of each remote module are defined.

`scrapers`: Scrape data from Twitter and Reddit, so that it can be stored in elastic-search

`wiki-es-dump`: Processes and stores raw wiki files for use by the response generators. `wiki-setup.md` contains detailed instructions for this step.

## Creating an Agent
Agents manage the bot’s data storage, logging, message input/output, and connections to remote modules. The agent class provided, `local_agent.py` stores data locally and inputs/outputs messages as text. By defining your own agent, you can alter any of these components, for example storing data in a Redis instance, or inputting messages as audio. 

Highlighted features of the `LocalAgent` are:
`init` function, which initializes
- `last_state` and `current_state` dicts
These are serialized/deserialized by the functions in `taco/core/taco_state.py.` If you change their attributes in your agent, then you should also update `taco_state.py`
- `user_attributes` dict, which contains
  - `user_id`: unique identifier for the user
  - `session_id`: unique identifier for the current session
  - `user_timezone`: the user’s timezone (if available) which is used by response generators to create time-specific responses, e.g. “good morning!”
  - `turn_num`: the number of the current turn
`persist` function
- Manages storage of the `state` and `user_attributes`. If you want to store things non-locally, you would make this change here
`should_launch` function
- Determine whether to launch the bot, for example based on specific commands
`should_end_session` function
- Determine whether to end the conversation, which may also be based on specific commands or heuristics
`process_utterance` function
- Retrieve the current state, previous state, and user attributes from your storage 
- Call handler.execute() on the current state, previous state, and user attributes, which returns updated states and a response
- Persist the updated states in your storage
- Return the response and current state

## Creating a new Response Generator
To create a new response generator, you will need to 
1. Define a new class for your response generator
2. Add your response generator to the handler

### Defining a Response Generator class
You will need to create a new class for your response generator. To do this, 
1. Create a file `new_response_generator.py` in `taco/response_generators` which defines a NewResponseGenerator class
2. Set the class’s name attribute to be 'NEW_NAME’
3. Define the following functions of your class:
  - init_state (returns a State object) which contains the state for your response generator which stores information about the response generator
  - get_entity (returns an UpdateEntity object). This is used to override the entity linker, in cases where the response generator has a better contextual understanding of what the new entity should be.
  - get_response (returns a ResponseGeneratorResult) based on the user’s utterance, annotations, and the response generator’s state. If the response generator doesn’t have any suitable responses, this returns an emptyResult object
  - get_prompt (returns a PromptResult) based on the user’s utterance, annotations, and the response generator’s state. If the response generator doesn’t have any suitable prompts, this returns an emptyPrompt object
  - update_state_if_chosen: updates the response generator’s conditional state if the response generator is chosen. For example, this might mean adding its response to a list of questions asked
  - update_state_if_not_chosen: updates the response generator’s conditional state if the response generator was not chosen. For example, by setting the current topic to be None.

### Adding a Response Generator to the Handler
In order for your response generator to be called, it needs to be added to a) your handler and b) the response priority list. To do this,
1. Add MyNewResponseGenerator to your handler’s list `response_generator_classes` in your agent. If you’re using the local agent, you would add this to `local_agent.py`
2. Using the name you declared in your response generator class, set the following in `response_priority.py`:


# Datasets

`datasets`: In this folder, we open-source the datasets we collected during the process of tacobot development, which covers multiple components, including natural language understanding, search engine, question answering, people-also-ask, etc. More details to come soon.