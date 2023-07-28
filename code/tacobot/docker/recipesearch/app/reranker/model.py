import os
import sys
import json

import torch
import torch.nn as nn
import torch.nn.functional as F

from transformers import AutoConfig, AutoModel


class SearchQueryRanker(nn.Module):
    def __init__(self):
        super(SearchQueryRanker, self).__init__()
        self.config = AutoConfig.from_pretrained('bert-base-uncased')
        self.bert_encoder = AutoModel.from_config(self.config)

        # self.config = AutoConfig.from_pretrained('roberta-large')
        # self.bert_encoder = AutoModel.from_pretrained('roberta-large')
        
        self.dropout = nn.Dropout(self.config.hidden_dropout_prob)
        
        # self.candidate_net = nn.Sequential(nn.Linear(2 * config.hidden_size, config.hidden_size),
        #                                    nn.ReLU(),
        #                                    nn.Linear(config.hidden_size, 1))
        
        self.output = nn.Linear(self.config.hidden_size, 1)

    def cand_loss(self, logits, labels):
        return F.cross_entropy(logits, labels)

    def forward(self, 
                input_ids=None,
                attention_mask=None,
                token_type_ids=None,
                labels=None,
                cand_size=None):
        
        # bs, nc = labels.size()
        # encode subqueries
        input_encoding = self.bert_encoder(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids
        )
        # cls_outputs = self.dropout(input_encoding[1])  # [B*N, D]
        cls_outputs = input_encoding[1]  # [B*N, D]

        cls_outputs = self.output(cls_outputs)  # [B*N, 1]
        cls_outputs = cls_outputs.reshape(-1, cand_size)

        if labels is not None:
            loss = F.binary_cross_entropy_with_logits(cls_outputs, labels, reduction='mean')
        else:
            loss = None

        return {'loss': loss, 'prediction': cls_outputs}
    

"""
if __name__ == '__main__':

    model = MyModel()
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

    # Toy data
    batch = {
        "question": [
            "what state is home to the university that is represented in sports by george washington colonials men 's basketball",
            "what year did the team with baltimore fight song win the superbowl",
            "which school with the fight song '' the orange and blue `` did emmitt smith play for"],
        "decompositions": [
            ["the education institution has a sports team named george washington colonials men 's basketball",
             "what state is the %composition",
             "done"
             ],
            ["the sports team with the fight song the baltimore fight song",
             "what year did %composition win the superbowl",
             "done"
             ],
            ["what football teams did emmitt smith play for",
             "what football teams is the sports team with the fight song the orange and blue",
             "done"
             ]]
    }

    question = tokenizer.batch_encode_plus(
        batch["question"], add_special_tokens=True, padding=True, return_tensors='pt')
    decompositions = tokenizer.batch_encode_plus(sum(
        batch["decompositions"], []), add_special_tokens=True, padding=True, return_tensors='pt')

    # Training
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0001)

    for _ in range(10):
        outputs = model(
            input_ids=question['input_ids'],
            token_type_ids=question['token_type_ids'],
            attention_mask=question['attention_mask'],
            decoder_input_ids=decompositions['input_ids'],
            decoder_token_type_ids=decompositions['token_type_ids'],
            decoder_attention_mask=decompositions['attention_mask'],
            # decoder_num_hops=[len(_)
            #                   for _ in batch["decompositions"]],
            return_dict=True)
        qd_loss = outputs['qd_loss']
        print(f"Epoch {_:3d}: qd_loss {qd_loss.data:2.4f}")

        optimizer.zero_grad()
        qd_loss.backward()
        optimizer.step()

    # TODO: save and load from pretrained
    # # model.save_pretrained("bert2bert")
    # # model = MyModel.from_pretrained("bert2bert")
    # pdb.set_trace()
    torch.save(model.state_dict, "bert2bert/model.pt")
    model = MyModel()
    model.load_state_dict("bert2bert/model.pt")

    # Generation
    generated = model.inference(
        input_ids=question['input_ids'],
        token_type_ids=question['token_type_ids'],
        attention_mask=question['attention_mask'])
    # pdb.set_trace()
    print(generated)
    for batch_idx in range(3):
        print(batch_idx)
        for i in range(len(generated)):
            print(tokenizer.decode(generated[i][batch_idx]))
"""