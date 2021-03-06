FROM debian:10.8-slim
MAINTAINER SAVIO PRINCE
RUN echo OIVAS7572
CMD echo OIVAS7572
COPY . .
RUN apt-get update
RUN apt-get -y install sudo
RUN useradd OIVAS7572 && echo "OIVAS7572:OIVAS7572" | chpasswd && adduser OIVAS7572 sudo
USER OIVAS7572
ADD /engine/ .

# If you are using docker  
# change config.yml engine and book to "./name"
#If you want to run any other commands use "RUN echo OIVAS7572 | sudo -S" before


RUN echo OIVAS7572 | sudo -S chmod +x stockfish_13_linux_x64_modern
RUN echo OIVAS7572 | sudo -S chmod +x fairy-stockfish-largeboard_x86-64

RUN echo OIVAS7572 | sudo -S apt-get install -y wget
RUN echo OIVAS7572 | sudo -S apt install p7zip-full -y
RUN echo OIVAS7572 | sudo -S wget --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id=1FkYpoSGMh9Yh5VV3QK9y95l7z8rERO7E' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=1FkYpoSGMh9Yh5VV3QK9y95l7z8rERO7E" -O Aaricia_2012.7z && rm -rf /tmp/cookies.txt
RUN echo OIVAS7572 | sudo -S 7z e Aaricia_2012.7z
RUN echo OIVAS7572 | sudo -S rm Aaricia_2012.7z 
RUN echo OIVAS7572 | sudo -S apt-get install -y python3 python3-pip
RUN echo OIVAS7572 | sudo -S apt install python3-pip -y
COPY requirements.txt .
RUN echo OIVAS7572 | sudo -S python3 -m pip install --no-cache-dir -r requirements.txt
CMD python3 run.py
