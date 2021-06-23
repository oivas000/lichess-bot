# MAINTAINER [OIVAS7572](https://github.com/OIVAS7572)

[![Python](https://github.com/OIVAS7572/lichess-bot/actions/workflows/Python.yml/badge.svg)](https://github.com/OIVAS7572/lichess-bot/actions/workflows/Python.yml)
[![Docker](https://github.com/OIVAS7572/lichess-bot/actions/workflows/Docker.yml/badge.svg)](https://github.com/OIVAS7572/lichess-bot/actions/workflows/Docker.yml)

# lichess-bot

- A bridge between [Lichess API](https://lichess.org/api#tag/Bot) and bots.
- This bot is using Docker and concentrated on Heroku server.

## How to Install In Heroku

- [Fork](https://github.com/OIVAS7572/lichess-bot/fork) this repository.
- Edit only your token in the `config.yml` file over [here](/config.yml#L1).
- Install [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) and Create a [new heroku app](https://dashboard.heroku.com/new-app).
**Do note that in certain operating systems Heroku CLI doesn't get added to path automatically. If that's the case you'll have to add heroku to your path manually.**
- Run this in cmd `heroku stack:set container -a appname` replace appname with your Heroku app's name.
- Go to the `Deploy` tab and click `Connect to GitHub`.
- Click on `search` and then select your fork of this repository.
- Click `Deploy`.
- Once it has been deployed, go to `Resources` tab on heroku and enable `worker (python3 lichess-bot.py -u)` dynos. (Do note that if you don't see any dynos in the `Resources` tab, then you must wait for about 5 minutes and then refresh your heroku page.)
- You're now connected to lichess and awaiting challenges! Your bot is up and ready!

## INFO 

ENGINE:
- Stockfish 13 SSE4.1 + POPCNT

OPENING BOOKS: 
- Goi5.1.bin
- Drawkiller_EloZoom_big.bin

**If you want to run bot localy on PC, read the [lichess-bot manual](https://github.com/ShailChoksi/lichess-bot#lichess-bot).**

### Acknowledgements
Credits to [ShailChoksi's lichess-bot](https://github.com/ShailChoksi/lichess-bot).
