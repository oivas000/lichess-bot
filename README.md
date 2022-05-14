# lichess-bot
**MAINTAINER [OIVAS7572](https://github.com/OIVAS7572)**

[![Python Build](https://github.com/OIVAS7572/lichess-bot/actions/workflows/python-build.yml/badge.svg)](https://github.com/OIVAS7572/lichess-bot/actions/workflows/python-build.yml)
[![Python Test](https://github.com/OIVAS7572/lichess-bot/actions/workflows/python-test.yml/badge.svg)](https://github.com/OIVAS7572/lichess-bot/actions/workflows/python-test.yml)
[![Docker](https://github.com/OIVAS7572/lichess-bot/actions/workflows/Docker.yml/badge.svg)](https://github.com/OIVAS7572/lichess-bot/actions/workflows/Docker.yml)

# lichess-bot
- A bridge between [Lichess API](https://lichess.org/api#tag/Bot) and bots.
- This bot is made with Python and it is running using Docker container and is concentrated on heroku.

## How to Install on Heroku
- Import or [Fork](https://github.com/OIVAS7572/lichess-bot/fork) this repository to your Github.
- Open the `Settings` tab on heroku and insert your [API access token with `bot:play` scopes enabled](https://lichess.org/account/oauth/token/create?scopes[]=bot:play&description=Lichess+Bot+Token) in the `Config vars` field in the format `LICHESS_BOT_TOKEN:API-ACCESS-TOKEN`, where you replace `API-ACCESS-TOKEN` with your API Access token.
- Install [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) and [create a new app](https://dashboard.heroku.com/new-app) in Heroku. <br/>
**Do note that in certain operating systems Heroku CLI doesn't get added to path automatically. If that's the case you'll have to add heroku to your path manually.**
- Run this command in cmd or powershell `heroku stack:set container -a appname`, where `appname` is replaced with your Heroku app's name.
- [Deploy your repository to heroku](https://devcenter.heroku.com/articles/git)
- After deploying wait for about 5 minutes till the build finishes and then in the `Resources` tab in heroku turn `worker` dynos. If you do not see any option to enable any dynos, then you'll have to wait for about 5 minutes and then refresh your page on heroku.

**You're now connected to lichess and awaiting challenges! Your bot is up and ready!**

## Bot Information
Engine:
- [Stockfish 15](https://stockfishchess.org/blog/2022/stockfish-15/) with the default NNUE.

Opening Books: 
- [Goi5.1.bin](https://gitlab.com/OIVAS7572/Goi5.1.bin/-/raw/master/Goi5.1.bin.7z)
- [Drawkiller_EloZoom_big.bin](engines/books/Drawkiller_EloZoom_big.bin)

**Keep you Forks or Imports Up-to-Date & Check the other Branches in this Repository**

**If you would like to run bot locally on PC, read the [lichess-bot manual](https://github.com/ShailChoksi/lichess-bot#how-to-install).**

## How to change the engine used?

**Changing the engine to an engine of your preference is simple. Just follow the following steps:**

- Firstly, you have to remove the engine used. To do this you need delete the file named `stockfish15` in the [`engines/` folder](/engines).
- Then you need to download the binary of the chess engine you want to used and into your GitHub repository, Go to the [`engines/` folder](/engines), Click on `Add files` and then click `Upload files` and upload the binary of the chess engine you have downloaded. <br/>
Note: Make sure you download a linux binary that is supported by heroku (by default Stockfish is used, and the default engine name is `stockfish15`).
- Then change the name of engine in [6th line of config.yml](/config.yml#L6) and [14th line of Dockerfile](/Dockerfile#L14) to your binary file's name.

## Acknowledgements
Credits to [ShailChoksi's lichess-bot](https://github.com/ShailChoksi/lichess-bot).

## License
This code is primarily taken from [lichess-bot by ShailChoksi](https://github.com/ShailChoksi/lichess-bot) and is hence run under the AGPLv3 License (or later at your option). Check out the [LICENSE file](/LICENSE) for full text.