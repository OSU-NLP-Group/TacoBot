import re
import numpy as np
from sentence_transformers import SentenceTransformer
import pickle
from sentence_transformers.util import semantic_search,dot_score
import torch

from time import perf_counter

required_context = ['text']
def get_required_context():
    return required_context


def clean_utterance(utterance):
    utterance = utterance.lower()
    for noise in ['actually', 'hmm', 'oh', 'uh', 'uhhh', 'well', "please", "alexa", "echo"]:
        utterance = utterance.replace(noise, " ")
    utterance = re.sub(r'\s+', " ", utterance)
    return utterance.capitalize()


class FAQModel(object):
    def __init__(self, faq_dump_path):
        super().__init__()
        self.faq_list, self.doc_embeddings = pickle.load(open(faq_dump_path, "rb"))
        self.model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
        self.model.eval()
        self.sim_threshold = 0.8

    def infer(self, question):
        encode_time = match_time = 0
        with torch.no_grad():
            encode_start = perf_counter()
            question_embeddings = self.model.encode(clean_utterance(question))
            encode_time = perf_counter()-encode_start
            match_start = perf_counter()

            # sim = cos_sim(question_embeddings, self.doc_embeddings)[0].numpy()
            # max_index = np.argmax(sim)

            result = semantic_search(question_embeddings, self.doc_embeddings, corpus_chunk_size=5000, top_k=1,score_function=dot_score)[0][0]
            score, max_index = result['score'], result['corpus_id']
            match_time = perf_counter()-match_start

        if score >= self.sim_threshold:
            return self.faq_list[max_index][1], encode_time, match_time
        else:
            return "", encode_time, match_time


faq_dump_path = "/deploy/app/checkpoint/faq_question_embeddings.pickle"
faq_model = FAQModel(faq_dump_path)


def handle_message(msg):
    initial_start = perf_counter()
    total_time = 0
    
    # your remote module should operate on the text or other context information here
    # most recent user utterance
    question = msg['text'][0]
    # current step's details
    answer, encode_time, match_time = faq_model.infer(question)
    total_time = perf_counter() - initial_start
    return {"response": answer, "shouldEndSession": False, 'profiling': [total_time, encode_time, match_time]}
