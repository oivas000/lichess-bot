FROM debian:stable-slim
MAINTAINER OIVAS7572
RUN echo OIVAS7572
COPY . .
COPY requirements.txt .

# If you want to run any other commands use "RUN" before.

RUN apt update > aptud.log && apt install -y wget python3 python3-pip p7zip-full > apti.log
RUN python3 -m pip install --no-cache-dir -r requirements.txt > pip.log

RUN wget --no-check-certificate -nv "https://gitlab.com/OIVAS7572/Goi5.1.bin/-/raw/MEGA/Goi5.1.bin.7z" -O Goi5.1.bin.7z \
&& 7z e Goi5.1.bin.7z && rm Goi5.1.bin.7z

RUN wget --no-check-certificate -nv "https://abrok.eu/stockfish/builds/590447d7a162058ed1f68270c84aac4e2f256bb1/linux64modern/stockfish_21082209_x64_modern.zip" -O chess-engine.zip \
&& 7z e chess-engine.zip && rm chess-engine.zip && mv stockfish* chess-engine

RUN chmod +x chess-engine
#Engine name ^^^^^^^^^^^^

CMD python3 lichess-bot.py -u
