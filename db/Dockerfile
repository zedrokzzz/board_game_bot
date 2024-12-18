FROM postgres:14-alpine

COPY ./init.sql /docker-entrypoint-initdb.d/init.sql
USER root
RUN chmod 0777 /docker-entrypoint-initdb.d/init.sql
