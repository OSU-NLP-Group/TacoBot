FROM public.ecr.aws/alexaprizesharedresources/cobot/cobot_base:v1

RUN apt-get update -y
RUN apt-get install -y nginx supervisor gcc g++

# FROM public.ecr.aws/alexaprizesharedresources/ubuntu:latest

# ENV DEBIAN_FRONTEND=noninteractive

# RUN apt-get update -y
# RUN apt-get install -y nginx supervisor gcc g++ python3-pip

# update pip
RUN pip3 install pip --upgrade

# Setup flask application
RUN mkdir -p /deploy/app
COPY app /deploy/app
RUN pip3 install -r /deploy/app/requirements.txt
RUN python3 -m spacy download en_core_web_sm

# RUN pip3 install awscli --upgrade

# Get pretrained model
RUN apt-get install -y wget
RUN mkdir -p /deploy/app/checkpoint
RUN wget https://intent-classification-model.s3.amazonaws.com/trained_model_4_28.tgz -P /deploy/app/checkpoint/
RUN tar -xzvf /deploy/app/checkpoint/trained_model_4_28.tgz -C /deploy/app/checkpoint/
RUN rm /deploy/app/checkpoint/trained_model_4_28.tgz
# RUN aws s3 cp s3://intent-classification-model/trained_model /deploy/app/checkpoint --recursive


RUN python3 -c "from transformers import RobertaTokenizer; RobertaTokenizer.from_pretrained('princeton-nlp/unsup-simcse-roberta-base')"
RUN python3 -c "from transformers import RobertaModel; RobertaModel.from_pretrained('princeton-nlp/unsup-simcse-roberta-base')"

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

