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


# Get pretrained model
RUN apt-get install -y wget
RUN apt-get install -y unzip
RUN mkdir -p /deploy/app/checkpoint
RUN wget https://asr-error-detector.s3.amazonaws.com/asr_error_classifier_single_task.zip -P /deploy/app/checkpoint/
RUN unzip /deploy/app/checkpoint/asr_error_classifier_single_task.zip -d /deploy/app/checkpoint/
RUN rm /deploy/app/checkpoint/asr_error_classifier_single_task.zip


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

