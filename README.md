# lichess-bot
A bridge between [Lichess API](https://lichess.org/api#tag/Chess-Bot) and bots.
This bot is using docker and concentrated on Heroku server.
## How to Install In Heroku
fork this repository to your Github repository.
Open config.yml and insert API accses token in to token option and commit changes
Install heroku cli and create app in Heroku.com.
Run this in cmd `heroku stack:set container -a appname` replace app name with your app's name.
Connect app with Github and deploy app in Heroku.
After deploying turn worker on in Resources menu in heroku. if it says add a procfile to your project to run it , reload the page once or twice
## INFO
ENGINE STOCKFISH 13 + additional alpha beta pruning and 
BOOK Aaricia_2012.bin
## NOTE 
this is the forked verison of https://github.com/OIVAS7572/lichess-bot but the difference is that , this repo has additional alpha beta pruning which helps the bot to search deeper
