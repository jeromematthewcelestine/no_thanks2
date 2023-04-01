import random
from itertools import cycle
import datetime
from math import log, sqrt
import pickle
import no_thanks
from sqlalchemy import create_engine, Column, Integer, String, Float, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json
import os, psutil

DATABASE_URL = "postgresql://jeromew:sclub8@localhost/nothanks2"

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()

class BoardGameStateAction3p(Base):
    __tablename__ = "board_game_state_actions_3p"

    # id = Column(Integer, primary_key=True)
    # n_players = Column(Integer, nullable=False, primary_key=True)
    player = Column(Integer, nullable=False, primary_key=True)
    state = Column(String, nullable=False, primary_key=True)
    action = Column(Integer, nullable=False, primary_key=True)
    plays = Column(Integer, nullable=False)
    wins = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint('player', 'state', 'action'),
    )

class BoardGameStateAction4p(Base):
    __tablename__ = "board_game_state_actions_4p"

    # id = Column(Integer, primary_key=True)
    # n_players = Column(Integer, nullable=False, primary_key=True)
    player = Column(Integer, nullable=False, primary_key=True)
    state = Column(String, nullable=False, primary_key=True)
    action = Column(Integer, nullable=False, primary_key=True)
    plays = Column(Integer, nullable=False)
    wins = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint('player', 'state', 'action'),
    )

Base.metadata.create_all(engine)

class MCTSPlayer_db2():
    def __init__(self, n_players = 3, thinking_time = 1, min_card = 3, max_card = 35, start_coins = 11, n_omit_cards = 9, filepath = None):

        self.thinking_time = thinking_time
        self.max_moves = 200

        self.wins = {}
        self.plays = {}

        self.min_card = min_card
        self.max_card = max_card
        self.start_coins = start_coins
        self.n_omit_cards = n_omit_cards

        self.n_players = n_players

        if self.n_players == 3:
            self.table = BoardGameStateAction3p
        elif self.n_players == 4:
            self.table = BoardGameStateAction4p
        else:
            raise ValueError("n_players must be 3 or 4")


        if filepath:
            print("Loading from file...")
            self.load_from(filepath)

        self.C = 1.4

        process = psutil.Process(os.getpid())
        print("memory (in bytes): ", process.memory_info().rss)  # in bytes 

    def save_to_database(self):
        print("Saving to database...")
        for (player, state, action), plays in self.plays.items():
            wins = self.wins.get((player, state, action), 0)

            state_key = json.dumps(state)
            entry = session.query(self.table).filter_by(player=player, state=state_key, action=action).first()

            if entry:
                entry.plays = plays
                entry.wins = wins
            else:
                entry = self.table(player=player, state=state_key, action=action, plays=plays, wins=wins)
                session.add(entry)

        session.commit()

    def load_from_database(self):
        print("Loading from database...")

        # Query all rows in the BoardGameStateAction table
        all_entries = session.query(self.table).all()

        for entry in all_entries:
            # Load JSON string into a Python object
            state = json.loads(entry.state)
            coins, cards, details = state
            state = tuple(coins), tuple(map(tuple, cards)), tuple(details)

            # Create the key for the dictionaries
            key = (entry.player, state, entry.action)

            # Update the plays and wins dictionaries
            self.plays[key] = entry.plays
            self.wins[key] = entry.wins

        print("Done loading from database...")


    def clear_database(self):
        session.query(self.table).delete()
        session.commit()

    def get_values_from_database(self, player, state, action):
        state_key = json.dumps(state)
        entry = session.query(self.table).filter_by(player=player, state=state_key, action=action).first()
        if entry:
            return entry.plays, entry.wins
        else:
            return 0, 0

    def make_state_packed(self, coins, cards, card_in_play, coins_in_play, n_cards_in_deck, current_player):
        details = (card_in_play, coins_in_play, n_cards_in_deck, current_player)
        packed_state = tuple(coins), tuple(map(tuple, cards)), details
        return packed_state

        
    def get_action(self, state, legal_actions):
        self.max_depth = 0

        board = no_thanks.Board(self.n_players,
                                    min_card = self.min_card,
                                    max_card = self.max_card,
                                    start_coins = self.start_coins,
                                    n_omit_cards = self.n_omit_cards)
        
        player = state[2][3]

        if not legal_actions:
            return
        if len(legal_actions) == 1:
            return legal_actions[0]
        
        # if self.thinking_time > 0:
        #     games = 0
        #     calculation_delta = datetime.timedelta(seconds = self.thinking_time)
        #     begin = datetime.datetime.utcnow()
        #     while datetime.datetime.utcnow() - begin < calculation_delta:
        #         board = no_thanks.Board(self.n_players,
        #                                 min_card = self.min_card,
        #                                 max_card = self.max_card,
        #                                 start_coins = self.start_coins,
        #                                 n_omit_cards = self.n_omit_cards)
        #         self.run_simulation(state, board)
        #         games += 1
        
        plays = {}
        wins = {}
        for action in legal_actions:
            plays[action], wins[action] = self.get_values_from_database(player, state, action)

        if not all(plays[action] for action in legal_actions) and self.thinking_time > 0:
            print("Must train!")
            plays_dict, wins_dict = self.train_from_state(state, seconds = self.thinking_time)
            for action in legal_actions:
                plays[action] = plays_dict[player, state, action]
                wins[action] = wins_dict[player, state, action]
        else:
            print("No need to train!")

        max_value = -1
        for action in legal_actions:
            print("Plays: ", plays)
            print("Wins: ", wins)
            value = wins[action] / plays[action]
            if value > max_value:
                max_value = value
                chosen_action = action

        return chosen_action
    
    def train_from_state(self, state, seconds = 1):
        self.max_depth = 0
        games = 0

        plays_dict = {}
        wins_dict = {}

        calculation_time = datetime.timedelta(seconds = seconds)

        begin = datetime.datetime.utcnow()
        while datetime.datetime.utcnow() - begin < calculation_time:
            board = no_thanks.Board(self.n_players,
                                    min_card = self.min_card,
                                    max_card = self.max_card,
                                    start_coins = self.start_coins,
                                    n_omit_cards = self.n_omit_cards)
            plays_dict, wins_dict = self.run_simulation(state, board, plays_dict = plays_dict,
                                                        wins_dict = wins_dict)
            games += 1

        print("Games played: ", games)
        print("Maximum depth searched:", self.max_depth)

        return plays_dict, wins_dict

    def train(self, seconds = 1):
        self.max_depth = 0
        games = 0

        calculation_time = datetime.timedelta(seconds = seconds)

        begin = datetime.datetime.utcnow()
        while datetime.datetime.utcnow() - begin < calculation_time:
            board = no_thanks.Board(self.n_players,
                                    min_card = self.min_card,
                                    max_card = self.max_card,
                                    start_coins = self.start_coins,
                                    n_omit_cards = self.n_omit_cards)
            initial_state = board.pack_state(board.starting_state())
            self.run_simulation(initial_state, board)
            games += 1

        print("Games played: ", games)
        print("Maximum depth searched:", self.max_depth)

    def run_simulation(self, state, board, plays_dict = None, wins_dict = None):
        if plays_dict is not None:
            plays, wins = plays_dict, wins_dict
        else:
            plays, wins = self.plays, self.wins

        visited_actions = set()
        # states_copy = self.states[:]
        # state = states_copy[-1]
        player = board.current_player(state)
        assert 0 <= player < self.n_players, f"Invalid current_player value: {player}"

        phase = "selection"

        for t in range(1, self.max_moves + 1):
            # print(state)
            legal_actions = board.legal_actions(state)

            if all(plays.get((player, state, action)) for action in legal_actions):
                # if we have stats on all of the legal moves here, use them
                log_total = log(
                    sum(plays[(player, state, action)] for action in legal_actions))
                value, action = max(
                    ((wins[(player, state, action)] / plays[(player, state, action)]) + self.C *
                        sqrt(log_total / plays[(player, state, action)]), action)
                        for action in legal_actions
                )
            else:
                if phase == "selection":
                    phase = "expansion"
                # otherwise, just pick a random one
                action = random.choice(legal_actions)

            # states_copy.append(state)

            if phase == "expansion" and (player, state, action) not in plays:
                plays[(player, state, action)] = 0
                wins[(player, state, action)] = 0
                if t > self.max_depth:
                    self.max_depth = t
                phase = "end_expansion"

            if phase == "selection" or "phase" == "expansion":
                visited_actions.add((player, state, action))
            elif phase == "end_expansion":
                visited_actions.add((player, state, action))
                phase = "simulation"

            # move to next state
            state = board.next_state(state, action)

            player = board.current_player(state)
            winner = board.winner(state)
            if winner is not None:
                break

        phase = "backpropagation"
        for player, state, action in visited_actions:
            plays[(player, state, action)] += 1
            if player == winner:
                wins[(player, state, action)] += 1

        return plays, wins

        


if __name__ == "__main__":
    mcts_player = MCTSPlayer_db2(n_players = 4)
    mcts_player.load_from_database()
    mcts_player.train(seconds = 120)
    mcts_player.save_to_database()