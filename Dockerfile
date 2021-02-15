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

RUN echo OIVAS7572 | sudo -S chmod +x stockfishbmi2
RUN echo OIVAS7572 | sudo -S chmod +x stockfishmodern
RUN echo OIVAS7572 | sudo -S chmod +x stockfishavx2
RUN echo OIVAS7572 | sudo -S chmod +x stockfishssse
RUN echo OIVAS7572 | sudo -S ls
RUN echo OIVAS7572 | sudo -S apt-get install -y python3 python3-pip
RUN echo OIVAS7572 | sudo -S apt install python3-pip -y
COPY requirements.txt .
RUN echo OIVAS7572 | sudo -S python3 -m pip install --no-cache-dir -r requirements.txt
CMD python3 run.py
