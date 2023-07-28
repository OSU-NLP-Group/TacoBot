"""
This module uses neuralcoref to extract the coreference clusters from the previous and current turn. The input to
neuralcoref is the user’s utterance from the previous and current turn along with the bot’s previous response. This
returns lists with the pronoun referenced along with the noun it points to.
"""
import spacy
import re

nlp = spacy.load("en_core_web_sm")

import neuralcoref

neuralcoref.add_to_pipe(nlp)

# text is user, response is bot
required_context = ["text", "response"]

ignore_list = [
    "'s",
    "i",
    "me",
    "my",
    "myself",
    "we",
    "our",
    "ours",
    "ourselves",
    "you",
    "you're",
    "you've",
    "you'll",
    "you'd",
    "your",
    "yours",
    "yourself",
    "yourselves",
]

remove_symbol = r"\:|\-|\~|\(|\)|\%|\$|\#|\@|\&|\*|\+|\=|\^|\<|\>"


def get_required_context():
    return required_context


def handle_message(msg):
    user_text = msg["text"]
    bot_response = msg["response"]
    # alternate user text and bot response, user response last
    input_text = ""
    for i in range(len(user_text) - 1, -1, -1):
        input_text += (user_text[i] + ". ") if user_text[i] else ""

        # strip prosody tags from responses
        if bot_response[i]:
            augmented_bot_response = re.sub(r"\<.*?\>", "", bot_response[i])
            augmented_bot_response = re.sub(remove_symbol, "", augmented_bot_response).strip()
            input_text += augmented_bot_response + " "
        else:
            input_text += ""

    doc = nlp(input_text)
    coref_clusters = doc._.coref_clusters
    valid_coref_clusters = []
    for cluster in coref_clusters:
        cluster_valid = True
        for item in cluster:
            if str(item) in ignore_list:
                cluster_valid = False
        if cluster_valid:
            word_pairs = []
            # transforming span into string for json
            for span in cluster.mentions:
                if word_pairs.count(span.text.lower()) <= 1:
                    word_pairs.append(span.text)
            valid_coref_clusters.append(word_pairs)
    return valid_coref_clusters
