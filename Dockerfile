FROM debian:10.10-slim
MAINTAINER OIVAS7572
RUN echo OIVAS7572
CMD echo OIVAS7572
COPY . .

#ADD /engine/ .
#RUN rm -r engine

# If you are using docker and you want to run any other commands use "RUN" before.

RUN apt-get update && apt-get install -y wget python3 python3-pip p7zip-full

RUN wget --no-check-certificate "https://gitlab.com/OIVAS7572/Goi5.1.bin/-/raw/master/Goi5.1.bin.7z" -O Goi5.1.bin.7z
RUN 7z e Goi5.1.bin.7z
RUN rm Goi5.1.bin.7z

RUN wget --no-check-certificate "https://abrok.eu/stockfish/builds/773dff020968f7a6f590cfd53e8fd89f12e15e36/linux64modern/stockfish_21070214_x64_modern.zip" -O stockfishmodern.zip
#RUN wget --no-check-certificate "https://tests.stockfishchess.org/api/nn/nn-3475407dc199.nnue" -O nn-3475407dc199.nnue
RUN 7z e stockfishmodern.zip
RUN rm stockfishmodern.zip
RUN mv stockfish_21070214_x64_modern stockfishmodern

COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

RUN chmod +x stockfishmodern
# Engine name is here ^^^^^^^^

CMD python3 run.py
