FROM python:3.10.4

ENV DEBIAN_FRONTEND=noninteractive
RUN apt update && apt install -y iputils-ping && rm -rf /var/lib/apt/lists/*


COPY requirements.txt /
RUN pip install -r /requirements.txt

COPY hadikontroller /app
WORKDIR /app

CMD ["python", "hadikontroller.py"]
