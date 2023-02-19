from __future__ import annotations
import os
import chess.engine
import chess.polyglot
import chess.syzygy
import chess.gaviota
import subprocess
import logging
import time
import random
from collections import Counter
from contextlib import contextmanager
import config
import model
import lichess
from config import Configuration
from typing import Dict, Any, List, Optional, Union, Tuple, Generator, Callable, Type
OPTIONS_TYPE = Dict[str, Any]
MOVE_INFO_TYPE = Dict[str, Any]
COMMANDS_TYPE = List[str]
LICHESS_EGTB_MOVE = Dict[str, Any]
CHESSDB_EGTB_MOVE = Dict[str, Any]
MOVE = Union[chess.engine.PlayResult, List[chess.Move]]

logger = logging.getLogger(__name__)

out_of_online_opening_book_moves: Counter[str] = Counter()


@contextmanager
def create_engine(engine_config: config.Configuration) -> Generator[EngineWrapper, None, None]:
    cfg = engine_config.engine
    engine_path = os.path.join(cfg.dir, cfg.name)
    engine_type = cfg.protocol
    commands = [engine_path]
    if cfg.engine_options:
        for k, v in cfg.engine_options.items():
            commands.append(f"--{k}={v}")

    stderr = None if cfg.silence_stderr else subprocess.DEVNULL

    Engine: Union[Type[UCIEngine], Type[XBoardEngine], Type[MinimalEngine]]
    if engine_type == "xboard":
        Engine = XBoardEngine
    elif engine_type == "uci":
        Engine = UCIEngine
    elif engine_type == "homemade":
        Engine = getHomemadeEngine(cfg.name)
    else:
        raise ValueError(
            f"    Invalid engine type: {engine_type}. Expected xboard, uci, or homemade.")
    options = remove_managed_options(cfg.lookup(f"{engine_type}_options") or config.Configuration({}))
    logger.debug(f"Starting engine: {commands}")
    engine = Engine(commands, options, stderr, cfg.draw_or_resign, cwd=cfg.working_dir)
    try:
        yield engine
    finally:
        engine.stop()
        engine.ping()
        engine.quit()


def remove_managed_options(config: config.Configuration) -> OPTIONS_TYPE:
    def is_managed(key: str) -> bool:
        return chess.engine.Option(key, "", None, None, None, None).is_managed()

    return {name: value for (name, value) in config.items() if not is_managed(name)}


def translate_termination(game: model.Game, board: chess.Board) -> str:
    winner_color = game.state.get("winner", "")
    termination: Optional[str] = game.state.get("status")

    if termination == model.Termination.MATE:
        return f"{winner_color.title()} mates"
    elif termination == model.Termination.TIMEOUT:
        return "Time forfeiture"
    elif termination == model.Termination.RESIGN:
        resigner = "black" if winner_color == "white" else "white"
        return f"{resigner.title()} resigns"
    elif termination == model.Termination.ABORT:
        return "Game aborted"
    elif termination == model.Termination.DRAW:
        if board.is_fifty_moves():
            return "50-move rule"
        elif board.is_repetition():
            return "Threefold repetition"
        else:
            return "Draw by agreement"
    elif termination:
        return termination
    else:
        return ""


PONDERPV_CHARACTERS = 6  # The length of ", PV: ".


class EngineWrapper:
    def __init__(self, options: OPTIONS_TYPE, draw_or_resign: config.Configuration) -> None:
        self.engine: Union[chess.engine.SimpleEngine, FillerEngine]
        self.scores: List[chess.engine.PovScore] = []
        self.draw_or_resign = draw_or_resign
        self.go_commands = config.Configuration(options.pop("go_commands", {}) or {})
        self.move_commentary: List[MOVE_INFO_TYPE] = []
        self.comment_start_index = -1

    def play_move(self,
                  board: chess.Board,
                  game: model.Game,
                  li: lichess.Lichess,
                  start_time: int,
                  move_overhead: int,
                  can_ponder: bool,
                  is_correspondence: bool,
                  correspondence_move_time: int,
                  engine_cfg: config.Configuration) -> None:
        polyglot_cfg = engine_cfg.polyglot
        online_moves_cfg = engine_cfg.online_moves
        draw_or_resign_cfg = engine_cfg.draw_or_resign
        lichess_bot_tbs = engine_cfg.lichess_bot_tbs

        best_move: MOVE
        best_move = get_book_move(board, game, polyglot_cfg)

        if best_move.move is None:
            best_move = get_egtb_move(board,
                                      game,
                                      lichess_bot_tbs,
                                      draw_or_resign_cfg)

        if not isinstance(best_move, list) and best_move.move is None:
            best_move = get_online_move(li,
                                        board,
                                        game,
                                        online_moves_cfg,
                                        draw_or_resign_cfg)

        if isinstance(best_move, list) or best_move.move is None:
            draw_offered = check_for_draw_offer(game)

            if len(board.move_stack) < 2:
                best_move = choose_first_move(self,
                                              board,
                                              game,
                                              draw_offered,
                                              best_move)
            elif is_correspondence:
                best_move = choose_move_time(self,
                                             board,
                                             game,
                                             correspondence_move_time,
                                             start_time,
                                             move_overhead,
                                             can_ponder,
                                             draw_offered,
                                             best_move)
            else:
                best_move = choose_move(self,
                                        board,
                                        game,
                                        can_ponder,
                                        draw_offered,
                                        start_time,
                                        move_overhead,
                                        best_move)
        else:
            self.stop()

        self.add_comment(best_move, board)
        self.print_stats()
        if best_move.resigned and len(board.move_stack) >= 2:
            li.resign(game.id)
        else:
            li.make_move(game.id, best_move)

    def search_for(self, board: chess.Board, movetime: int, ponder: bool, draw_offered: bool,
                   root_moves: MOVE) -> chess.engine.PlayResult:
        return self.search(board, chess.engine.Limit(time=movetime / 1000), ponder, draw_offered, root_moves)

    def first_search(self, board: chess.Board, movetime: int, draw_offered: bool,
                     root_moves: MOVE) -> chess.engine.PlayResult:
        # No pondering after the first move since a different clock is used afterwards.
        return self.search_for(board, movetime, False, draw_offered, root_moves)

    def search_with_ponder(self, board: chess.Board, wtime: int, btime: int, winc: int, binc: int, ponder: bool,
                           draw_offered: bool, root_moves: MOVE) -> chess.engine.PlayResult:
        time_limit = chess.engine.Limit(white_clock=wtime / 1000,
                                        black_clock=btime / 1000,
                                        white_inc=winc / 1000,
                                        black_inc=binc / 1000)
        return self.search(board, time_limit, ponder, draw_offered, root_moves)

    def add_go_commands(self, time_limit: chess.engine.Limit) -> chess.engine.Limit:
        movetime = self.go_commands.movetime
        if movetime is not None:
            movetime_sec = float(movetime) / 1000
            if time_limit.time is None or time_limit.time > movetime_sec:
                time_limit.time = movetime_sec
        time_limit.depth = self.go_commands.depth
        time_limit.nodes = self.go_commands.nodes
        return time_limit

    def offer_draw_or_resign(self, result: chess.engine.PlayResult, board: chess.Board) -> chess.engine.PlayResult:
        def actual(score: chess.engine.PovScore) -> int:
            return score.relative.score(mate_score=40000)

        can_offer_draw = self.draw_or_resign.offer_draw_enabled
        draw_offer_moves = self.draw_or_resign.offer_draw_moves
        draw_score_range: int = self.draw_or_resign.offer_draw_score
        draw_max_piece_count = self.draw_or_resign.offer_draw_pieces
        pieces_on_board = chess.popcount(board.occupied)
        enough_pieces_captured = pieces_on_board <= draw_max_piece_count
        if can_offer_draw and len(self.scores) >= draw_offer_moves and enough_pieces_captured:
            scores = self.scores[-draw_offer_moves:]

            def score_near_draw(score: chess.engine.PovScore) -> bool:
                return abs(actual(score)) <= draw_score_range
            if len(scores) == len(list(filter(score_near_draw, scores))):
                result.draw_offered = True

        resign_enabled = self.draw_or_resign.resign_enabled
        min_moves_for_resign = self.draw_or_resign.resign_moves
        resign_score: int = self.draw_or_resign.resign_score
        if resign_enabled and len(self.scores) >= min_moves_for_resign:
            scores = self.scores[-min_moves_for_resign:]

            def score_near_loss(score: chess.engine.PovScore) -> bool:
                return actual(score) <= resign_score
            if len(scores) == len(list(filter(score_near_loss, scores))):
                result.resigned = True
        return result

    def search(self, board: chess.Board, time_limit: chess.engine.Limit, ponder: bool, draw_offered: bool,
               root_moves: MOVE) -> chess.engine.PlayResult:
        time_limit = self.add_go_commands(time_limit)
        result: chess.engine.PlayResult
        result = self.engine.play(board,
                                  time_limit,
                                  info=chess.engine.INFO_ALL,
                                  ponder=ponder,
                                  draw_offered=draw_offered,
                                  root_moves=root_moves if isinstance(root_moves, list) else None)
        # Use null_score to have no effect on draw/resign decisions
        null_score = chess.engine.PovScore(chess.engine.Mate(1), board.turn)
        self.scores.append(result.info.get("score", null_score))
        result = self.offer_draw_or_resign(result, board)
        return result

    def comment_index(self, move_stack_index: int) -> int:
        if self.comment_start_index < 0:
            return -1
        else:
            return move_stack_index - self.comment_start_index

    def comment_for_board_index(self, index: int) -> MOVE_INFO_TYPE:
        no_info: MOVE_INFO_TYPE = {}
        comment_index = self.comment_index(index)
        if comment_index < 0 or comment_index % 2 != 0:
            return no_info

        try:
            return self.move_commentary[comment_index // 2]
        except IndexError:
            return no_info

    def add_comment(self, move: chess.engine.PlayResult, board: chess.Board) -> None:
        if self.comment_start_index < 0:
            self.comment_start_index = len(board.move_stack)
        move_info: MOVE_INFO_TYPE = dict(move.info.copy()) if move.info else {}
        if "pv" in move_info:
            move_info["ponderpv"] = board.variation_san(move.info["pv"])
        if "refutation" in move_info:
            move_info["refutation"] = board.variation_san(move.info["refutation"])
        if "currmove" in move_info:
            move_info["currmove"] = board.san(move.info["currmove"])
        self.move_commentary.append(move_info)

    def print_stats(self) -> None:
        for line in self.get_stats():
            logger.info(line)

    def readable_score(self, relative_score: chess.engine.PovScore) -> str:
        score = relative_score.relative
        cp_score = score.score()
        if cp_score is None:
            str_score = f"#{score.mate()}"
        else:
            str_score = str(round(cp_score / 100, 2))
        return str_score

    def readable_wdl(self, wdl: chess.engine.PovWdl) -> str:
        wdl_percentage = round(wdl.relative.expectation() * 100, 1)
        return f"{wdl_percentage}%"

    def readable_number(self, number: int) -> str:
        if number >= 1e9:
            return f"{round(number / 1e9, 1)}B"
        elif number >= 1e6:
            return f"{round(number / 1e6, 1)}M"
        elif number >= 1e3:
            return f"{round(number / 1e3, 1)}K"
        return str(number)

    def get_stats(self, for_chat: bool = False) -> List[str]:
        can_index = self.move_commentary and self.move_commentary[-1]
        info: MOVE_INFO_TYPE = self.move_commentary[-1].copy() if can_index else {}

        def to_readable_value(stat: str, info: MOVE_INFO_TYPE) -> str:
            readable: Dict[str, Callable[[Any], str]] = {"score": self.readable_score, "wdl": self.readable_wdl,
                                                         "hashfull": lambda x: f"{round(x / 10, 1)}%",
                                                         "nodes": self.readable_number,
                                                         "nps": lambda x: f"{self.readable_number(x)}nps",
                                                         "tbhits": self.readable_number,
                                                         "cpuload": lambda x: f"{round(x / 10, 1)}%"}

            def identity(x: Any) -> str:
                return str(x)

            return str(readable.get(stat, identity)(info[stat]))

        def to_readable_key(stat: str) -> str:
            readable = {"wdl": "winrate", "ponderpv": "PV", "nps": "speed", "score": "evaluation"}
            stat = readable.get(stat, stat)
            return stat.title()

        stats = ["score", "wdl", "depth", "nodes", "nps", "ponderpv"]
        if for_chat and "ponderpv" in info:
            bot_stats = [f"{to_readable_key(stat)}: {to_readable_value(stat, info)}"
                         for stat in stats if stat in info and stat != "ponderpv"]
            len_bot_stats = len(", ".join(bot_stats)) + PONDERPV_CHARACTERS
            ponder_pv = info["ponderpv"].split()
            try:
                while len(" ".join(ponder_pv)) + len_bot_stats > lichess.MAX_CHAT_MESSAGE_LEN:
                    ponder_pv.pop()
                if ponder_pv[-1].endswith("."):
                    ponder_pv.pop()
                info["ponderpv"] = " ".join(ponder_pv)
            except IndexError:
                pass
            if not info["ponderpv"]:
                info.pop("ponderpv")
        return [f"{to_readable_key(stat)}: {to_readable_value(stat, info)}" for stat in stats if stat in info]

    def get_opponent_info(self, game: model.Game) -> None:
        pass

    def name(self) -> str:
        engine_info: Dict[str, str] = dict(self.engine.id)
        name: str = engine_info["name"]
        return name

    def report_game_result(self, game: model.Game, board: chess.Board) -> None:
        pass

    def stop(self) -> None:
        pass

    def get_pid(self) -> str:
        pid = "?"
        if self.engine.transport is not None:
            pid = str(self.engine.transport.get_pid())
        return pid

    def ping(self) -> None:
        self.engine.ping()

    def quit(self) -> None:
        self.engine.quit()
        self.engine.close()


class UCIEngine(EngineWrapper):
    def __init__(self, commands: COMMANDS_TYPE, options: OPTIONS_TYPE, stderr: Optional[int],
                 draw_or_resign: config.Configuration, **popen_args: str) -> None:
        super().__init__(options, draw_or_resign)
        self.engine = chess.engine.SimpleEngine.popen_uci(commands, timeout=10., debug=False, setpgrp=False, stderr=stderr,
                                                          **popen_args)
        self.engine.configure(options)

    def stop(self) -> None:
        self.engine.protocol.send_line("stop")

    def get_opponent_info(self, game: model.Game) -> None:
        name = game.opponent.name
        if (name and isinstance(self.engine.protocol, chess.engine.UciProtocol) and
                "UCI_Opponent" in self.engine.protocol.config):
            rating = game.opponent.rating or "none"
            title = game.opponent.title or "none"
            player_type = "computer" if title == "BOT" else "human"
            self.engine.configure({"UCI_Opponent": f"{title} {rating} {player_type} {name}"})

    def report_game_result(self, game: model.Game, board: chess.Board) -> None:
        if isinstance(self.engine.protocol, chess.engine.UciProtocol):
            self.engine.protocol._position(board)


class XBoardEngine(EngineWrapper):
    def __init__(self, commands: COMMANDS_TYPE, options: OPTIONS_TYPE, stderr: Optional[int],
                 draw_or_resign: config.Configuration, **popen_args: str) -> None:
        super().__init__(options, draw_or_resign)
        self.engine = chess.engine.SimpleEngine.popen_xboard(commands, timeout=10., debug=False, setpgrp=False,
                                                             stderr=stderr, **popen_args)
        egt_paths = options.pop("egtpath", {}) or {}
        features = self.engine.protocol.features if isinstance(self.engine.protocol, chess.engine.XBoardProtocol) else {}
        egt_features = features.get("egt", "")
        if isinstance(egt_features, str):
            egt_types_from_engine = egt_features.split(",")
            egt_type: str
            for egt_type in filter(None, egt_types_from_engine):
                if egt_type in egt_paths:
                    options[f"egtpath {egt_type}"] = egt_paths[egt_type]
                else:
                    logger.debug(f"No paths found for egt type: {egt_type}.")
        self.engine.configure(options)

    def report_game_result(self, game: model.Game, board: chess.Board) -> None:
        # Send final moves, if any, to engine
        if isinstance(self.engine.protocol, chess.engine.XBoardProtocol):
            self.engine.protocol._new(board, None, {})

        endgame_message = translate_termination(game, board)
        if endgame_message:
            endgame_message = " {" + endgame_message + "}"

        self.engine.protocol.send_line(f"result {game.result()}{endgame_message}")

    def stop(self) -> None:
        self.engine.protocol.send_line("?")

    def get_opponent_info(self, game: model.Game) -> None:
        if (game.opponent.name and isinstance(self.engine.protocol, chess.engine.XBoardProtocol) and
                self.engine.protocol.features.get("name", True)):
            title = f"{game.opponent.title} " if game.opponent.title else ""
            self.engine.protocol.send_line(f"name {title}{game.opponent.name}")
        if game.me.rating and game.opponent.rating:
            self.engine.protocol.send_line(f"rating {game.me.rating} {game.opponent.rating}")
        if game.opponent.title == "BOT":
            self.engine.protocol.send_line("computer")


class MinimalEngine(EngineWrapper):
    """
    Subclass this to prevent a few random errors

    Even though MinimalEngine extends EngineWrapper,
    you don't have to actually wrap an engine.

    At minimum, just implement `search`,
    however you can also change other methods like
    `notify`, `first_search`, `get_time_control`, etc.
    """
    def __init__(self, commands: COMMANDS_TYPE, options: OPTIONS_TYPE, stderr: Optional[int],
                 draw_or_resign: Configuration, name: Optional[str] = None, **popen_args: str) -> None:
        super().__init__(options, draw_or_resign)

        self.engine_name = self.__class__.__name__ if name is None else name

        self.engine = FillerEngine(self, name=self.engine_name)

    def get_pid(self) -> str:
        return "?"

    def search(self, board: chess.Board, time_limit: chess.engine.Limit, ponder: bool, draw_offered: bool,
               root_moves: MOVE) -> chess.engine.PlayResult:
        """
        The method to be implemented in your homemade engine

        NOTE: This method must return an instance of "chess.engine.PlayResult"
        """
        raise NotImplementedError("The search method is not implemented")

    def notify(self, method_name: str, *args: Any, **kwargs: Any) -> None:
        """
        The EngineWrapper class sometimes calls methods on "self.engine".
        "self.engine" is a filler property that notifies <self>
        whenever an attribute is called.

        Nothing happens unless the main engine does something.

        Simply put, the following code is equivalent
        self.engine.<method_name>(<*args>, <**kwargs>)
        self.notify(<method_name>, <*args>, <**kwargs>)
        """
        pass


class FillerEngine:
    """
    Not meant to be an actual engine.

    This is only used to provide the property "self.engine"
    in "MinimalEngine" which extends "EngineWrapper"
    """
    def __init__(self, main_engine: MinimalEngine, name: str = "") -> None:
        self.id: Dict[str, str] = {
            "name": name
        }
        self.name = name
        self.main_engine = main_engine

    def __getattr__(self, method_name: str) -> Any:
        main_engine = self.main_engine

        def method(*args: Any, **kwargs: Any) -> Any:
            nonlocal main_engine
            nonlocal method_name
            return main_engine.notify(method_name, *args, **kwargs)

        return method


def getHomemadeEngine(name: str) -> Type[MinimalEngine]:
    import strategies
    engine: Type[MinimalEngine] = getattr(strategies, name)
    return engine


def choose_move_time(engine: EngineWrapper, board: chess.Board, game: model.Game, search_time: int, start_time: int,
                     move_overhead: int, ponder: bool, draw_offered: bool, root_moves: MOVE) -> chess.engine.PlayResult:
    pre_move_time = int((time.perf_counter_ns() - start_time) / 1e6)
    overhead = pre_move_time + move_overhead
    wb = "w" if board.turn == chess.WHITE else "b"
    clock_time = max(0, game.state[f"{wb}time"] - overhead)
    search_time = min(search_time, clock_time)
    logger.info(f"Searching for time {search_time} for game {game.id}")
    return engine.search_for(board, search_time, ponder, draw_offered, root_moves)


def choose_first_move(engine: EngineWrapper, board: chess.Board, game: model.Game,
                      draw_offered: bool, root_moves: MOVE) -> chess.engine.PlayResult:
    # need to hardcode first movetime (10000 ms) since Lichess has 30 sec limit.
    search_time = 10000
    logger.info(f"Searching for time {search_time} for game {game.id}")
    return engine.first_search(board, search_time, draw_offered, root_moves)


def choose_move(engine: EngineWrapper, board: chess.Board, game: model.Game, ponder: bool, draw_offered: bool,
                start_time: int, move_overhead: int, root_moves: MOVE) -> chess.engine.PlayResult:
    pre_move_time = int((time.perf_counter_ns() - start_time) / 1e6)
    overhead = pre_move_time + move_overhead
    wb = "w" if board.turn == chess.WHITE else "b"
    game.state[f"{wb}time"] = max(0, game.state[f"{wb}time"] - overhead)
    logger.info("Searching for wtime {wtime} btime {btime}".format_map(game.state) + f" for game {game.id}")
    return engine.search_with_ponder(board,
                                     game.state["wtime"],
                                     game.state["btime"],
                                     game.state["winc"],
                                     game.state["binc"],
                                     ponder,
                                     draw_offered,
                                     root_moves)


def check_for_draw_offer(game: model.Game) -> bool:
    return game.state.get(f"{game.opponent_color[0]}draw", False)


def get_book_move(board: chess.Board, game: model.Game,
                  polyglot_cfg: config.Configuration) -> chess.engine.PlayResult:
    no_book_move = chess.engine.PlayResult(None, None)
    use_book = polyglot_cfg.enabled
    max_game_length = polyglot_cfg.max_depth * 2 - 1
    if not use_book or len(board.move_stack) > max_game_length:
        return no_book_move

    variant = "standard" if board.uci_variant == "chess" else str(board.uci_variant)
    config.change_value_to_list(polyglot_cfg.config, "book", key=variant)
    books = polyglot_cfg.book.lookup(variant)

    for book in books:
        with chess.polyglot.open_reader(book) as reader:
            try:
                selection = polyglot_cfg.selection
                min_weight = polyglot_cfg.min_weight
                if selection == "weighted_random":
                    move = reader.weighted_choice(board).move
                elif selection == "uniform_random":
                    move = reader.choice(board, minimum_weight=min_weight).move
                elif selection == "best_move":
                    move = reader.find(board, minimum_weight=min_weight).move
            except IndexError:
                # python-chess raises "IndexError" if no entries found
                move = None

        if move is not None:
            logger.info(f"Got move {move} from book {book} for game {game.id}")
            return chess.engine.PlayResult(move, None)

    return no_book_move


def get_online_move(li: lichess.Lichess, board: chess.Board, game: model.Game, online_moves_cfg: config.Configuration,
                    draw_or_resign_cfg: config.Configuration) -> Union[chess.engine.PlayResult, List[chess.Move]]:
    online_egtb_cfg = online_moves_cfg.online_egtb
    chessdb_cfg = online_moves_cfg.chessdb_book
    lichess_cloud_cfg = online_moves_cfg.lichess_cloud_analysis
    max_out_of_book_moves = online_moves_cfg.max_out_of_book_moves
    offer_draw = False
    resign = False
    comment: Optional[chess.engine.InfoDict] = None
    best_move, wdl = get_online_egtb_move(li, board, game, online_egtb_cfg)
    if best_move is not None:
        can_offer_draw = draw_or_resign_cfg.offer_draw_enabled
        offer_draw_for_zero = draw_or_resign_cfg.offer_draw_for_egtb_zero
        if can_offer_draw and offer_draw_for_zero and wdl == 0:
            offer_draw = True

        can_resign = draw_or_resign_cfg.resign_enabled
        resign_on_egtb_loss = draw_or_resign_cfg.resign_for_egtb_minus_two
        if can_resign and resign_on_egtb_loss and wdl == -2:
            resign = True

        wdl_to_score = {2: 9900, 1: 500, 0: 0, -1: -500, -2: -9900}
        comment = {"score": chess.engine.PovScore(chess.engine.Cp(wdl_to_score[wdl]), board.turn)}
    elif out_of_online_opening_book_moves[game.id] < max_out_of_book_moves:
        best_move, comment = get_chessdb_move(li, board, game, chessdb_cfg)

    if best_move is None and out_of_online_opening_book_moves[game.id] < max_out_of_book_moves:
        best_move, comment = get_lichess_cloud_move(li, board, game, lichess_cloud_cfg)

    if best_move:
        if isinstance(best_move, str):
            return chess.engine.PlayResult(chess.Move.from_uci(best_move),
                                           None,
                                           comment,
                                           draw_offered=offer_draw,
                                           resigned=resign)
        return [chess.Move.from_uci(move) for move in best_move]
    out_of_online_opening_book_moves[game.id] += 1
    used_opening_books = chessdb_cfg.enabled or lichess_cloud_cfg.enabled
    if out_of_online_opening_book_moves[game.id] == max_out_of_book_moves and used_opening_books:
        logger.info(f"Will stop using online opening books for game {game.id}.")
    return chess.engine.PlayResult(None, None)


def get_chessdb_move(li: lichess.Lichess, board: chess.Board, game: model.Game,
                     chessdb_cfg: config.Configuration) -> Tuple[Optional[str], Optional[chess.engine.InfoDict]]:
    wb = "w" if board.turn == chess.WHITE else "b"
    use_chessdb = chessdb_cfg.enabled
    time_left = game.state[f"{wb}time"]
    min_time = chessdb_cfg.min_time * 1000
    if not use_chessdb or time_left < min_time or board.uci_variant != "chess":
        return None, None

    move = None
    comment: chess.engine.InfoDict = {}
    site = "https://www.chessdb.cn/cdb.php"
    quality = chessdb_cfg.move_quality
    action = {"best": "querypv",
              "good": "querybest",
              "all": "query"}
    try:
        params = {"action": action[quality],
                  "board": board.fen(),
                  "json": 1}
        data = li.online_book_get(site, params=params)
        if data["status"] == "ok":
            if quality == "best":
                depth = data["depth"]
                if depth >= chessdb_cfg.min_depth:
                    score = data["score"]
                    move = data["pv"][0]
                    comment["score"] = chess.engine.PovScore(chess.engine.Cp(score), board.turn)
                    comment["depth"] = data["depth"]
                    comment["pv"] = list(map(chess.Move.from_uci, data["pv"]))
                    logger.info(f"Got move {move} from chessdb.cn (depth: {depth}, score: {score}) for game {game.id}")
            else:
                move = data["move"]
                logger.info(f"Got move {move} from chessdb.cn for game {game.id}")

        if chessdb_cfg.contribute:
            params["action"] = "queue"
            li.online_book_get(site, params=params)
    except Exception:
        pass

    return move, comment


def get_lichess_cloud_move(li: lichess.Lichess, board: chess.Board, game: model.Game,
                           lichess_cloud_cfg: config.Configuration) -> Tuple[Optional[str], Optional[chess.engine.InfoDict]]:
    wb = "w" if board.turn == chess.WHITE else "b"
    time_left = game.state[f"{wb}time"]
    min_time = lichess_cloud_cfg.min_time * 1000
    use_lichess_cloud = lichess_cloud_cfg.enabled
    if not use_lichess_cloud or time_left < min_time:
        return None, None

    move = None
    comment: chess.engine.InfoDict = {}

    quality = lichess_cloud_cfg.move_quality
    multipv = 1 if quality == "best" else 5
    variant = "standard" if board.uci_variant == "chess" else board.uci_variant

    try:
        data = li.online_book_get("https://lichess.org/api/cloud-eval",
                                  params={"fen": board.fen(),
                                          "multiPv": multipv,
                                          "variant": variant})
        if "error" not in data:
            depth = data["depth"]
            knodes = data["knodes"]
            min_depth = lichess_cloud_cfg.min_depth
            min_knodes = lichess_cloud_cfg.min_knodes
            if depth >= min_depth and knodes >= min_knodes:
                if quality == "best":
                    pv = data["pvs"][0]
                else:
                    best_eval = data["pvs"][0]["cp"]
                    pvs = data["pvs"]
                    max_difference = lichess_cloud_cfg.max_score_difference
                    if wb == "w":
                        pvs = list(filter(lambda pv: pv["cp"] >= best_eval - max_difference, pvs))
                    else:
                        pvs = list(filter(lambda pv: pv["cp"] <= best_eval + max_difference, pvs))
                    pv = random.choice(pvs)
                move = pv["moves"].split()[0]
                score = pv["cp"] if wb == "w" else -pv["cp"]
                comment["score"] = chess.engine.PovScore(chess.engine.Cp(score), board.turn)
                comment["depth"] = data["depth"]
                comment["nodes"] = data["knodes"] * 1000
                comment["pv"] = list(map(chess.Move.from_uci, pv["moves"].split()))
                logger.info(f"Got move {move} from lichess cloud analysis (depth: {depth}, score: {score}, knodes: {knodes})"
                            f" for game {game.id}")
    except Exception:
        pass

    return move, comment


def get_online_egtb_move(li: lichess.Lichess, board: chess.Board, game: model.Game,
                         online_egtb_cfg: config.Configuration) -> Tuple[Union[str, List[str], None], int]:
    use_online_egtb = online_egtb_cfg.enabled
    wb = "w" if board.turn == chess.WHITE else "b"
    pieces = chess.popcount(board.occupied)
    source = online_egtb_cfg.source
    minimum_time = online_egtb_cfg.min_time * 1000
    if (not use_online_egtb
            or game.state[f"{wb}time"] < minimum_time
            or board.uci_variant not in ["chess", "antichess", "atomic"]
            and source == "lichess"
            or board.uci_variant != "chess"
            and source == "chessdb"
            or pieces > online_egtb_cfg.max_pieces
            or board.castling_rights):

        return None, -3

    quality = online_egtb_cfg.move_quality
    variant = "standard" if board.uci_variant == "chess" else str(board.uci_variant)

    try:
        if source == "lichess":
            return get_lichess_egtb_move(li, game, board, quality, variant)
        elif source == "chessdb":
            return get_chessdb_egtb_move(li, game, board, quality)
    except Exception:
        pass

    return None, -3


def get_egtb_move(board: chess.Board, game: model.Game, lichess_bot_tbs: config.Configuration,
                  draw_or_resign_cfg: config.Configuration) -> Union[chess.engine.PlayResult, List[chess.Move]]:
    best_move, wdl = get_syzygy(board, game, lichess_bot_tbs.syzygy)
    if best_move is None:
        best_move, wdl = get_gaviota(board, game, lichess_bot_tbs.gaviota)
    if best_move:
        can_offer_draw = draw_or_resign_cfg.offer_draw_enabled
        offer_draw_for_zero = draw_or_resign_cfg.offer_draw_for_egtb_zero
        offer_draw = bool(can_offer_draw and offer_draw_for_zero and wdl == 0)

        can_resign = draw_or_resign_cfg.resign_enabled
        resign_on_egtb_loss = draw_or_resign_cfg.resign_for_egtb_minus_two
        resign = bool(can_resign and resign_on_egtb_loss and wdl == -2)
        wdl_to_score = {2: 9900, 1: 500, 0: 0, -1: -500, -2: -9900}
        comment: chess.engine.InfoDict = {"score": chess.engine.PovScore(chess.engine.Cp(wdl_to_score[wdl]), board.turn)}
        if isinstance(best_move, chess.Move):
            return chess.engine.PlayResult(best_move, None, comment, draw_offered=offer_draw, resigned=resign)
        return best_move
    return chess.engine.PlayResult(None, None)


def get_lichess_egtb_move(li: lichess.Lichess, game: model.Game, board: chess.Board, quality: str,
                          variant: str) -> Tuple[Union[str, List[str], None], int]:
    name_to_wld = {"loss": -2,
                   "maybe-loss": -1,
                   "blessed-loss": -1,
                   "draw": 0,
                   "cursed-win": 1,
                   "maybe-win": 1,
                   "win": 2}
    pieces = chess.popcount(board.occupied)
    max_pieces = 7 if board.uci_variant == "chess" else 6
    if pieces <= max_pieces:
        data = li.online_book_get(f"http://tablebase.lichess.ovh/{variant}",
                                  params={"fen": board.fen()})
        if quality == "best":
            move = data["moves"][0]["uci"]
            wdl = name_to_wld[data["moves"][0]["category"]] * -1
            dtz = data["moves"][0]["dtz"] * -1
            dtm = data["moves"][0]["dtm"]
            if dtm:
                dtm *= -1
            logger.info(f"Got move {move} from tablebase.lichess.ovh (wdl: {wdl}, dtz: {dtz}, dtm: {dtm}) for game {game.id}")
        elif quality == "suggest":
            best_wdl = name_to_wld[data["moves"][0]["category"]]

            def good_enough(possible_move: LICHESS_EGTB_MOVE) -> bool:
                return name_to_wld[possible_move["category"]] == best_wdl

            possible_moves = list(filter(good_enough, data["moves"]))
            if len(possible_moves) > 1:
                move = [move["uci"] for move in possible_moves]
                wdl = best_wdl * -1
                logger.info(f"Suggesting moves from tablebase.lichess.ovh (wdl: {wdl}) for game {game.id}")
            else:
                best_move = possible_moves[0]
                move = best_move["uci"]
                wdl = name_to_wld[best_move["category"]] * -1
                dtz = best_move["dtz"] * -1
                dtm = best_move["dtm"]
                if dtm:
                    dtm *= -1
                logger.info(f"Got move {move} from tablebase.lichess.ovh (wdl: {wdl}, dtz: {dtz}, dtm: {dtm})"
                            f" for game {game.id}")
        else:
            best_wdl = name_to_wld[data["moves"][0]["category"]]

            def good_enough(possible_move: LICHESS_EGTB_MOVE) -> bool:
                return name_to_wld[possible_move["category"]] == best_wdl
            possible_moves = list(filter(good_enough, data["moves"]))
            random_move = random.choice(possible_moves)
            move = random_move["uci"]
            wdl = name_to_wld[random_move["category"]] * -1
            dtz = random_move["dtz"] * -1
            dtm = random_move["dtm"]
            if dtm:
                dtm *= -1
            logger.info(f"Got move {move} from tablebase.lichess.ovh (wdl: {wdl}, dtz: {dtz}, dtm: {dtm}) for game {game.id}")

        return move, wdl
    return None, -3


def get_chessdb_egtb_move(li: lichess.Lichess, game: model.Game, board: chess.Board,
                          quality: str) -> Tuple[Union[str, List[str], None], int]:
    def score_to_wdl(score: int) -> int:
        return piecewise_function([(-20001, 2),
                                   (-1, -1),
                                   (0, 0),
                                   (20000, 1)], 2, score)

    def score_to_dtz(score: int) -> int:
        return piecewise_function([(-20001, -30000 - score),
                                   (-1, -20000 - score),
                                   (0, 0),
                                   (20000, 20000 - score)], 30000 - score, score)

    action = "querypv" if quality == "best" else "queryall"
    data = li.online_book_get("https://www.chessdb.cn/cdb.php",
                              params={"action": action, "board": board.fen(), "json": 1})
    if data["status"] == "ok":
        if quality == "best":
            score = data["score"]
            move = data["pv"][0]
            wdl = score_to_wdl(score)
            dtz = score_to_dtz(score)
            logger.info(f"Got move {move} from chessdb.cn (wdl: {wdl}, dtz: {dtz}) for game {game.id}")
        elif quality == "suggest":
            best_wdl = score_to_wdl(data["moves"][0]["score"])

            def good_enough(move: CHESSDB_EGTB_MOVE) -> bool:
                return score_to_wdl(move["score"]) == best_wdl

            possible_moves = list(filter(good_enough, data["moves"]))
            if len(possible_moves) > 1:
                wdl = score_to_wdl(possible_moves[0]["score"])
                move = [move["uci"] for move in possible_moves]
                logger.info(f"Suggesting moves from from chessdb.cn (wdl: {wdl}) for game {game.id}")
            else:
                best_move = possible_moves[0]
                score = best_move["score"]
                move = best_move["uci"]
                wdl = score_to_wdl(score)
                dtz = score_to_dtz(score)
                logger.info(f"Got move {move} from chessdb.cn (wdl: {wdl}, dtz: {dtz}) for game {game.id}")
        else:
            best_wdl = score_to_wdl(data["moves"][0]["score"])

            def good_enough(move: CHESSDB_EGTB_MOVE) -> bool:
                return score_to_wdl(move["score"]) == best_wdl
            possible_moves = list(filter(good_enough, data["moves"]))
            random_move = random.choice(possible_moves)
            score = random_move["score"]
            move = random_move["uci"]
            wdl = score_to_wdl(score)
            dtz = score_to_dtz(score)
            logger.info(f"Got move {move} from chessdb.cn (wdl: {wdl}, dtz: {dtz}) for game {game.id}")

        return move, wdl
    return None, -3


def get_syzygy(board: chess.Board, game: model.Game,
               syzygy_cfg: config.Configuration) -> Tuple[Union[chess.Move, List[chess.Move], None], int]:
    if (not syzygy_cfg.enabled
            or chess.popcount(board.occupied) > syzygy_cfg.max_pieces
            or board.uci_variant not in ["chess", "antichess", "atomic"]):
        return None, -3
    move: Union[chess.Move, List[chess.Move]]
    move_quality = syzygy_cfg.move_quality
    with chess.syzygy.open_tablebase(syzygy_cfg.paths[0]) as tablebase:
        for path in syzygy_cfg.paths[1:]:
            tablebase.add_directory(path)

        try:
            moves = score_syzygy_moves(board, dtz_scorer, tablebase)

            best_wdl = max(map(dtz_to_wdl, moves.values()))
            good_moves = [(move, dtz) for move, dtz in moves.items() if dtz_to_wdl(dtz) == best_wdl]
            if move_quality == "good":
                move, dtz = random.choice(good_moves)
                logger.info(f"Got move {move.uci()} from syzygy (wdl: {best_wdl}, dtz: {dtz}) for game {game.id}")
                return move, best_wdl
            elif move_quality == "suggest" and len(good_moves) > 1:
                move = [chess_move for chess_move, dtz in good_moves]
                logger.info(f"Suggesting moves from syzygy (wdl: {best_wdl}) for game {game.id}")
                return move, best_wdl
            else:
                best_dtz = min([dtz for chess_move, dtz in good_moves])
                best_moves = [chess_move for chess_move, dtz in good_moves if dtz == best_dtz]
                move = random.choice(best_moves)
                logger.info(f"Got move {move.uci()} from syzygy (wdl: {best_wdl}, dtz: {best_dtz}) for game {game.id}")
                return move, best_wdl
        except KeyError:
            # Attempt to only get the WDL score. It returns a move of quality="good", even if quality is set to "best".
            try:
                moves = score_syzygy_moves(board, lambda tablebase, b: -tablebase.probe_wdl(b), tablebase)
                best_wdl = max(moves.values())
                good_chess_moves = [chess_move for chess_move, wdl in moves.items() if wdl == best_wdl]
                logger.debug("Found a move using 'move_quality'='good'. We didn't find an '.rtbz' file for this endgame."
                             if move_quality == "best" else "")
                if move_quality == "suggest" and len(good_chess_moves) > 1:
                    move = good_chess_moves
                    logger.info(f"Suggesting moves from syzygy (wdl: {best_wdl}) for game {game.id}")
                else:
                    move = random.choice(good_chess_moves)
                    logger.info(f"Got move {move.uci()} from syzygy (wdl: {best_wdl}) for game {game.id}")
                return move, best_wdl
            except KeyError:
                return None, -3


def dtz_scorer(tablebase: chess.syzygy.Tablebase, board: chess.Board) -> int:
    dtz = -tablebase.probe_dtz(board)
    return dtz + (1 if dtz > 0 else -1) * board.halfmove_clock * (0 if dtz == 0 else 1)


def dtz_to_wdl(dtz: int) -> int:
    return piecewise_function([(-100, -1), (-1, -2), (0, 0), (99, 2)], 1, dtz)


def get_gaviota(board: chess.Board, game: model.Game,
                gaviota_cfg: config.Configuration) -> Tuple[Union[chess.Move, List[chess.Move], None], int]:
    if (not gaviota_cfg.enabled
            or chess.popcount(board.occupied) > gaviota_cfg.max_pieces
            or board.uci_variant != "chess"):
        return None, -3
    move: Union[chess.Move, List[chess.Move]]
    move_quality = gaviota_cfg.move_quality
    # Since gaviota TBs use dtm and not dtz, we have to put a limit where after it the position are considered to have
    # a syzygy wdl=1/-1, so the positions are draws under the 50 move rule. We use min_dtm_to_consider_as_wdl_1 as a
    # second limit, because if a position has 5 pieces and dtm=110 it may take 98 half-moves, to go down to 4 pieces and
    # another 12 to mate, so this position has a syzygy wdl=2/-2. To be safe, the first limit is 100 moves, which
    # guarantees that all moves have a syzygy wdl=2/-2. Setting min_dtm_to_consider_as_wdl_1 to 100 will disable it
    # because dtm >= dtz, so if abs(dtm) < 100 => abs(dtz) < 100, so wdl=2/-2.
    min_dtm_to_consider_as_wdl_1 = gaviota_cfg.min_dtm_to_consider_as_wdl_1
    with chess.gaviota.open_tablebase(gaviota_cfg.paths[0]) as tablebase:
        for path in gaviota_cfg.paths[1:]:
            tablebase.add_directory(path)

        try:
            moves = score_gaviota_moves(board, dtm_scorer, tablebase)

            best_wdl = max(map(dtm_to_gaviota_wdl, moves.values()))
            good_moves = [(move, dtm) for move, dtm in moves.items() if dtm_to_gaviota_wdl(dtm) == best_wdl]
            best_dtm = min([dtm for move, dtm in good_moves])

            pseudo_wdl = dtm_to_wdl(best_dtm, min_dtm_to_consider_as_wdl_1)
            if move_quality == "good":
                best_moves = good_enough_gaviota_moves(good_moves, best_dtm, min_dtm_to_consider_as_wdl_1)
                move, dtm = random.choice(best_moves)
                logger.info(f"Got move {move.uci()} from gaviota (pseudo wdl: {pseudo_wdl}, dtm: {dtm}) for game {game.id}")
            elif move_quality == "suggest":
                best_moves = good_enough_gaviota_moves(good_moves, best_dtm, min_dtm_to_consider_as_wdl_1)
                if len(best_moves) > 1:
                    move = [chess_move for chess_move, dtm in best_moves]
                    logger.info(f"Suggesting moves from gaviota (pseudo wdl: {pseudo_wdl}) for game {game.id}")
                else:
                    move, dtm = random.choice(best_moves)
                    logger.info(f"Got move {move.uci()} from gaviota (pseudo wdl: {pseudo_wdl}, dtm: {dtm})"
                                f" for game {game.id}")
            else:
                # There can be multiple moves with the same dtm.
                best_moves = [(move, dtm) for move, dtm in good_moves if dtm == best_dtm]
                move, dtm = random.choice(best_moves)
                logger.info(f"Got move {move.uci()} from gaviota (pseudo wdl: {pseudo_wdl}, dtm: {dtm}) for game {game.id}")
            return move, pseudo_wdl
        except KeyError:
            return None, -3


def dtm_scorer(tablebase: Union[chess.gaviota.NativeTablebase, chess.gaviota.PythonTablebase], board: chess.Board) -> int:
    dtm = -tablebase.probe_dtm(board)
    return dtm + (1 if dtm > 0 else -1) * board.halfmove_clock * (0 if dtm == 0 else 1)


def dtm_to_gaviota_wdl(dtm: int) -> int:
    return piecewise_function([(-1, -1), (0, 0)], 1, dtm)


def dtm_to_wdl(dtm: int, min_dtm_to_consider_as_wdl_1: int) -> int:
    # We use 100 and not min_dtm_to_consider_as_wdl_1, because we want to play it safe and not resign in a
    # position where dtz=-102 (only if resign_for_egtb_minus_two is enabled).
    return piecewise_function([(-100, -1), (-1, -2), (0, 0), (min_dtm_to_consider_as_wdl_1 - 1, 2)], 1, dtm)


def good_enough_gaviota_moves(good_moves: List[Tuple[chess.Move, int]], best_dtm: int,
                              min_dtm_to_consider_as_wdl_1: int) -> List[Tuple[chess.Move, int]]:
    if best_dtm < 100:
        # If a move had wdl=2 and dtz=98, but halfmove_clock is 4 then the real wdl=1 and dtz=102, so we
        # want to avoid these positions, if there is a move where even when we add the halfmove_clock the
        # dtz is still <100.
        return [(move, dtm) for move, dtm in good_moves if dtm < 100]
    elif best_dtm < min_dtm_to_consider_as_wdl_1:
        # If a move had wdl=2 and dtz=98, but halfmove_clock is 4 then the real wdl=1 and dtz=102, so we
        # want to avoid these positions, if there is a move where even when we add the halfmove_clock the
        # dtz is still <100.
        return [(move, dtm) for move, dtm in good_moves if dtm < min_dtm_to_consider_as_wdl_1]
    elif best_dtm <= -min_dtm_to_consider_as_wdl_1:
        # If a move had wdl=-2 and dtz=-98, but halfmove_clock is 4 then the real wdl=-1 and dtz=-102, so we
        # want to only choose between the moves where the real wdl=-1.
        return [(move, dtm) for move, dtm in good_moves if dtm <= -min_dtm_to_consider_as_wdl_1]
    elif best_dtm <= -100:
        # If a move had wdl=-2 and dtz=-98, but halfmove_clock is 4 then the real wdl=-1 and dtz=-102, so we
        # want to only choose between the moves where the real wdl=-1.
        return [(move, dtm) for move, dtm in good_moves if dtm <= -100]
    else:
        return good_moves


def piecewise_function(range_definitions: List[Tuple[int, int]], last_value: int, position: int) -> int:
    """ Returns a value according to a position argument
    This function is meant to replace if-elif-else blocks that turn ranges into discrete values. For
    example,

    piecewise_function([(-20001, 2), (-1, -1), (0, 0), (20000, 1)], 2, score)

    is equivalent to:

    if score < -20000:
        return -2
    elif score < 0:
        return -1
    elif score == 0:
        return 0
    elif score <= 20000:
        return 1
    else:
        return 2

    Note: We use -20001 and not -20000, because we use <= and not <.

    Arguments:
    range_definitions:
        A list of tuples with the first element being the inclusive right border of region and the second
        element being the associated value. An element of this list (a, b) corresponds to
        if x <= a:
            return b
        where x is the value of the position argument. This argument should be sorted by the first element
        for correct operation.
    last_value:
        If the position argument is greater than all of the borders in the range_definition argument,
        return this value.
    position:
        The value that will be compared to the first element of the range_definitions tuples.
    """
    for border, value in range_definitions:
        if position <= border:
            return value
    return last_value


def score_syzygy_moves(board: chess.Board, scorer: Callable[[chess.syzygy.Tablebase, chess.Board], int],
                       tablebase: chess.syzygy.Tablebase) -> Dict[chess.Move, int]:
    moves = {}
    for move in board.legal_moves:
        board_copy = board.copy()
        board_copy.push(move)
        moves[move] = scorer(tablebase, board_copy)
    return moves


def score_gaviota_moves(board: chess.Board,
                        scorer: Callable[[Union[chess.gaviota.NativeTablebase, chess.gaviota.PythonTablebase],
                                          chess.Board], int],
                        tablebase: Union[chess.gaviota.NativeTablebase, chess.gaviota.PythonTablebase]
                        ) -> Dict[chess.Move, int]:
    moves = {}
    for move in board.legal_moves:
        board_copy = board.copy()
        board_copy.push(move)
        moves[move] = scorer(tablebase, board_copy)
    return moves
