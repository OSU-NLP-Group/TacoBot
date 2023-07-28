import torch
import json
import numpy as np
import random

from transformers import RobertaTokenizer, RobertaModel
from torch import nn

TASK_EXAMPLES = [
    'make origami', 'grow tomatoes', 'remove spray paint',
    'fix a leaky faucet', 'wallpaper my room', 'wash paint brushes', 'wash my car'
]
RECIPE_EXAMPLES = [
    'tomato soup', 'chicken curry', 'fish taco', 'banana bread', 'pad thai',
    'smoothie'
]

class BadTaskTemplateManager():
    def __init__(self):
        self.general_prompt = "I am sorry, I can't help with this type of task. "
        self.legal_prompt = "I am sorry, I can't help with legal tasks. "
        self.medical_prompt = "I am sorry, I can't help with medical tasks. "
        self.financial_prompt = "I am sorry, I can't help with financial tasks. "
        self.suicide_prompt = "It might not always feel like it, but there are people who can help. " \
    "Please know that you can call the National Suicide Prevention Lifeline, twenty-four hours a day, seven days a week. Their number is, 1-800-273-8255. Again, that's 1-800-273-8255. "

        self.danger_prompt = 'Such tasks may harm you or your properties. '
        self.goodbye_prompt = [
            "Sorry to say goodbye. ",
            "Sorry but I have to stop here. Have a nice one. ", 
            "I have to exit here. Sorry and goodbye. ", 
            "I need to end this chat. Sorry and goodbye. ", 
            "Sorry to stop here. I hope to help you again soon. "
        ]
        self.expert_prompt = [
            "Because it\'s professional, I will leave it to the experts to help you. ", 
            "I believe an expert in that field would help you better. ", 
            "I don\'t want to misguide you without professional knowledge. ",
            "I think you may need more professional help for this task. ",
            "It would be better for you to get help from experts in the area. "
        ]
        self.unsupported_prompt = [
            "I only know how to help with cooking or DIY tasks. ",
            "This task may not be a cooking or DIY task. ",
            "I\'m not familiar with topics other than cooking or DIY tasks. ",
            "I can deal with cooking or DIY tasks instead. ",
            "I\'m glad to assist you with cooking or DIY tasks instead. "
        ]
        self.privacy_prompt = [
            "This task might harm your privacy. ",
            "I\'d like to protect your privacy. ",
            "Your privacy is my priority. ",
            "It may hurt your privacy. ", 
            "It might expose your private information. "
        ]
        self.follow_up_prompt = "Try asking me something else like how to {} , or , search recipes for {}."

class Filter(nn.Module):
    def __init__(self, phrases):
        super().__init__()
        self.name = "princeton-nlp/unsup-simcse-roberta-base"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.tokenizer = RobertaTokenizer.from_pretrained(self.name)
        self.model = RobertaModel.from_pretrained(self.name)
        self.model = self.model.to(self.device)

        self.phrases = None
        with torch.no_grad():
            self.phrases = [
                self.embed(phrases['good']), 
                self.embed(phrases['bad']),
                self.embed(phrases['financial']),
                self.embed(phrases['legal']),
                self.embed(phrases['medical']),
            ]

    def embed(self, utterance):
        inputs = self.tokenizer(utterance, return_tensors="pt", padding=True).to(self.device)
        embeddings = self.model(**inputs)[0][:, 0, :]
        embeddings = embeddings / torch.norm(embeddings, dim=-1, keepdim=True)
        return embeddings

    def forward(self, utterance):
        embedding = self.embed(utterance)
        scores = []
        for ph in self.phrases:
            scores.append((embedding.matmul(ph.t())).max().item())
        return np.argmax(scores)


required_context = ['text']
phrases = json.load(open('/deploy/app/data/data.json'))
model = Filter(phrases)

def get_required_context():
    return required_context


def handle_message(msg):
    input_text = msg['text'][0]

    if input_text:
        template_manager = BadTaskTemplateManager()
        if ('suicide' in input_text) or ('kill myself' in input_text):
            return {"response": template_manager.suicide_prompt, 'shouldEndSession': True}

        result = model.forward(input_text)
        print('Task filter Result -> %s' % str(result))
        if result == 1:
            return {"response": template_manager.general_prompt, 'shouldEndSession': True}
        elif result == 2:
            template = template_manager.financial_prompt + random.choice(template_manager.expert_prompt) + template_manager.follow_up_prompt
            return template.format(random.choice(TASK_EXAMPLES), random.choice(RECIPE_EXAMPLES))
        elif result == 3:
            template = template_manager.legal_prompt + random.choice(template_manager.expert_prompt) + template_manager.follow_up_prompt
            return template.format(random.choice(TASK_EXAMPLES), random.choice(RECIPE_EXAMPLES))
        elif result == 4:
            template = template_manager.medical_prompt + random.choice(template_manager.expert_prompt) + template_manager.follow_up_prompt
            return template.format(random.choice(TASK_EXAMPLES), random.choice(RECIPE_EXAMPLES))
        else:
            return ''
    else:
        return ""
