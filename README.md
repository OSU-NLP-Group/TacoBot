# TacoBot
This is the codebase for [TacoBot](https://arxiv.org/pdf/2307.16081.pdf). The code structure in this repository is inspired by the implementation of [Chirpy Cardinal](https://arxiv.org/pdf/2207.12021.pdf). We thank the authors for their valuable work.


# Getting Started
- Check the code out, start [here](#how-the-code-is-organized)
- Check the datasets we collected, start [here](#datasets)


# Code Structure

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
 - `dialog_manager.py`: this contains the function `get_response_and_prompt`, which runs all response generators, ranks their responses, and returns the highest ranking response and prompt, and the function `execute_turn` which loads the rg states from the previous turn, updates the state based on the response and prompt chosen by `get_response_and_prompt` and then returns the bot’s next utterance
 - `handler.py` deserializes the state, runs the NLP pipeline, updates the state based on it, calls dialog manager’s `execute_turn`, and then serializes the state
 - `taco_ranking_strategy.py` Logic for ranking responses and prompts
- `state.py`: The State class defines what should be stored in each state and contains functions for serializing/deserializing the state.
- `user_attributes.py`: The UserAttributes class defines which user attributes should be recorded and contains functions for serializing/deserializing user attributes.

`taco/response_generators`: Contains all response generators used by the bot. More detail can be found in the Creating a Response Generator<link> section

## Creating an Agent
Agents manage the bot’s data storage, logging, message input/output, and connections to remote modules. The agent class provided, `local_agent.py` stores data locally and inputs/outputs messages as text. By defining your own agent, you can alter any of these components, for example storing data in a Redis instance, or inputting messages as audio. 

Highlighted features of the `LocalAgent` are:
`init` function, which initializes
- `last_state` and `current_state` dicts
These are serialized/deserialized by the functions in `taco/core/state.py.` If you change their attributes in your agent, then you should also update `state.py`
- `user_attributes` dict, which contains
  - `user_id`: unique identifier for the user
  - `session_id`: unique identifier for the current session
  - `user_timezone`: the user’s timezone (if available) which is used by response generators to create time-specific responses, e.g. “good morning!”

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
1. Create a folder which contains `new_response_generator.py` in `taco/response_generators` which defines a NewResponseGenerator class
2. Set the class’s name attribute to be 'NEW_NAME’

### Adding a Response Generator to the Handler
In order for your response generator to be called, it needs to be added to a) your handler and b) the response priority list. To do this,
1. Add MyNewResponseGenerator to your handler’s list `response_generator_classes` in your agent. If you’re using the local agent, you would add this to `local_agent.py`
2. Using the name you declared in your response generator class, set the following in `response_priority.py`:


# Datasets

`datasets`: In this folder, we open-source the datasets we collected during the process of tacobot development, which covers multiple components, including natural language understanding, question answering, etc. 

## Domain Classifier

Inside the folder `datasets/domain-classifier`, you will find the dataset for domain classifier. Each line in the data file represents a unique record and is structured as:

```json
{
    "utterance": "how do i paint a wall",
    "domain": "diy"
}
```

Key Descriptions:

- utterance: Represents the text of the user utterance.
- domain: The domain tag for the given utterance, either 'cooking' or 'diy'.


## Intent Classifier

Inside the folder `datasets/intent-classifier`, you will find the dataset for intent classifier. Each line in the data file is structured as:

```json
{
    "utterance": "do you like a movie",
    "intents": ["QuestionIntent"]
}
```

Key Descriptions:

- utterance: Represents the text of the user utterance.
- intents: A list containing the intent labels corresponding to the given utterance.


## Question Type Classifier

Inside the folder `datasets/question-classifier`, you will find the dataset for question type classifier. Each line in the data file is structured as:

```json
{
    "sentence": "which ingredient can i use as an alternative for bread",
    "label": "SubstituteQuestion"
}
```

Key Descriptions:

- sentence: Represents the user's question text, including any accompanying context.
- label: The tag of the question type.

## Machine Reading Comprehension (MRC)

Inside the folder `datasets/mrc`, you will find the dataset for MRC QA. Each line in the data file is structured as:

```json
{
    "url": "https://www.wikihow.com/Make-a-Water-Filter",
    "title": "How to Make a Water Filter",
    "step_count": 4,
    "step_context": "Put the coffee filter over the mouth of the bottle and tighten the cap over it ...",
    "question": "How to keep the bottle steady?",
    "answer": "Put the bottle cap-side-down into a mug or cup. This will help keep the bottle steady while you fill it."
}
```

Key Descriptions:

- url: The url of the WikiHow article.
- title: The title of the corresponding WikiHow task.
- step_count: The index of the step number in the task.
- step_context: The step content in the task as the context.
- question: Represents the user's question text.
- answer: The answer of the question.


## Citation
```
@article{mo2023roll,
  title={Roll Up Your Sleeves: Working with a Collaborative and Engaging Task-Oriented Dialogue System},
  author={Mo, Lingbo and Chen, Shijie and Chen, Ziru and Deng, Xiang and Lewis, Ashley and Singh, Sunit and Stevens, Samuel and Tai, Chang-You and Wang, Zhen and Yue, Xiang and others},
  journal={arXiv preprint arXiv:2307.16081},
  year={2023}
}
```
