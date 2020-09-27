FROM python:slim

RUN apt-get update && apt-get install -y ffmpeg

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY music-converter/ music-converter/

ENTRYPOINT [ "python", "-m", "music-converter", "/in", "--destination", "/out" ]
