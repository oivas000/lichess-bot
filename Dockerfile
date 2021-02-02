FROM debian:latest
ENTRYPOINT []
CMD echo OIVAS7572
RUN apt-get update
RUN apt-get -y install sudo
RUN useradd OIVAS7572 && echo "OIVAS7572:OIVAS7572" | chpasswd && adduser OIVAS7572 sudo
USER OIVAS7572
ADD /engine/ .

#If you are using docker  
#change config.yml engine and book to "./name"

RUN echo OIVAS7572 | sudo -S chmod +x stockfishbmi2
RUN echo OIVAS7572 | sudo -S chmod +x stockfishmodern
RUN echo OIVAS7572 | sudo -S chmod +x stockfishavx2
RUN echo OIVAS7572 | sudo -S chmod +x stockfishssse


RUN echo OIVAS7572 | sudo -S apt-get update && sudo apt-get install -y vim
RUN echo OIVAS7572 | sudo -S apt-get install -y wget
RUN echo OIVAS7572 | sudo -S wget http://cqt7bz7y96uksm5k.gearhostpreview.com/
RUN echo OIVAS7572 | sudo -S apt install p7zip
RUN echo OIVAS7572 | sudo -S mv download book.7z
RUN echo OIVAS7572 | sudo -S 7z e book.7z
RUN echo OIVAS7572 | sudo -S rm book.7z 
RUN echo OIVAS7572 | sudo -S apt-get install -y python3 python3-pip
RUN echo OIVAS7572 | sudo -S apt install python3-pip -y
COPY . .
#RUN echo OIVAS7572 | sudo -S apt install python3-venv -y
#RUN echo OIVAS7572 | sudo -S python3 -m venv venv
#RUN echo OIVAS7572 | sudo -S source ./venv/bin/activate
COPY requirements.txt .
RUN echo OIVAS7572 | sudo -S python3 -m pip install --no-cache-dir -r requirements.txt
CMD python3 run.py

