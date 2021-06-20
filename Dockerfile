FROM debian:10.9-slim
MAINTAINER SAVIO PRINCE
RUN echo OIVAS7572
CMD echo OIVAS7572
COPY . .
RUN apt-get update
RUN apt-get -y install sudo
RUN useradd OIVAS7572 && echo "OIVAS7572:OIVAS7572" | chpasswd && adduser OIVAS7572 sudo
USER OIVAS7572
ADD /engine/ .

# If you are using docker and you want to run any other commands use "RUN echo OIVAS7572 | sudo -S" before.

RUN echo OIVAS7572 | sudo -S apt-get install -y wget
RUN echo OIVAS7572 | sudo -S apt install p7zip-full -y
RUN echo OIVAS7572 | sudo -S wget -U "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36" --no-check-certificate "https://gitlab.com/OIVAS7572/Goi5.1.bin/-/raw/master/Goi5.1.bin.7z" -O Goi5.1.bin.7z
RUN echo OIVAS7572 | sudo -S 7z e Goi5.1.bin.7z
RUN echo OIVAS7572 | sudo -S rm Goi5.1.bin.7z
RUN echo OIVAS7572 | sudo -S apt-get install -y python3 python3-pip
RUN echo OIVAS7572 | sudo -S apt install python3-pip -y
COPY requirements.txt .
RUN echo OIVAS7572 | sudo -S python3 -m pip install --no-cache-dir -r requirements.txt

RUN echo OIVAS7572 | sudo -S chmod +x stockfishmodern
#                 Engine name is here ^
#RUN echo OIVAS7572 | sudo -S apt-get install -y libopenblas-dev
# If you want to use Lc0 uncomment (remove the hash tag '#') the 29th line.

CMD python3 run.py