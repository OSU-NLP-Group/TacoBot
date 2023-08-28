# TacoBot
Codebase for [TacoBot](https://sunlab-osu.github.io/tacobot/) (Coming soon)


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