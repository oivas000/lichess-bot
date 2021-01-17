FROM debian:latest
ENTRYPOINT []
CMD ["echo OIVAS7572"]
RUN apt-get update && \
    apt-get -y install sudo
RUN useradd OIVAS7572 && echo "OIVAS7572:OIVAS7572" | chpasswd && adduser OIVAS7572 sudo
USER OIVAS7572


RUN echo OIVAS7572 | sudo -S apt-get update && sudo apt-get install -y vim
RUN echo OIVAS7572 | sudo -S apt-get install -y wget
RUN echo OIVAS7572 | sudo -S apt-get update
RUN echo OIVAS7572 | sudo -S apt-get install -y python3 python3-pip
ADD /engine/ .
RUN chmod +x ./engine/stockfishbmi2
RUN chmod +x ./engine/stockfishmodern
RUN chmod +x ./engine/stockfishavx2
RUN chmod +x ./engine/stockfishssse
CMD ["apt install python3-pip -y"]
CMD ["apt install python3-venv"]
CMD ["python3 -m venv venv"]
CMD ["source ./venv/bin/activate"]
COPY requirements.txt .
RUN echo OIVAS7572 | sudo -S python3 -m pip install --no-cache-dir -r requirements.txt
COPY . .
CMD python3 lichess-bot.py -u

