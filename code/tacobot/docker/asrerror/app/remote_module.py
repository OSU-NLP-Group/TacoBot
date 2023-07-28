from transformers import AutoTokenizer, BertForSequenceClassification
import torch
import torch.utils.checkpoint
import re


def clean_utterance(utterance):
    utterance = utterance.lower()
    for noise in ['actually', 'hmm', 'oh', 'uh', 'uhhh', 'well', "please", "alexa", "echo"]:
        utterance = utterance.replace(noise, " ")
    utterance = re.sub(r'\s+', " ",utterance)
    return utterance.strip().strip('?.,')


class Predictor(object):
    def __init__(self, checkpoint) -> None:
        super().__init__()
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.tokenizer = AutoTokenizer.from_pretrained(checkpoint)
        self.model = BertForSequenceClassification.from_pretrained(checkpoint)
        self.model = self.model.to(self.device)
        self.model.eval()

    def infer(self, utterance):
        with torch.no_grad():
            tokenized_input = self.tokenizer(utterance, return_tensors='pt').to(self.device)
            model_output = self.model(**tokenized_input)
            logits = torch.softmax(model_output.logits,dim=1)[0,1].item()

            threshold1 = 0.65
            threshold2 = 0.45

            if logits >= threshold1:
                confidence = 'High'
            elif logits<=threshold2:
                confidence = 'Low'
            else:
                confidence = 'Medium'

        return confidence

required_context = ['text']
predictor = Predictor("/deploy/app/checkpoint/asr_error_classifier_single_task")


def get_required_context():
    return required_context

def handle_message(msg):
    input_text = clean_utterance(msg['text'][0])

    confidence = predictor.infer(input_text)

    # 'asr_prediction': "1" represents "correct" while "0" means "asr_error"
    return {'confidence': confidence}