

Call the function, *model_eval* in inference.py

```
from inference import model_eval
res = model_eval([('learn wrestling', ['How to Perform Pro Wrestling Moves', 'How to Become a Pro Wrestler', 'How to Wrestle'])], model_path='./diy_reranker.pt')
```

Get the reranked list from *res['reranked']*