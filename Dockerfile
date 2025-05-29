FROM docker.arvancloud.ir/python:3.12.0
RUN apt-get update && \
    apt-get install -y build-essential python vim net-tools && \
    pip install uwsgi

WORKDIR /code
COPY requirements.txt /code/requirements.txt
RUN pip install  --default-timeout=1000 -r /code/requirements.txt
COPY . /code

CMD ["/bin/bash","-c","./startup.sh"]
