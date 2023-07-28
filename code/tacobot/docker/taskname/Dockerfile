#FROM public.ecr.aws/alexaprizesharedresources/cobot/cobot_base:v1

#RUN apt-get update -y
#RUN apt-get install -y nginx supervisor gcc g++

FROM public.ecr.aws/alexaprizesharedresources/ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y
RUN apt-get install -y nginx supervisor gcc g++ python3-pip

# update pip
RUN pip3 install pip --upgrade

# Setup flask application
RUN mkdir -p /deploy/app
COPY app /deploy/app
RUN pip3 install --upgrade -r /deploy/app/requirements.txt

RUN apt-get install -y libenchant-dev

# Get pretrained model
RUN apt-get install -y wget
RUN mkdir -p /deploy/app/checkpoint

RUN mkdir -p /deploy/app/data
RUN wget https://taco-recipe-data.s3.amazonaws.com/cleaned_cooking_nouns.json -P /deploy/app/data/
RUN wget https://taco-recipe-data.s3.amazonaws.com/cleaned_cooking_verbs.json -P /deploy/app/data/

RUN wget https://classifier-extractor.s3.us-east-2.amazonaws.com/classifier_extractor/pos_recipe_cpt.tar.gz -P /deploy/app/checkpoint/
RUN tar -xzvf /deploy/app/checkpoint/pos_recipe_cpt.tar.gz -C /deploy/app/checkpoint/
RUN rm /deploy/app/checkpoint/pos_recipe_cpt.tar.gz

RUN wget https://classifier-extractor.s3.us-east-2.amazonaws.com/classifier_extractor/diy_extractor_checkpoint.tar.gz -P /deploy/app/checkpoint/
RUN tar -xzvf /deploy/app/checkpoint/diy_extractor_checkpoint.tar.gz -C /deploy/app/checkpoint/
RUN rm /deploy/app/checkpoint/diy_extractor_checkpoint.tar.gz

# RUN mkdir -p /deploy/app/checkpoint/classifier_checkpoint
# RUN wget https://classifier-extractor.s3.us-east-2.amazonaws.com/classifier_extractor/classifier_checkpoint.tgz -P /deploy/app/checkpoint/
# RUN tar -xzvf /deploy/app/checkpoint/classifier_checkpoint.tgz -C /deploy/app/checkpoint/classifier_checkpoint/
# RUN rm /deploy/app/checkpoint/classifier_checkpoint.tgz
# RUN aws s3 cp s3://intent-classification-model/trained_model /deploy/app/checkpoint --recursive


# RUN python3 -c "from transformers import RobertaTokenizer; RobertaTokenizer.from_pretrained('princeton-nlp/unsup-simcse-roberta-base')"
# RUN python3 -c "from transformers import AutoConfig; AutoConfig.from_pretrained('princeton-nlp/unsup-simcse-roberta-base')"
RUN python3 -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('bert-base-uncased')"


# Setup nginx
RUN rm /etc/nginx/sites-enabled/default
COPY config/flask.conf /etc/nginx/sites-available/
RUN ln -s /etc/nginx/sites-available/flask.conf /etc/nginx/sites-enabled/flask.conf
RUN echo "daemon off;" >> /etc/nginx/nginx.conf

RUN ln -s /usr/local/bin/gunicorn /usr/bin/gunicorn
# Setup supervisord
RUN mkdir -p /var/log/supervisor
COPY config/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
#COPY config/gunicorn.conf /etc/supervisor/conf.d/gunicorn.conf

EXPOSE 80

# Start processes
CMD ["/usr/bin/supervisord"] 

