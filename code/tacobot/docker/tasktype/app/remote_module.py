"""
This module uses spacy along with an ignore list to extract the relevant noun phrases from the current user utterance
and bot response from the previous turn.
"""
import spacy
import re
from opensearchpy import OpenSearch

from transformers import AutoTokenizer, AutoModelForQuestionAnswering
from transformers import AutoModel, AutoConfig
from transformers.models.roberta.modeling_roberta import RobertaPreTrainedModel
from transformers.modeling_outputs import SequenceClassifierOutput
import torch
import os
import json
import numpy as np
from torch import nn
import torch.nn.functional as F
import pickle
import re
import pdb


access_token = "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"

required_context = ['text']
nlp = spacy.load('en_core_web_sm')
stopwords = nlp.Defaults.stop_words
stopwords |= {'one', 'two', 'three', 'first', 'second', 'third'}
stopwords |= {'suggest', 'suggestions', 'suggestion', 'recommendation', 'recommendations', 'recommend', 'search' ,'like', 'want', \
        'a', 'about', 'let', 'need', 'prefer', 'try', 'an',\
        'tips', 'tip', 'prepare','recipes', 'recipe', 'task', 'tasks', 'ingredients', 'ingredient', 'cook', 'cooking', 'make', 'instruction', 'instructions', \
        'something', 'anything', 'else', 'different', 'other', 'another'}

recipe_keywords = {'recipe', 'recipes', 'cook', 'cooking'}

ambiguous_terms = [
    ['diy', r'\b((?<!hot)(?<!hot ))dog(s)?\b'], # dog but not hotdog
    ['diy', r'\bbean\s*bag(s)?\b'],
    ['diy', r'\bbubble(s)?(?! tea|tea)\b'],
    ['diy', r'\b(?<!pot)(?<!pot )sticker(s)?\b'],
    ['diy', r'\bcooler(s)?\b'],
    ['diy', r'\b(make.*bed(s)?|bed(s)? making|bed(s)? make)\b'],
    ['diy', r'\b(remove oil(s)?|oil(s)? removing|oil(s)? remove)\b'],
    ['cooking', r'\bangel hair(s)?\b'],
    ['cooking', r'\bbagel(s)?\b'],
    ['cooking', r'\bcutlet(s)?\b'],
    ['cooking', r'\b(?<!breed )(?<!catch )shrimp(s)?\b'],
]
ambiguous_terms = [[type, re.compile(pattern)] for type,pattern in ambiguous_terms]


def clean_utterance(utterance, for_cls=False):
    utterance = utterance.lower()
    for noise in ['actually', 'hmm', 'oh', 'uh', 'uhhh', 'well', "please", "alexa", "echo"]:
#         utterance = utterance.replace(noise, " ")
        utterance = re.sub(r"\b"+noise+r"\b", '', utterance)
    utterance = re.sub(r'\bd\.*\s*i\.*\s*y\.*', 'diy', utterance)
    if for_cls:
        for noise in ['a', 'an', 'my', 'your', 'the']:
    #         utterance = utterance.replace(noise, " ")
            utterance = re.sub(r"\b"+noise+r"\b", '', utterance)
    utterance = re.sub(r'\s+', " ",utterance)
    return utterance.strip().strip('?.,')

class ClassificationHead(nn.Module):
    """Head for sentence-level classification tasks."""

    def __init__(self, config, num_labels):
        super().__init__()
        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        classifier_dropout = (
            config.hidden_dropout_prob
        )
        self.dropout = nn.Dropout(classifier_dropout)
        self.out_proj = nn.Linear(config.hidden_size, num_labels)

    def forward(self, features, **kwargs):
        x = features[:, 0, :]  # take <s> token (equiv. to [CLS])
        x = self.dropout(x)
        x = self.dense(x)
        x = torch.tanh(x)
        x = self.dropout(x)
        x = self.out_proj(x)
        return x

class TypeModel(RobertaPreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.num_labels = config.num_labels
        self.config = AutoConfig.from_pretrained('princeton-nlp/unsup-simcse-roberta-base', use_auth_token=access_token)

        self.roberta = AutoModel.from_config(self.config)
        self.classifier = ClassificationHead(config, config.num_labels)

        self.loss_fct_0 = torch.nn.BCEWithLogitsLoss()
        
        self.loss_fct_1 = torch.nn.CrossEntropyLoss()

        self.init_weights()
    def forward(
        self,
        input_ids=None,
        attention_mask=None,
        token_type_ids=None,
        position_ids=None,
        head_mask=None,
        inputs_embeds=None,
        labels=None,
        output_attentions=None,
        output_hidden_states=None,
        return_dict=None,
    ):
        r"""
        labels (:obj:`torch.LongTensor` of shape :obj:`(batch_size,)`, `optional`):
            Labels for computing the sequence classification/regression loss. Indices should be in :obj:`[0, ...,
            config.num_labels - 1]`. If :obj:`config.num_labels == 1` a regression loss is computed (Mean-Square loss),
            If :obj:`config.num_labels > 1` a classification loss is computed (Cross-Entropy).
        """
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        outputs = self.roberta(
            input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            head_mask=head_mask,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )
        sequence_output = outputs[0]
        logits = self.classifier(sequence_output)

        loss = None
        if labels is not None:
            loss = self.loss_fct_0(logits[:, 2], labels[:, 1].float())
            loss += self.loss_fct_1(logits[:, :2], labels[:, 0])

        if not return_dict:
            output = (logits) + outputs[2:]
            return ((loss,) + output) if loss is not None else output

        return SequenceClassifierOutput(
            loss=loss,
            logits=logits,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
        )
    
class TypePredictor(object):
    def __init__(self, checkpoint) -> None:
        super().__init__()
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.tokenizer = AutoTokenizer.from_pretrained(checkpoint, config=AutoConfig.from_pretrained(checkpoint))
        self.model = TypeModel.from_pretrained(checkpoint, config=AutoConfig.from_pretrained(checkpoint))
        self.model = self.model.to(self.device)
        self.model.eval()

    def infer(self, utterance):
        with torch.no_grad():
            tokenized_input = self.tokenizer(clean_utterance(utterance), return_tensors='pt').to(self.device)
            model_output = self.model(**tokenized_input)
            logits = model_output.logits
            logits[:, 2] = torch.sigmoid(logits[:,2])
            logits[:, :2] = torch.softmax(logits[:,:2], -1)
        results = {'cooking': logits[0,0].item(), 'diy': logits[0,1].item(), 'empty': logits[0,2].item()}
        return results

def get_required_context():
    return required_context

def handle_message(msg):
    # checks if any noun phrases are in the ignore list

    # most recent user utterance
    input_text = clean_utterance(msg['text'][0])
    input_doc = nlp(input_text)
    if len(input_text)==0:
        return {'tasktype': None, 'tasktype_pred': {}, 'taskname': '', 'task_selection': [-1, 0.0]}
    try:
        tasktype_pred = tasktype_classification(input_doc)
        
        # if tasktype_pred[0]=='cooking':
        #     taskname = taskname_extraction(input_text, input_doc, 'recipe')
        # else:
        #     taskname = taskname_extraction(input_text, input_doc, 'diy')
    except:
        tasktype_pred = ('diy', {})
        # taskname = taskname_extraction(input_text, input_doc, 'diy')

    # if msg.get('selected_task', None) is None and msg.get('proposed_tasks', None) is not None and msg.get('proposed_tasks', None):
    #     try:
    #         if len(msg['proposed_tasks'])>0:
    #             selection = task_selection(input_doc, [re.sub(r'\bhow to\b','',task['title'].lower().strip('?.')) for task in msg['proposed_tasks']])
    #         else:
    #             selection = [-1, 0.0]
    #     except:
    #         selection = [-1, 0.0]
    # else:
    #     selection = [-1, 0.0]
    return {'tasktype': tasktype_pred[0], 'tasktype_pred': tasktype_pred}
    # return {'tasktype': tasktype_pred[0], 'tasktype_pred': tasktype_pred, 'taskname': taskname, 'task_selection': selection}

print("loading CLS model")

# cls_predictor = TypePredictor('/data/deng.595/workspace/cobot_interaction_model/cls_results/trained_model')
# with open('/data/deng.595/workspace/cobot_interaction_model/data/recipe1M/cleaned_cooking_verbs.json', 'r') as f:
#     cooking_verbs = set(json.load(f))
# with open('/data/deng.595/workspace/cobot_interaction_model/data/recipe1M/cleaned_cooking_nouns.json', 'r') as f:
#     cooking_nouns = {i:set(nouns) for i,nouns in json.load(f).items()}
cls_predictor = TypePredictor("/deploy/app/checkpoint/classifier_checkpoint/")
with open('/deploy/app/data/cleaned_cooking_verbs.json', 'r') as f:
    cooking_verbs = set(json.load(f))
with open('/deploy/app/data/cleaned_cooking_nouns.json', 'r') as f:
    cooking_nouns = {i:set(nouns) for i,nouns in json.load(f).items()}
    
print("CLS model loaded")

    
def tasktype_classification(utterance_doc):
    def match_cooking_with_vocab(doc):
        idx = 0
        tokens = [token.lemma_ for token in doc]
        match_food = False
        while idx<len(doc):
            matched = False
            for n_i in [5,4,3,2,1]:
                phrase = ' '.join(tokens[idx:idx+n_i])
                if phrase in cooking_nouns[str(n_i)]:
                    matched = True
                    match_food = True
                    idx += n_i
                    break
                elif n_i == 1:
                    if doc[idx].pos_=='VERB':
                        if tokens[idx] in cooking_verbs:
                            matched = True
                            idx += n_i
                            break
                    elif doc[idx].pos_!='NOUN':
                        if tokens[idx] in stopwords:
                            matched = True
                            idx += n_i
                            break
            if not matched:
                return False
        if match_food:
            return True
        else:
            return False
    utterance = clean_utterance(' '.join([token.lemma_ for token in utterance_doc]), for_cls=True)
    pred = cls_predictor.infer(utterance)
    if pred['diy']>pred['cooking'] and pred['diy']<0.8 and match_cooking_with_vocab(utterance_doc):
        pred['diy']=0.0
        pred['cooking']=1.0
    for type, pattern in ambiguous_terms:
        if pattern.search(utterance) is not None:
            if type == 'diy':
                pred['diy']=1.0
                pred['cooking']=0.0
            else:
                pred['diy']=0.0
                pred['cooking']=1.0
    if pred['diy']>pred['cooking']:
        return ('diy', pred)
    else:
        return ('cooking', pred)




