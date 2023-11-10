FROM tensorflow/tensorflow:2.3.1-gpu

ARG DEBIAN_FRONTEND=noninteractive

ENV TZ=Europe/Bratislava

WORKDIR /code

RUN apt-get update && \
    apt-get install -y tzdata && \
    pip3 install --upgrade pip

COPY requirements.txt /code/

RUN pip install -r requirements.txt

COPY . /code/

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
