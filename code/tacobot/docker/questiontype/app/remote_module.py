from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoConfig
import torch
import re

required_context = ['text']
def get_required_context():
    return required_context


def clean_utterance(utterance):
    utterance = utterance.lower()
    for noise in ['actually', 'hmm', 'oh', 'uh', 'uhhh', 'well', "please", "alexa", "echo", "?"]:
        utterance = utterance.replace(noise, "")
    utterance = re.sub(r'\s+', " ", utterance)
    return utterance


class QuestionClassificationModel(object):
    def __init__(self, checkpoint):
        super().__init__()
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.tokenizer = AutoTokenizer.from_pretrained(checkpoint, config=AutoConfig.from_pretrained(checkpoint))
        self.model = AutoModelForSequenceClassification.from_pretrained(checkpoint, config=AutoConfig.from_pretrained(checkpoint)).to(self.device)
        self.model.eval()
        self.label_list = sorted(['EVI', 'FAQ', 'MRC', 'SubstituteQuestion', 'IngredientQuestion'])

    def infer(self, question, context, top_k=2):
        example = clean_utterance(question).lower() + "\n" + context.lower()
        with torch.no_grad():
            tokenized_input = self.tokenizer(example, max_length=256, truncation=True, return_tensors='pt').to(self.device)
            model_output = self.model(**tokenized_input)
            logits = model_output.logits.softmax(dim=1)
            indices = logits.argsort(descending=True)[0][:top_k].tolist()
            return [(self.label_list[k],logits[0][k].item()) for k in indices]


model_name = "/deploy/app/checkpoint/question_classifier"
question_classifier = QuestionClassificationModel(model_name)


def handle_message(msg):
    # your remote module should operate on the text or other context information here
    # most recent user utterance
    question = msg['text'][0]
    # current step's details
    context = msg.get('current_step_details', [])
    if context and len(context) > 0:
        results = question_classifier.infer(question, context[-1])
    else:
        results = question_classifier.infer(question, '')

    question_types = [r[0] for r in results]

    # confidence_threshold = 0.8
    # confidences = ["HIGH_CONFIDENCE" if r[1] > confidence_threshold else "LOW_CONFIDENCE" for r in results]

    return {'question_types': question_types}