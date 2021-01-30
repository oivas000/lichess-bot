import os

def lichess():
    program = "python3"
    arguments = ["lichess-bot.py"]
    print(os.execvp(program, (program,) +  tuple(arguments)))
lichess()    