from python:alpine

RUN apk update \
    && rm -rf /var/cache/apk/*

RUN pip3 install --upgrade pip && pip3 install pipenv

RUN set -ex && mkdir /opt/app

WORKDIR /opt/app

COPY Pipfile Pipfile

COPY Pipfile.lock Pipfile.lock

# --deploy requires lockfile to be up to date. You can remove --deploy if
# you're having issues in dev.
RUN set -ex && pipenv install --deploy --system
