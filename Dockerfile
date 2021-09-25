FROM debian:stable-slim
MAINTAINER OIVAS7572
RUN echo OIVAS7572
COPY . .
COPY requirements.txt .

# If you want to run any other commands use "RUN" before.

RUN apt-get update && apt-get install -y wget python3 python3-pip p7zip-full
RUN python3 -m pip install --no-cache-dir -r requirements.txt

RUN wget --no-check-certificate "https://gitlab.com/OIVAS7572/Goi5.1.bin/-/raw/master/Goi5.1.bin.7z" -O Goi5.1.bin.7z \
&& 7z e Goi5.1.bin.7z && rm Goi5.1.bin.7z

RUN wget --no-check-certificate "https://abrok.eu/stockfish/builds/773dff020968f7a6f590cfd53e8fd89f12e15e36/linux64modern/stockfish_21070214_x64_modern.zip" -O chess-engine.zip \
#&& wget --no-check-certificate "https://tests.stockfishchess.org/api/nn/nn-3475407dc199.nnue" -O nn-3475407dc199.nnue \
&& 7z e chess-engine.zip && rm chess-engine.zip && mv stockfish* chess-engine

RUN chmod +x chess-engine
# Engine name is here ^^^^^^

CMD python3 lichess-bot.py -u