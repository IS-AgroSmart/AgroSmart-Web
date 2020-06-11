FROM python:3.7.7-buster

ADD requirements.txt /app/requirements.txt

RUN apt-get update
RUN apt-get install -y gdal-bin libgdal-dev python-gdal build-essential
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt
#RUN set -ex \
#    && apk add --no-cache --virtual .fetch-deps gdal \
#    && apk add --no-cache --virtual .build-deps postgresql-dev build-base \
#    && apk add jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev bind-tools mariadb-connector-c-dev gdal \
#    && python -m venv /env \
#    && /env/bin/pip install --upgrade pip \
#    && /env/bin/pip install --no-cache-dir -r /app/requirements.txt \
#    && runDeps="$(scanelf --needed --nobanner --recursive /env \
#        | awk '{ gsub(/,/, "\nso:", $2); print "so:" $2 }' \
#        | sort -u \
#        | xargs -r apk info --installed \
#        | sort -u)" \
#    && apk add --virtual rundeps $runDeps \
#    && apk del .build-deps

# ADD . /app
WORKDIR /app

ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH

EXPOSE 8000

#CMD ["gunicorn", "--bind", ":8000", "--workers", "3", "--worker-class", "eventlet", "IngSoft1.wsgi:application"]
CMD ["python", "manage.py", "runserver"]
