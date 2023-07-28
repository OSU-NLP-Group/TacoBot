from transformers import AutoTokenizer, AutoModelForQuestionAnswering
import torch
import spacy
import re
import collections
from typing import Tuple
import numpy as np

required_context = ['text']
def get_required_context():
    return required_context


nlp = spacy.load("en_core_web_sm")

def get_complete_sentences(context, answer):
    doc = nlp(context)
    single_sents = [sent.text for sent in doc.sents]
    two_sents = [single_sents[i] + ' ' + single_sents[i + 1] for i in range(len(single_sents) - 1)]
    for s in single_sents:
        if answer in s:
            return s.rstrip()

    for s in two_sents:
        if answer in s:
            return s.rstrip()

    return answer


def clean_utterance(utterance):
    utterance = utterance.lower()
    for noise in ['actually', 'hmm', 'oh', 'uh', 'uhhh', 'well', "please", "alexa", "echo"]:
        utterance = utterance.replace(noise, " ")
    utterance = re.sub(r'\s+', " ", utterance)
    return utterance.capitalize()


class MRCModel(object):
    def __init__(self, checkpoint) -> None:
        super().__init__()
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.tokenizer = AutoTokenizer.from_pretrained(checkpoint)
        self.pad_on_right = self.tokenizer.padding_side == "right"
        self.model = AutoModelForQuestionAnswering.from_pretrained(checkpoint).to(self.device)
        self.model.eval()

    def infer(self, question, context):
        example = {
            'question': [clean_utterance(question)],
            'context': [context],
            'id': ['example:0'],
        }
        tokenized_example = self._pre_process(example)

        with torch.no_grad():
            inputs = {
                "input_ids": torch.tensor(tokenized_example["input_ids"],device=self.device),
                "attention_mask": torch.tensor(tokenized_example["attention_mask"],device=self.device)
            }
            outputs = self.model(**inputs)
            start_logits = outputs.start_logits.cpu().numpy()
            end_logits = outputs.end_logits.cpu().numpy()
            prediction = (start_logits, end_logits)
            tokenized_example["context"] = context
            result = self._post_processing(tokenized_example, prediction)

        return result

    def _pre_process(self, example):
        tokenized_examples = self.tokenizer(
            example['question'],
            example['context'],
            truncation="only_second" if self.pad_on_right else "only_first",
            max_length=384,
            stride=128,
            return_overflowing_tokens=True,
            return_offsets_mapping=True,
            padding=True,
        )

        # Since one example might give us several features if it has a long context, we need a map from a feature to
        # its corresponding example. This key gives us just that.
        sample_mapping = tokenized_examples.pop("overflow_to_sample_mapping")

        # For evaluation, we will need to convert our predictions to substrings of the context, so we keep the
        # corresponding example_id and we will store the offset mappings.
        tokenized_examples["example_id"] = []

        for i in range(len(tokenized_examples["input_ids"])):
            # Grab the sequence corresponding to that example (to know what is the context and what is the question).
            sequence_ids = tokenized_examples.sequence_ids(i)
            context_index = 1 if self.pad_on_right else 0

            # One example can give several spans, this is the index of the example containing this span of text.
            sample_index = sample_mapping[i]
            tokenized_examples["example_id"].append(example["id"][sample_index])

            # Set to None the offset_mapping that are not part of the context so it's easy to determine if a token
            # position is part of the context or not.
            tokenized_examples["offset_mapping"][i] = [
                (o if sequence_ids[k] == context_index else None)
                for k, o in enumerate(tokenized_examples["offset_mapping"][i])
            ]

        return tokenized_examples

    def _post_processing(
            self,
            example,
            predictions: Tuple[np.ndarray, np.ndarray],
            version_2_with_negative: bool = True,
            n_best_size: int = 20,
            max_answer_length: int = 30,
            null_score_diff_threshold: float = 0.0,
    ):
        """
        Post-processes the predictions of a question-answering model to convert them to answers that are substrings of the
        original contexts. This is the base postprocessing functions for models that only return start and end logits.
        """

        all_start_logits, all_end_logits = predictions

        # Build a map example to its corresponding features.
        features_per_example = collections.defaultdict(list)
        for i in range(len(predictions[0])):
            features_per_example['example:0'].append(i)

        # The dictionaries we have to fill.
        all_predictions = collections.OrderedDict()
        all_nbest_json = collections.OrderedDict()
        if version_2_with_negative:
            scores_diff_json = collections.OrderedDict()


        min_null_prediction = None
        prelim_predictions = []

        # Looping through all the features associated to the current example.
        for feature_index in range(len(predictions[0])):
            # We grab the predictions of the model for this feature.
            start_logits = all_start_logits[feature_index]
            end_logits = all_end_logits[feature_index]
            # This is what will allow us to map some the positions in our logits to span of texts in the original
            # context.
            offset_mapping = example["offset_mapping"][feature_index]

            # Update minimum null prediction.
            feature_null_score = start_logits[0] + end_logits[0]
            if min_null_prediction is None or min_null_prediction["score"] > feature_null_score:
                min_null_prediction = {
                    "offsets": (0, 0),
                    "score": feature_null_score,
                    "start_logit": start_logits[0],
                    "end_logit": end_logits[0],
                }

            # Go through all possibilities for the `n_best_size` greater start and end logits.
            start_indexes = np.argsort(start_logits)[-1: -n_best_size - 1: -1].tolist()
            end_indexes = np.argsort(end_logits)[-1: -n_best_size - 1: -1].tolist()
            for start_index in start_indexes:
                for end_index in end_indexes:
                    # Don't consider out-of-scope answers, either because the indices are out of bounds or correspond
                    # to part of the input_ids that are not in the context.
                    if (
                            start_index >= len(offset_mapping)
                            or end_index >= len(offset_mapping)
                            or offset_mapping[start_index] is None
                            or len(offset_mapping[start_index]) < 2
                            or offset_mapping[end_index] is None
                            or len(offset_mapping[end_index]) < 2
                    ):
                        continue
                    # Don't consider answers with a length that is either < 0 or > max_answer_length.
                    if end_index < start_index or end_index - start_index + 1 > max_answer_length:
                        continue

                    prelim_predictions.append(
                        {
                            "offsets": (offset_mapping[start_index][0], offset_mapping[end_index][1]),
                            "score": start_logits[start_index] + end_logits[end_index],
                            "start_logit": start_logits[start_index],
                            "end_logit": end_logits[end_index],
                        }
                    )
        if version_2_with_negative:
            # Add the minimum null prediction
            prelim_predictions.append(min_null_prediction)
            null_score = min_null_prediction["score"]

        # Only keep the best `n_best_size` predictions.
        predictions = sorted(prelim_predictions, key=lambda x: x["score"], reverse=True)[:n_best_size]

        # Add back the minimum null prediction if it was removed because of its low score.
        if version_2_with_negative and not any(p["offsets"] == (0, 0) for p in predictions):
            predictions.append(min_null_prediction)

        # Use the offsets to gather the answer text in the original context.
        context = example["context"]
        for pred in predictions:
            offsets = pred.pop("offsets")
            pred["text"] = context[offsets[0]: offsets[1]]

        # In the very rare edge case we have not a single non-null prediction, we create a fake prediction to avoid
        # failure.
        if len(predictions) == 0 or (len(predictions) == 1 and predictions[0]["text"] == ""):
            predictions.insert(0, {"text": "empty", "start_logit": 0.0, "end_logit": 0.0, "score": 0.0})

        # Compute the softmax of all scores (we do it with numpy to stay independent from torch/tf in this file, using
        # the LogSumExp trick).
        scores = np.array([pred.pop("score") for pred in predictions])
        exp_scores = np.exp(scores - np.max(scores))
        probs = exp_scores / exp_scores.sum()

        # Include the probabilities in our predictions.
        for prob, pred in zip(probs, predictions):
            pred["probability"] = prob

        # Pick the best prediction. If the null answer is not possible, this is easy.
        if not version_2_with_negative:
            all_predictions['example:0'] = predictions[0]["text"]
        else:
            # Otherwise we first need to find the best non-empty prediction.
            i = 0
            while predictions[i]["text"] == "":
                i += 1
            best_non_null_pred = predictions[i]

            # Then we compare to the null prediction using the threshold.
            score_diff = null_score - best_non_null_pred["start_logit"] - best_non_null_pred["end_logit"]
            scores_diff_json['example:0'] = float(score_diff)  # To be JSON-serializable.
            if score_diff > null_score_diff_threshold:
                all_predictions['example:0'] = ""
            else:
                all_predictions['example:0'] = best_non_null_pred["text"]

        # Make `predictions` JSON-serializable by casting np.float back to float.
        all_nbest_json['example:0'] = [
            {k: (float(v) if isinstance(v, (np.float16, np.float32, np.float64)) else v) for k, v in pred.items()}
            for pred in predictions
        ]

        return all_predictions['example:0']


model_name = "/deploy/app/checkpoint/roberta-wikihow-finetuned"
mrc_model = MRCModel(model_name)


def parse_step_nums(current_state: str):    
    pattern = r'MethodNo([0-9]+)of([0-9]+)w([0-9]+)steps_StepAt([0-9]+)'
    match = re.search(pattern, current_state)
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
    return -1, -1, -1, -1


def get_inst(msg):
    method_idx, num_methods, total_steps, current_step = parse_step_nums(msg.get('taco_state', ''))
    prev_method_idx, prev_num_methods, prev_total_steps, prev_step = parse_step_nums(msg.get('last_taco_state', ''))
    if current_step - prev_step == 1:
        return ' You may say previous to revisit. '
    elif current_step - prev_step > 1:
        return f' You may say go to step {prev_step + 1} to revisit. '
    else:
        return ' You may say next to move on. '


def handle_message(msg):
    # your remote module should operate on the text or other context information here
    # most recent user utterance
    question = msg['text'][0]
    # current step's details
    context_list = msg.get('current_step_details', [])
    is_wikihow = msg.get('is_wikihow', False)

    if question and len(context_list) > 0:
        context = ' '.join(context_list)
        speak_output = mrc_model.infer(question, context)

        if not speak_output:
            return {"response": '', "shouldEndSession": False}
        elif speak_output:
            if is_wikihow:
                speak_output = get_complete_sentences(context, speak_output)
            else:
                speak_output = speak_output.rstrip()
                speak_output = (speak_output + ' ') if speak_output[-1] == '.' else (speak_output + '. ')

            speak_output = re.sub(r'\n+', '. ', speak_output)
            if len(context_list) > 1 and speak_output in context_list[0]:
                speak_output = (
                    'I found the answer in the previous step. ' + 
                    speak_output + 
                    get_inst(msg)
                )
            else:
                speak_output += ' You may say next to move on. '
            
            return {"response": speak_output, "shouldEndSession": False}
        else:
            return {"response": '', "shouldEndSession": False}
    else:
        return {"response": '', "shouldEndSession": False}