FROM python:3.12.12-alpine3.22@sha256:848ba4413eb897e225159b8fc1b02094576cbae4aa73fc13142608ae2c8c0e32

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_FILE=/var/lib/records/records.json
WORKDIR /srv
COPY app/ /srv/app/
RUN mkdir -p /var/lib/records
USER root
EXPOSE 8000
CMD ["python", "/srv/app/server.py"]
