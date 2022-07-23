FROM python:alpine3.14
RUN mkdir /app
WORKDIR /app
ADD . .

RUN pip3 install -r requirements.txt
RUN pip3 install gunicorn
CMD ["gunicorn", "-w 4", "-b", "0.0.0.0:5000", "main:app"]