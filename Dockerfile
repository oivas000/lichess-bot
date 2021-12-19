FROM debian:stable-slim
MAINTAINER OIVAS7572
RUN echo OIVAS7572
COPY . .
COPY requirements.txt .

# If you want to run any other commands use "RUN" before.

RUN apt update > aptud.log && apt install -y wget python3 python3-pip p7zip-full build-essential git > apti.log
RUN python3 -m pip install --no-cache-dir -r requirements.txt > pip.log

RUN git clone https://github.com/official-stockfish/Stockfish.git
WORKDIR /Stockfish/src/
RUN make -j build ARCH=x86-64-sse41-popcnt
WORKDIR ../../
RUN cp /Stockfish/src/stockfish . && rm -r Stockfish && mv stockfish chess-engine

#RUN wget --no-check-certificate "http://abrok.eu/stockfish/latest/linux/stockfish_x64_modern.zip" -O chess-engine.zip
#RUN wget --no-check-certificate "https://tests.stockfishchess.org/api/nn/nn-3475407dc199.nnue" -O nn-3475407dc199.nnue
#RUN 7z e chess-engine.zip && rm chess-engine.zip && mv stockfish* chess-engine

RUN wget --no-check-certificate -nv "https://gitlab.com/OIVAS7572/Goi5.1.bin/-/raw/MEGA/Goi5.1.bin.7z" -O Goi5.1.bin.7z \
&& 7z e Goi5.1.bin.7z && rm Goi5.1.bin.7z

RUN chmod +x chess-engine
# Engine name is here ^^^^^^

CMD python3 lichess-bot.py -u
