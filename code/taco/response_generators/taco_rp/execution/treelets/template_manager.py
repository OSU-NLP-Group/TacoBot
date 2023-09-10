DETAIL_TIP_TEMPLATES = {
    'recipe': [
        "I\'d love to tell you more about this step, but whole foods recipes does not contain more details for each step. Please try asking when we are using Wikihow as the source! We can move on if you say next. "
    ],
    'no detail': [
        "This step doesn\'t have more details. We can move on if you say next. "
    ],
    'long detail': [
        "Okay! Feel free to interrupt me since this is long. "
    ],
    'ask more tips': [
        " Do you wanna know the {} {} for this step? "
    ],
    'no more tips': [
        " I can read again if you say repeat. We can also continue the task if you say next. "
    ],
    'next tip': [
        " You can say next to listen to more tips. Or you can say resume to go back to the steps. "
    ]
}

EXEC_TEMPLATES = {
    'method and part markers': {
        'method': [
            "Method {}. "
        ],
        'part': [
            "Part {}. "
        ]

    },
    'step markers': {
        'half': [
            'We\'re halfway there! ',
            'Halfway done! '
        ],
        'three more': [
            'Three more steps left! Next, ',
            'Only three more steps! Next, '
        ],
        'last': [
            'Lastly, ',
            'Finally, ',
        ]
    },
    'last step inst': {
        'ending step': [
            # ' You can still ask me to tell you more details, or say complete to finish this task. '
            ' You can say complete to finish this task. '
            ],
        'last step of part': [' Say next and we can move on to the next part. ']
    },
    'details': [
        " If you want to know more, ask me, tell me the details. ",
        " There are more details for many steps. Try asking me, tell me the details. ",
        " I can give you more details for many steps. Just say, tell me the details. "
    ], 
    'timer': [
        " If you want to time this step, ask me, set timer for {}. ",
        " You can set a timer for this step. Try asking me, set timer for {}. ",
        " I can help you to time this step. Just say, set timer for {}. "
    ],
    'resume': [
        'Welcome back, let\'s continue our task {}! Last time we stopped at step {} of {}. '
    ],
    'warning': [
        ' Before we get started, Please be careful when using any tools or equipment. Remember, safety first! '
    ],
    'navi': [
        ' You may use commands like previous, next, repeat, or, you can ask me related questions. '
    ]
}

EXEC_EXCEPTION_TEMPLATES = {
    'steps left': {
        True: [
            'We are currently at {method_or_part} {method_idx}, step {current_step} of {total_step}. {total_parts} '
        ],
        False: [
            'We are currently at step {current_step} of {total_step}. '
        ]
    },
    'first step': [
        'Whoops! This is the very first step. '
    ],
    'step overflow': {
        True: [
            'Whoops! There {is_or_are} only {steps} steps in {method_or_part} {method_idx}. '
        ],
        False: [
            'Whoops! There {is_or_are} only {steps} steps. '
        ]
    }, 
    'step underflow': [
        "Whoops! We're only at step {step_idx}. "
    ],
    'method overflow': [
        'Whoops! There {is_or_are} only {total} {method_or_part1}. '
    ], 
    'no more step': [
        "Whoops! There are no more steps. You can say previous to go back, or say complete to finish the task. "
    ],
    'switch task': [
        'Whoops! According to the competition rules, we can\'t stop the current task to do another. '
    ]
}

EXE_HINT_TEMPLATES = {
    'next to move on': [
        "You may say next to move on. ",
        "You may say next to continue. "
    ],
    'next to move on or last step': [
        "You may say next or go to the last step to move on. "
    ],
    'next to move on or last method_part': [
        "You may say next or go to the last {method_or_part} to continue. "
    ]
}