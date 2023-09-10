from taco.response_generators.taco_rp.templates import Template



START_QUESTION = [
    'Are you ready to start now? ',
    'Can we start now? ',
    'Shall we start now? ',
    '<amazon:domain name="music"> Should we, as the kids say, rock-and-roll? </amazon:domain> ',
    'Ready to dive in? ',
    'Okay, ready to roll up your sleeves? ',
    'Ready to boogie, as the kids say? ',
]

WIKIHOW_PREP_TEMPLATES = {
    'resume_task': [
        'Welcome back! Let\'s continue the task we started. '
    ],
    'rating': {
        'default': [
            "Let\'s work on {}. "
        ],
        'has_rating': [
            "This article, {} has {} stars. "
        ]
    },
    'views': {
        'million': [
            'It has millions of views on wikihow! '
        ],
        'many_thousands': [
            'It is one of the most popular wikihow articles! '
        ],
        'few_thousands': [
            'It has thousands of views on wikihow! '
        ],
        'not_many': [
            'It is one of the newest wikihow articles! '
        ]
    },
    'methods':[
        'You can choose a method, or we can start with the first one. '    
    ]
}

RECIPE_PREP_TEMPLATES = {
    'resume_task': [
        'Welcome back! Let\'s continue the recipe we started. '
    ],
    'ingredient': {
        True: [
            Template("Here are the ${num} ingredients for ${title} on your screen. "),
            Template("I listed the ${num} ingredients for ${title} on your screen. "),
            Template("The ${num} ingredients for ${title} are on your screen. "),
        ],
        False: [
            Template("${title} has ${num} ingredients. "),
            Template("There are ${num} ingredients in ${title}. "),
        ]
    },
    'info': {
        'one_slot': 'It needs {}. ',
        'two_slots': 'It has {} and needs {}. ',
    },
    'read': [
        'You can ask me to read the ingredients. ',
        'I can read the ingredients if you want. ',
    ],
    'add': [
        'You can ask me to add the ingredients to your grocery list. ',
        'I can add the ingredients to your grocery list. ',
    ], 
    'start': [
        Template("Ready to embark upon this culinary adventure? "),
        Template("${start_question} "),
    ]
}
