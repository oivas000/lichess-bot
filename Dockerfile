FROM debian:latest
MAINTAINER SAVIO PRINCE
RUN echo OIVAS7572
CMD echo OIVAS7572
COPY . .
WORKDIR ..
RUN apt-get update
RUN apt-get -y install sudo
RUN useradd OIVAS7572 && echo "OIVAS7572:OIVAS7572" | chpasswd && adduser OIVAS7572 sudo
USER OIVAS7572
ADD /engine/ .

# If you are using docker  
# change config.yml engine and book to "./name"
# 3-4-5piecesSyzygy.zip # 1Zd9uLYAK61eC_Yin79X59w1BfREfairU
# Cerebellum3Merge.bin.7z # 1_f6Ru0FhD3V4-VFSUVuX6-95NLaL_Y3_

RUN echo OIVAS7572 | sudo -S chmod +x stockfishbmi2
RUN echo OIVAS7572 | sudo -S chmod +x stockfishmodern
RUN echo OIVAS7572 | sudo -S chmod +x stockfishavx2
RUN echo OIVAS7572 | sudo -S chmod +x stockfishssse

RUN echo OIVAS7572 | sudo -S rm -r engine
RUN echo OIVAS7572 | sudo -S apt-get update && sudo apt-get install -y vim
RUN echo OIVAS7572 | sudo -S apt-get install -y wget
RUN echo OIVAS7572 | sudo -S apt install p7zip-full -y
WORKDIR 3-4-5
RUN echo OIVAS7572 | sudo -S wget --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id=1Zd9uLYAK61eC_Yin79X59w1BfREfairU' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=1Zd9uLYAK61eC_Yin79X59w1BfREfairU" -O 3-4-5piecesSyzygy.zip && rm -rf /tmp/cookies.txt
RUN echo OIVAS7572 | sudo -S 7z e 3-4-5piecesSyzygy.zip
RUN echo OIVAS7572 | sudo -S rm 3-4-5piecesSyzygy.zip
WORKDIR ..
RUN echo OIVAS7572 | sudo -S wget --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id=1_f6Ru0FhD3V4-VFSUVuX6-95NLaL_Y3_' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=1_f6Ru0FhD3V4-VFSUVuX6-95NLaL_Y3_" -O Cerebellum3Merge.bin.7z && rm -rf /tmp/cookies.txt
RUN echo OIVAS7572 | sudo -S 7z e book.7z
RUN echo OIVAS7572 | sudo -S rm book.7z
RUN echo OIVAS7572 | sudo -S pwd && ls

RUN echo OIVAS7572 | sudo -S apt-get install -y python3 python3-pip
RUN echo OIVAS7572 | sudo -S apt install python3-pip -y
RUN echo OIVAS7572 | sudo -S ls
COPY requirements.txt .
RUN echo OIVAS7572 | sudo -S python3 -m pip install --no-cache-dir -r requirements.txt
CMD python3 run.py
