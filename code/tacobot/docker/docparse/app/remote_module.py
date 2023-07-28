import spacy
import re
import json

nlp = spacy.load("en_core_web_sm", exclude=["ner"])
token_map = {
    "approx.": "approximately",
    "hr.": "hr",
    "min.": "min",
    "sec.": "sec",
    "tbsp.": "Tbsp",
    "Tbsp.": "Tbsp",
    "tsp.": "Tsp",
    "Tsp.": "Tsp",
    "lb.": "lb",
    "oz.": "oz",
}

def replace_tokens(sent):
    tokens = sent.split()
    for i in range(len(tokens)):
        t = tokens[i]
        if t in token_map:
            tokens[i] = token_map[t]
    return ' '.join(tokens)


def recipe_clean_step(sent):
    sent = re.sub(r'\(.*?\.\)', '', sent)
    sent = re.sub(r'\[.*?\]', '', sent)
    sent = re.sub(r'\{.*?\}', '', sent)
    sent = re.sub(r'<.*?>', '', sent)
    sent = re.sub(r'\n', '', sent)
    sent = re.sub(r'\*', '', sent)
    sent = re.sub(r'\d+\\*\.', '', sent)
    sent = sent.replace(".n", ".")
    sent = replace_tokens(sent).lstrip().rstrip()
    return sent


def recipe_clean_sent(sent):
    lower_sent = sent.text.lower()

    if 'tip:' == lower_sent[:4]:
        return nlp(sent.text[4:].lstrip())
    elif 'note:' == lower_sent[:5]:
        return nlp(sent.text[5:].lstrip())
    elif 'etc.' == lower_sent[-4:]:
        return nlp(sent.text[:-4].rstrip() + ' and so on. ')
    else:
        return sent


def get_lemma_set(doc):
    return set(
            [
                token.lemma_ for token in doc if not token.is_stop
            ]
        )


def recipe_chunk(doc):
    chunked = []
    todo = [recipe_clean_sent(sent) for sent in doc.sents if re.search("[a-zA-Z]", sent.text) is not None]

    while len(todo) >= 3:
        lemma_0 = get_lemma_set(todo[0])
        lemma_1 = get_lemma_set(todo[1])
        lemma_2 = get_lemma_set(todo[2])

        overlap_0 = len(lemma_0.intersection(lemma_1))
        overlap_2 = len(lemma_2.intersection(lemma_1))

        if overlap_2 > overlap_0:
            if len(todo[1]) + len(todo[2]) <= 35:
                chunked.append(todo[0].text + ' ')
                chunked.append(todo[1].text + ' ' + todo[2].text + ' ')
                todo = todo[3:]
            else:
                chunked.append(todo[0].text + ' ')
                chunked.append(todo[1].text + ' ')
                todo = todo[2:]
        else:
            if len(todo[0]) + len(todo[1]) <= 35:
                chunked.append(todo[0].text + ' ' + todo[1].text + ' ')
                todo = todo[2:]
            else:
                chunked.append(todo[0].text + ' ')
                chunked.append(todo[1].text + ' ')
                todo = todo[2:]

    if len(todo) == 1:
        if len(todo[0]) <= 5 and len(chunked) > 0:
            chunked[-1] += (todo[0].text + ' ')
        else:
            chunked.append(todo[0].text + ' ')
    elif len(todo) == 2:
        if len(todo[0]) + len(todo[1]) <= 35:
            chunked.append(todo[0].text + ' ' + todo[1].text + ' ')
        else:
            chunked.append(todo[0].text + ' ')
            chunked.append(todo[1].text + ' ')

    return chunked

def parse_recipes(r):
    recipe_item = r['recipe']
    result = []

    recipe_steps = list(nlp.pipe(
        [recipe_clean_step(step['stepText']) for step in recipe_item['instructions']]
    ))

    for i, step in enumerate(recipe_item['instructions']):
        step_doc = recipe_steps[i]
        image = ''
        step_ingredients = step['stepIngredients']

        lower_step_text = step_doc.text.lower()
        if (
            'sidechef' in lower_step_text or
            ('try' in lower_step_text and 'alexa' in lower_step_text) or
            'photograph by' in lower_step_text
        ):
            continue

        if len(step['stepImages']) > 0:
            image = step['stepImages'][0]['url']
        elif len(recipe_item['images']) > 0:
            image = recipe_item['images'][0]['url']

        if i == len(recipe_item['instructions']) - 1 and lower_step_text == 'enjoy!':
            result[-1]['instruction'] += ' Enjoy! '
            break

        insts = recipe_chunk(step_doc)
        for inst in insts:
            result.append({
                            'instruction': inst,
                            'image': image,
                            'ingredients': step_ingredients
                        })
            
    return result


def add_period(x):
    x = x.rstrip()
    return (x + ' ') if x[-1] == '.' else (x + '. ')


def clean_wikihow(step):
    paragraphs = re.split(r'\n+', step)
    inst_detail = nlp(re.sub(r'\(.*?\)', '', paragraphs[0]))
    inst_detail_sents = [sent.text for sent in inst_detail.sents]

    inst = ''
    details = ''
    tips = paragraphs[1:]
    is_list = False
    if len(tips) > 0:
        is_list = (max([len(re.sub(r'\(.*?\)', '', t).split()) for t in tips]) <= 10)

    if len(inst_detail_sents) >= 3 and len(inst_detail) >= 35:
        inst = inst_detail_sents[0] + ' ' + inst_detail_sents[1] + ' '
        if inst_detail[-1].text == ':' and is_list:
            details = ' '.join(inst_detail_sents[2:-1]) + ' '
            tips = [add_period(inst_detail_sents[-1] + ' ' + ', '.join(tips[:-1]) + ', and ' + tips[-1])]
            if not details.strip():
                details = tips[0]
                tips = []
        else:
            details = ' '.join(inst_detail_sents[2:]) + ' ' 
    elif len(tips) > 0:
        inst = inst_detail.text
        if inst_detail[-1].text == ':' and is_list:
            inst += (' ' + tips[0] + ', ' + tips[1] + ', and so on. ')
            details = add_period(inst_detail_sents[-1] + ' ' + ', '.join(tips[:-1]) + ', and ' + tips[-1])
            tips = []
        else:
            details = tips[0]
            tips = tips[1:]
    else:
        inst = inst_detail.text

    return {
        'instruction': inst,
        'detail': details,
        'tips': tips,
    }


def parse_wikihow(w):
    wikihow_item = w['_source']

    result = []
    for i in range(len(wikihow_item['methods'])):
        steps = []
        for j in range(len(wikihow_item['methods'][i])):
            step_text = wikihow_item['methods'][i][j]
            if 'methodsHeadlines' in wikihow_item:
                try:
                    step_text = wikihow_item['methodsHeadlines'][i][j] + ' ' + step_text
                except:
                    pass

            parse = clean_wikihow(step_text)
            parse['image'] = wikihow_item['methodsImages'][i][j] if wikihow_item['methodsImages'][i][j] else ''
            parse['qa_context'] = step_text
            steps.append(parse)
        result.append(steps)

    return result


required_context = ['text']

def get_required_context():
    return required_context

def handle_message(msg):
    """
    recipe: 
    if is_batch
        list of list of
        {
            'instruction': '',
            'image': '',
            'ingredients': []
        }
    else:
        list of 
        {
            'instruction': '',
            'image': '',
            'ingredients': []
        }

    wikihow: list of list of
    {
        'instruction': '',
        'detail': '',
        'tips': [],
        'image': '',
        'qa_context': ''
    }
    """
    
    current_task_docparse = msg.get('current_task_docparse', None)
    result = None
    is_batch = False

    if not current_task_docparse:
        query_result = msg.get('query_result', None)
        list_item_selected = msg.get('list_item_selected', -1)
        is_wikihow = msg.get('is_wikihow', None)

        if query_result and (is_wikihow is not None):
            if list_item_selected >= 0:
                if is_wikihow:
                    result = parse_wikihow(query_result[list_item_selected])
                else:
                    result = parse_recipes(json.loads(query_result['documents'][list_item_selected]))
            else:
                if not is_wikihow:
                    result = [parse_recipes(json.loads(item)) for item in query_result['documents']]
                    is_batch = True
    
    return {'docparse': result, 'is_batch': is_batch}
