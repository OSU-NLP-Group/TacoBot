

Call the function, *model_eval* in inference.py

```
from inference import model_eval
res = model_eval([('learn wrestling', ['How to Wrestle', 'How to Perform Pro Wrestling Moves', 'How to Become a Pro Wrestler'])], model_path='./saved_pytorch_model_best_epoch.pt')
```

Get the reranked list from *res['reranked']*