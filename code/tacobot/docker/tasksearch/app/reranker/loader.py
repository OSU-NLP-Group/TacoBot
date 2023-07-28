import re
import pdb
import json
import random
import pickle
import numpy as np
from tqdm import tqdm

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer


class WikihowTitleDataset(Dataset):
    def __init__(self, data_path, train=False, 
                 train_neg_size=9, train_pos_size=1, 
                 top_k=3, test_neg_size=30, demo=0,
                 do_syn_rep=False):
        
        self.train = train
        self.data = [json.loads(x) for x in open(data_path)]
        
        if demo > 0:
            self.data = self.data[:demo]
        
        self.train_neg_size = train_neg_size
        self.train_pos_size = train_pos_size
        self.top_k = top_k
        self.test_neg_size = test_neg_size
        self.do_syn_rep = do_syn_rep
        
        self.size = len(self.data)

    def __len__(self):
        return self.size
    
    def __getitem__(self, idx):
        # print(random.uniform(0, 1))
        if self.train:
            query = self.data[idx]['query']
            
            if self.do_syn_rep:
                query = synonym_replacement(query)
            
            negatives = self.data[idx]['negatives']
            positives = self.data[idx]['positives'][:self.top_k] # only trust the top-3 search
            
            if len(negatives) > self.train_neg_size:
                neg_samples = random.sample(negatives, self.train_neg_size)
            else:
                neg_samples = random.choices(negatives, k=self.train_neg_size)

            if len(positives) > self.train_pos_size:
                pos_samples = random.sample(positives, self.train_pos_size)
            else:
                pos_samples = random.choices(positives, k=self.train_pos_size)
            
            candidates = neg_samples + pos_samples
            labels = [0] * len(neg_samples) + [1] * len(pos_samples)
            indices = list(range(len(candidates))); random.shuffle(indices)
            candidates = [candidates[i] for i in indices]
            labels = [labels[i] for i in indices]

            return {
                'query': query,
                'candidates': candidates,
                'labels': labels
            }
            
        else:
            query = self.data[idx]['query']
            if "labeled_titles" not in self.data[idx]:
                negatives = self.data[idx]['negatives'][:self.test_neg_size]
                positives = self.data[idx]['positives'][:self.top_k]
                candidates = negatives + positives
                labels = [0] * len(negatives) + [1] * len(positives)
            else:
                candidates = self.data[idx]['candidates']
                labels = [1 if x in self.data[idx]['labeled_titles'] else 0 for x in candidates]
                if sum(labels) == 0:
                    candidates += self.data[idx]['labeled_titles'] 
                    labels += [1] * len(self.data[idx]['labeled_titles'] )

            return {
                'query': query,
                'candidates': candidates,
                'labels': labels
            }
            
            

if __name__ == '__main__':
    
    # train_set = WikihowTitleDataset(
    #     './wikihow_titles_train_2160.jsonl',
    #     train=True
    # )
    # train_loader = DataLoader(train_set, batch_size=3, shuffle=True)

    train_set = WikihowTitleDataset(
        './wikihow_titles_val_463.jsonl',
        train=True
    )
    train_loader = DataLoader(train_set, batch_size=1)

    print(len(train_set))
    print(len(train_loader))

    tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')    
    for batch in tqdm(train_loader):
        print(batch)
        labels = torch.cat([x.unsqueeze(1) for x in batch['labels']], dim=1)
        print(labels)
        list_query = []
        list_title = []
        for i in range(len(batch['query'])):
            for j in range(len(batch['candidates'])):
                list_query.append(batch['query'][i])
                list_title.append(batch['candidates'][j][i])
        print(list_query, list_title)
        # print(tokenizer(list_query, list_title, padding=True, truncation=True, return_tensors="pt").input_ids)
        exit()