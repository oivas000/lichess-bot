# MAINTAINER [OIVAS7572](https://github.com/OIVAS7572)

[![Python application](https://github.com/TheYoBots/lichess-bot-1/actions/workflows/python-app.yml/badge.svg)](https://github.com/TheYoBots/lichess-bot-1/actions/workflows/python-app.yml)
[![Docker Image CI](https://github.com/TheYoBots/lichess-bot-1/actions/workflows/docker-image.yml/badge.svg)](https://github.com/TheYoBots/lichess-bot-1/actions/workflows/docker-image.yml)


# lichess-bot

- A bridge between [Lichess API](https://lichess.org/api#tag/Chess-Bot) and bots.
- This bot is using docker and concentrated on Heroku server.

## How to Install In Heroku

- Import or Fork this repository to your Github repository.
- Open config.yml and insert API accses token in to token option and commit changes
- Install heroku cli and create app in Heroku.com.
- Run this in cmd `heroku stack:set container -a appname` replace app name with your app's name.
- Connect app with Github and deploy app in Heroku.
- After deploying turn worker on in Resources menu in heroku. 

## INFO

- ENGINE STOCKFISH 13 SSE4.1 + POPCNT
- BOOK Aaricia_2012.bin
