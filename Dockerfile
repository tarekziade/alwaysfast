FROM python:3.11

WORKDIR /usr/src/app

COPY requirements.txt ./
COPY src ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./src/af.py" ]
