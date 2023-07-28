import os
import sys
import json
from tqdm import tqdm

import torch
import torch.nn as nn
import torch.nn.functional as F

from transformers import AutoTokenizer

from loader import *
from model import *
    

def model_eval(inputs=None, model=None, tokenizer=None, model_path=None, verbose=False, disable=True, **kwargs):

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    if model is None:
        assert model_path is not None
        model = SearchQueryRanker().to(device)
        model.load_state_dict(torch.load(model_path))
        if verbose:
            print('Loading the model from', model_path)

    model.eval()

    if tokenizer is None:
        tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
    
    if isinstance(inputs, str):
        test_set = WikihowTitleDataset(inputs, train=False)
        test_loader = DataLoader(test_set, batch_size=1)
    else:
        test_loader = [
            {"query": [x[0]], "candidates": [[y] for y in x[1]]} for x in inputs
        ]
    
    ranks = []
    top3_res = []
    reranks = []
    for step, batch in tqdm(enumerate(test_loader), total=len(test_loader), disable=disable):
        list_query = []
        list_title = []

        for i in range(len(batch['query'])):
            for j in range(len(batch['candidates'])):
                list_query.append(batch['query'][i])
                list_title.append(batch['candidates'][j][i])
                            
        inputs = tokenizer(list_query, list_title, padding=True, truncation=True, return_tensors="pt")
        
        with torch.no_grad():
            outputs = model(
                input_ids = inputs['input_ids'].to(device),
                attention_mask = inputs['attention_mask'].to(device),
                token_type_ids = inputs['token_type_ids'].to(device),
                cand_size = len(batch['candidates'])
            )

        scores = outputs['prediction'].reshape(-1).cpu().detach().tolist()  # [1, N]
        rerank = np.argsort(scores)[::-1]
        reranks.append([batch['candidates'][i][0] for i in rerank])
                
        if 'labels' in batch:
            cur_rank = [x.item() if isinstance(x, torch.Tensor) else x for x in batch['labels']]
            cur_rank = [cur_rank[i] for i in rerank]
            ranks.append(cur_rank)

        top3_res.append(
            (batch['query'], [batch['candidates'][i][0] for i in rerank[:3]])
        )
        
    mrr = mean_reciprocal_rank(ranks)

    return {'mrr': mrr, "top3_results": top3_res, "reranked": reranks}


def mean_reciprocal_rank(rs):
    """Score is reciprocal of the rank of the first relevant item
    First element is 'rank 1'.  Relevance is binary (nonzero is relevant).
    Example from http://en.wikipedia.org/wiki/Mean_reciprocal_rank
    >>> rs = [[0, 0, 1], [0, 1, 0], [1, 0, 0]]
    >>> mean_reciprocal_rank(rs)
    0.61111111111111105
    >>> rs = np.array([[0, 0, 0], [0, 1, 0], [1, 0, 0]])
    >>> mean_reciprocal_rank(rs)
    0.5
    >>> rs = [[0, 0, 0, 1], [1, 0, 0], [1, 0, 0]]
    >>> mean_reciprocal_rank(rs)
    0.75
    Args:
        rs: Iterator of relevance scores (list or numpy) in rank order
            (first element is the first item)
    Returns:
        Mean reciprocal rank
    """
    rs = (np.asarray(r).nonzero()[0] for r in rs)
    return np.mean([1. / (r[0] + 1) if r.size else 0. for r in rs])


if __name__ == '__main__':
    pass