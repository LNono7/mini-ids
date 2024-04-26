FROM python:3-bookworm

WORKDIR /usr/src/app

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get -qq update \
    && apt-get -yqq install --no-install-recommends rsyslog openssh-server sshpass iproute2 netcat-traditional\
    && apt-get clean -y \
    && apt-get -qqy autoremove \
    && rm -rf /var/lib/apt/lists/*

COPY app ./

RUN chmod 755 trigger_ids.bash

RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "main.py" ]