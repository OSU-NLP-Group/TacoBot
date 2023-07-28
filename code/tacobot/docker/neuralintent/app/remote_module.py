import torch
from torch import nn
import json
import re

from transformers import AutoTokenizer, AutoModel
from transformers.models.roberta.modeling_roberta import RobertaPreTrainedModel, RobertaClassificationHead
from transformers.modeling_outputs import SequenceClassifierOutput

import spacy
nlp = spacy.load('en_core_web_sm')

def norm_utterance(utterance):
    doc = nlp(utterance)
    ban_tokens = {
        'seconds',
        'done'
    }
    return ' '.join([token.text if token.text in ban_tokens else token.lemma_ for token in doc])

noises = ['actually', 'hmm', 'oh', 'uh', 'uhhh', 'well', "please", "alexa", "echo",\
                'a', 'an', 'my', 'your', 'the', 'sorry']
clean_regexes = [
    [re.compile(r"\b("+'|'.join(noises)+r")\b"), ''],
    [re.compile(r'\bd\.*\s*i\.*\s*y\.*'), 'diy'],
    [re.compile(r'\s+'), " "]
]
def clean_utterance(utterance):
    utterance = utterance.lower()
    for regex, to_replace in clean_regexes:
        utterance = regex.sub(to_replace, utterance)
    utterance = norm_utterance(utterance)
    return utterance.strip().strip('?.,')

class Vocab(object):
    def __init__(self, f_name) -> None:
        self.token_to_idx = {
            'NeutralIntent': 0,
            'AcknowledgeIntent': 1,
            'NegativeAcknowledgeIntent': 2,            
        }
        self.idx_to_token = [
            'NeutralIntent',
            'AcknowledgeIntent',
            'NegativeAcknowledgeIntent',
        ]
        
        with open(f_name, 'r') as f:
            for line in f:
                line = line.strip()
                if line not in self.token_to_idx:
                    self.token_to_idx[line] = len(self.token_to_idx)
                    self.idx_to_token.append(line)

    def get_idx(self, token):
        return self.token_to_idx[token]
    def get_token(self, idx):
        return self.idx_to_token[idx]
    def __len__(self):
        return len(self.idx_to_token)

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

class IntentModel(RobertaPreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.num_labels = config.num_labels
        self.config = config

        self.roberta = AutoModel.from_pretrained('princeton-nlp/unsup-simcse-roberta-base')
        self.classifier = ClassificationHead(config, config.num_labels)

        self.loss_fct_0 = torch.nn.BCEWithLogitsLoss(pos_weight=(1)*torch.ones([self.num_labels-3]))
        
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
            loss = self.loss_fct_0(logits[:, 3:], labels[:, 3:].float()) + self.loss_fct_1(logits[:, :3], labels[:, :3].argmax(-1))

        if not return_dict:
            output = (logits) + outputs[2:]
            return ((loss,) + output) if loss is not None else output

        return SequenceClassifierOutput(
            loss=loss,
            logits=logits,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
        )

class Predictor(object):
    def __init__(self, intent_vocab, checkpoint) -> None:
        super().__init__()
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.tokenizer = AutoTokenizer.from_pretrained(checkpoint)
        self.intent_vocab = Vocab(intent_vocab)
        self.model = IntentModel.from_pretrained(checkpoint)
        self.model = self.model.to(self.device)
        self.model.eval()

    def infer(self, utterance):
        with torch.no_grad():
            tokenized_input = self.tokenizer(utterance, return_tensors='pt').to(self.device)
            model_output = self.model(**tokenized_input)
            logits = model_output.logits
            logits[:, 3:] = torch.sigmoid(logits[:,3:])
            logits[:, :3] = torch.softmax(logits[:,:3], -1)
        results = {intent: logits[0,i].item() for i,intent in enumerate(self.intent_vocab.idx_to_token)}
        return results


required_context = ['text']
predictor = Predictor('checkpoint/intents.txt', 'checkpoint')

def get_required_context():
    return required_context

def handle_message(msg):
    if msg['text'][0]:
        input_text = clean_utterance(msg['text'][0])

        preds = predictor.infer(input_text)
        return {'intent_scores': preds}
    else:
        return None
