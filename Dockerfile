FROM python:3.9
ADD requirements.txt /requirements.txt
RUN pip3 install -r requirements.txt
ADD . /
EXPOSE 5000
CMD [ "gunicorn", "--name", "flask-web", "--workers", "1", "-k", "gevent", "--timeout", "120", "--bind", "0.0.0.0:5000", "app:app" ]