FROM debian:stable-slim
MAINTAINER OIVAS7572
RUN echo OIVAS7572
COPY . .

# If you want to run any other commands use "RUN" before.

RUN apt update > aptud.log && apt install -y wget python3 python3-pip p7zip-full > apti.log
RUN python3 -m pip install --no-cache-dir -r requirements.txt > pip.log

RUN wget --no-check-certificate -nv "https://gitlab.com/OIVAS7572/Goi5.1.bin/-/raw/MEGA/Goi5.1.bin.7z" -O Goi5.1.bin.7z \
&& 7z e Goi5.1.bin.7z && rm Goi5.1.bin.7z && mv Goi5.1.bin engines/books/Goi5.1.bin

RUN wget --no-check-certificate -nv "https://abrok.eu/stockfish/builds/c2aaaa65f97d4cd5fc06f19ce8d158d85dcd7a7b/linux64modern/stockfish_22070513_x64_modern.zip" -O chess-engine.zip \
&& 7z e chess-engine.zip && rm chess-engine.zip && mv stockfish* engines/chess-engine

RUN chmod +x engines/chess-engine
#Engine name ^^^^^^^^^^^^^^^^^^^^

CMD python3 lichess-bot.py -u
