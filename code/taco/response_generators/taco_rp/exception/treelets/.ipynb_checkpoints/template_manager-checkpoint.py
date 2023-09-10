import json
import random

from taco.response_generators.taco_rp.templates import Template
from taco.response_generators.taco_rp import vocab
from taco.response_generators.taco_rp import examples


BAD_TASK_TEMPLATES = {
    'reject': {
        'general': "I am sorry, I can't help with this type of task. ",
        'legal': "I am sorry, I can't help with legal tasks. ", 
        'medical': "I am sorry, I can't help with medical tasks. ",
        'financial': "I am sorry, I can't help with financial tasks. ",
        'suicide': (
            "It might not always feel like it, but there are people who can help. " +
            "Please know that you can call the National Suicide Prevention Lifeline, twenty-four hours a day, seven days a week. Their number is, 1-800-273-8255. Again, that's 1-800-273-8255. "
        )
    }, 
    'reason': {
        'professional': [
            "Because it\'s professional, I will leave it to the experts to help you. ", 
            "I believe an expert in that field would help you better. ", 
            "I don\'t want to misguide you without professional knowledge. ",
            "I think you may need more professional help for this task. ",
            "It would be better for you to get help from experts in the area. "
        ],
        'unsupported': [
            "I only know how to help with cooking or DIY tasks. ",
            "This task may not be a cooking or DIY task. ",
            "I\'m not familiar with topics other than cooking or DIY tasks. ",
            "I can deal with cooking or DIY tasks instead. ",
            "I\'m glad to assist you with cooking or DIY tasks instead. "
        ],
        'privacy': [
            "This task might harm your privacy. ",
            "I\'d like to protect your privacy. ",
            "Your privacy is my priority. ",
            "It may hurt your privacy. ", 
            "It might expose your private information. "
        ]
    }, 
    'follow up': {
        'suggest tasks': [
            "Try asking me something else like how to {}, or, search recipes for {}."
        ]
    }
}


ERROR_TEMPLATES = {
    'back channel': [
        Template("I heard, ${text}. I’ll learn to respond better after this chat! "),
        Template("You said, ${text}. I’ll learn to understand you better after this chat! "),
        Template("${sad_exclamation}, sorry. I don’t think I understood what you said. You can try again! "),
        Template("These robot ears just aren’t what they used to be. I don’t think I caught what you said. "),
        Template("${sad_exclamation}. I didn’t catch that. "),
        Template("${sad_exclamation}. I couldn’t figure out what you said. "),
    ],
    'multi cancel': [
        "I think you said cancel multiple times. If you want to quit, say stop. "
    ],
    'nothing': [
        "I didn't hear anything. "
    ],
    'alexa command': [
        "I heard {}, but I can\'t help because I\'m an Alexa Prize skill for DIY and cooking tasks. "
    ],
    'permission': [
        "I need your permission to do this. " + 
        "After this chat, you may turn it on in your Alexa app, settings, Alexa privacy, manage skill permissions. "
    ],
    'suggest help': [
        "Come closer and rephrase. If you don't know what to say, you can ask me, help. "
    ]
}


HELP_TEMPLATES = {
    "welcome": [
        Template("You may try asking how to ${task} or search recipes for ${recipe} You may also ask me for my favorite tasks or my favorite recipes. "),
        Template("My passion is helping humans with cooking and do-it-yourself tasks around the house. What can I help you with friend? For example, you can ask me for a recipe for ${recipe} or how to ${task}, or I can tell you my favorites. "),
    ], 
    "prep_wikihow": [
        "We\'re about to start the task {}. Say yes and we\'ll start the task. You may also say cancel to propose a new task, or say stop to come back later. "
    ],
    "prep_recipe": [
        "We\'re preparing for the {} recipe. If you're ready, say start cooking. Or you can say stop and come back later. You may also say cancel and work on something else."
    ],
    "Task_Execution": [
        "We\'re working on the task {}. You may use next and previous to navigate. Or you may say, go to step three, to jump between steps. You can also ask me related questions."
    ], 
    "Task_Details": [
        "We were discussing the details for this step. Say resume, and let\'s return to the task. " 
    ],
    "choice": {
        "no_result": {
            True: [
                "I couldn't find any results in WikiHow for your previous search. Please try asking how to do a different task, such as {}. "
            ],
            False: [
                "I couldn't find any results in Whole Foods for your previous search. Please try searching recipes for a different dish name, such as {}. "
            ]
        },
        "1_result": [
            "The current option is {}. Please say, the first one, if you want to try this. " 
        ],
        "2_results": [
            "The current two options are {} and {}. Do you want the first one or the second one? "
        ],
        "3_results": [
            "The current three options are {}, {}, and {}. Do you want the first, second, or third option? "
        ],
        "compare_cancel": [
            'I can compare the search results for you. Or you can say, cancel, to return and start a new task. '
        ]
    }
}


def select_bad_task_template(type):
    template = ''

    if type == 0: #suicide
        return BAD_TASK_TEMPLATES['reject']['suicide']
    elif type == 1: #danger
        return BAD_TASK_TEMPLATES['reject']['general']
    elif type == 2: #legal
        template = (
            BAD_TASK_TEMPLATES['reject']['legal'] + 
            random.choice(BAD_TASK_TEMPLATES['reason']['professional']) +
            random.choice(BAD_TASK_TEMPLATES['follow up']['suggest tasks'])
        )
    elif type == 3: #financial
        template = (
            BAD_TASK_TEMPLATES['reject']['financial'] + 
            random.choice(BAD_TASK_TEMPLATES['reason']['professional']) +
            random.choice(BAD_TASK_TEMPLATES['follow up']['suggest tasks'])
        )
    elif type == 4: #medical
        template = (
            BAD_TASK_TEMPLATES['reject']['medical'] + 
            random.choice(BAD_TASK_TEMPLATES['reason']['professional']) +
            random.choice(BAD_TASK_TEMPLATES['follow up']['suggest tasks'])
        )
    elif type == 5: #unsupported
        template = (
            BAD_TASK_TEMPLATES['reject']['general'] + 
            random.choice(BAD_TASK_TEMPLATES['reason']['unsupported']) +
            random.choice(BAD_TASK_TEMPLATES['follow up']['suggest tasks'])
        )
    elif type == 6: #privacy
        template = (
            BAD_TASK_TEMPLATES['reject']['general'] + 
            random.choice(BAD_TASK_TEMPLATES['reason']['privacy']) +
            random.choice(BAD_TASK_TEMPLATES['follow up']['suggest tasks'])
        )

    if template == '':
        return ''
    else:
        return template.format(examples.random_task(), examples.random_recipe())


def select_error_template(text, intent, last_intent, need_permission=False):
    template = ''
    if intent == 'CancelIntent' and last_intent == 'CancelIntent':
        template = random.choice(ERROR_TEMPLATES['multi cancel'])
    elif text == '':
        template = random.choice(ERROR_TEMPLATES['nothing'])
    elif intent == 'AlexaCommandIntent':
        template = random.choice(ERROR_TEMPLATES['alexa command']).format(text)
    elif need_permission:
        template = random.choice(ERROR_TEMPLATES['permission'])
    else:
        template = random.choice(ERROR_TEMPLATES['back channel']).substitute(text=text, sad_exclamation=random.choice(vocab.SAD_EXCLAMATIONS))

    template += random.choice(ERROR_TEMPLATES['suggest help'])
    return template


def select_help_template(taco_state, user_attributes):
    is_wikihow = getattr(user_attributes, 'is_wikihow', None)
    current_task = getattr(user_attributes, 'current_task', None)
    if 'TaskPreparation' in taco_state:
        list_item_selected = getattr(user_attributes, "list_item_selected", -1)
        if list_item_selected >= 0:
            if is_wikihow:
                current_task = user_attributes.query_result[list_item_selected]["_source"]["articleTitle"]
            else:
                current_task = json.loads(user_attributes.query_result['documents'][list_item_selected])["recipe"]["displayName"]

    response = ''
    
    if taco_state == 'Welcome' or True:
#         "20220928" modify
        response += random.choice(HELP_TEMPLATES['welcome']).substitute(task=examples.random_task(), recipe=examples.random_recipe())
    elif 'TaskChoice' in taco_state:
        response += get_choices(user_attributes)
    elif 'TaskPreparation' in taco_state:
        if is_wikihow:
            response += random.choice(HELP_TEMPLATES['prep_wikihow']).format(current_task)
        else:
            response += random.choice(HELP_TEMPLATES['prep_recipe']).format(current_task)
    elif 'Instruction' in taco_state:
        response += random.choice(HELP_TEMPLATES['Task_Execution']).format(current_task)
    elif 'Detail' in taco_state:
        response += random.choice(HELP_TEMPLATES['Task_Details'])
 
    return response


def get_choices(user_attributes):
    is_wikihow = getattr(user_attributes, 'is_wikihow', False)
    proposed_tasks = getattr(user_attributes, 'proposed_tasks', [])
    num_results = len(proposed_tasks)

    speak_output = ''
    speak_output = select_template(num_results, proposed_tasks, is_wikihow)
    return speak_output


def select_template(num_results, proposed_tasks, is_wikihow):
    speak_output = ''

    if num_results == 0:
        if is_wikihow:
            speak_output = random.choice(HELP_TEMPLATES['choice']['no_result'][is_wikihow]).format(examples.random_task())
        else:
            speak_output = random.choice(HELP_TEMPLATES['choice']['no_result'][is_wikihow]).format(examples.random_recipe())
    elif num_results == 1:
        speak_output = random.choice(HELP_TEMPLATES['choice']['1_result']).format(proposed_tasks[0]['title'])
    elif num_results == 2:
        speak_output = random.choice(HELP_TEMPLATES['choice']['2_results']).format(proposed_tasks[0]['title'], proposed_tasks[1]['title'])
    elif num_results == 3:
        speak_output = random.choice(HELP_TEMPLATES['choice']['3_results']).format(proposed_tasks[0]['title'], proposed_tasks[1]['title'], proposed_tasks[2]['title'])

    if num_results > 0:
        speak_output += random.choice(HELP_TEMPLATES['choice']['compare_cancel'])
                        
    return speak_output
