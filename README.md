# MAINTAINER [OIVAS7572](https://github.com/OIVAS7572)

[![Python](https://github.com/OIVAS7572/lichess-bot/actions/workflows/Python.yml/badge.svg)](https://github.com/OIVAS7572/lichess-bot/actions/workflows/Python.yml)
[![Docker](https://github.com/OIVAS7572/lichess-bot/actions/workflows/Docker.yml/badge.svg)](https://github.com/OIVAS7572/lichess-bot/actions/workflows/Docker.yml)

# lichess-bot

- A bridge between [Lichess API](https://lichess.org/api#tag/Bot) and bots.
- This bot is using Docker and concentrated on Heroku server.

## How to Install In Heroku

- Import or Fork this repository to your Github.
- Open config.yml and insert API accses token in to token option and commit changes.
- Install [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) and create app in Heroku.com.
**Do note that in certain operating systems Heroku CLI doesn't get added to path automatically. If that's the case you'll have to add heroku to your path manually.**
- Run this in cmd `heroku stack:set container -a appname` replace appname with your Heroku app's name.
- Connect app with Github and deploy app in Heroku.
- After deploying turn worker on in Resources menu in Heroku. 

## INFO 

ENGINE:
- Stockfish 13 SSE4.1 + POPCNT

OPENING BOOKS: 
- Goi5.1.bin
- Drawkiller_EloZoom_big.bin

**If you want to run bot localy on PC, read the [lichess-bot manual](https://github.com/ShailChoksi/lichess-bot#lichess-bot).**

### Acknowledgements
Credits to [ShailChoksi's lichess-bot](https://github.com/ShailChoksi/lichess-bot).