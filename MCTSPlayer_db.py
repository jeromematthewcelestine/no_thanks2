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

class GameNode(Base):
    __tablename__ = 'GameNode'
    player = Column(Integer, primary_key=True)
    n_cards_in_deck = Column(Integer, primary_key=True)
    coins_in_play = Column(Integer, primary_key=True)
    card_in_play = Column(Integer, primary_key=True)
    coins0 = Column(Integer, primary_key=True)
    coins1 = Column(Integer, primary_key=True)
    coins2 = Column(Integer, primary_key=True)
    cards0 = Column(String, primary_key=True)
    cards1 = Column(String, primary_key=True)
    cards2 = Column(String, primary_key=True)
    action = Column(Integer, primary_key=True)
    plays = Column(Integer, nullable=False)
    wins = Column(Float, nullable=False)


self.Base.metadata.create_all(engine)

    session = self.Session()
    new_row = self.GameNode(player=33)
    session.add(new_row)
    session.commit()
    session.close()

class BoardGameStateAction(Base):
    __tablename__ = "board_game_state_actions"

    # id = Column(Integer, primary_key=True)
    player = Column(Integer, nullable=False, primary_key=True)
    state = Column(String, nullable=False, primary_key=True)
    action = Column(Integer, nullable=False, primary_key=True)
    plays = Column(Integer, nullable=False)
    wins = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint('player', 'state', 'action'),
    )

Base.metadata.create_all(engine)

class MCTSPlayer():
    def __init__(self, n_players = 3, thinking_time = 1, min_card = 3, max_card = 33, start_coins = 11):

        self.thinking_time = thinking_time
        self.max_moves = 200

        self.min_card = 3
        self.max_card = 33
        self.start_coins = 11
        self.n_players = n_players
        self.C = 1.4


    def get_state_action_entry(self, player, state, action):
        state_key = json.dumps(state)
        entry = session.query(BoardGameStateAction).filter_by(player=player, state=state_key, action=action).first()
        return entry

    def update_state_action_entry(self, player, state, action, plays, wins):
        # print("update_state_action_entry")
        state_key = json.dumps(state)
        entry = self.get_state_action_entry(player, state, action)
        if entry:
            entry.plays = plays
            entry.wins = wins
        else:
            entry = BoardGameStateAction(player=player, state=state_key, action=action, plays=plays, wins=wins)
            session.add(entry)
        session.commit()

    def get_plays_wins(self, player, state, action):
        entry = self.get_state_action_entry(player, state, action)
        if entry:
            return entry.plays, entry.wins
        else:
            return None
    
    def create_state_action_entry(self, player, state, action):
        state_key = json.dumps(state)
        entry = BoardGameStateAction(player=player, state=state_key, action=action, plays=0, wins=0)
        session.add(entry)
        session.commit()
        

    def make_state_packed(self, coins, cards, card_in_play, coins_in_play, n_cards_in_deck, current_player):
        details = (card_in_play, coins_in_play, n_cards_in_deck, current_player)
        packed_state = tuple(coins), tuple(map(tuple, cards)), details
        return packed_state

    def train(self, seconds = 1):
        self.max_depth = 0
        games = 0

        calculation_time = datetime.timedelta(seconds = seconds)

        begin = datetime.datetime.utcnow()
        while datetime.datetime.utcnow() - begin < calculation_time:
        # for i in range(1):
            board = no_thanks.Board(self.n_players, min_card = self.min_card, max_card = self.max_card, start_coins = self.start_coins)
            initial_state = board.pack_state(board.starting_state())
            self.run_simulation(initial_state, board)
            games += 1

        print("Games played: ", games)
        print("Maximum depth searched:", self.max_depth)
        
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

        if self.thinking_time > 0:
            games = 0
            calculation_delta = datetime.timedelta(seconds = self.thinking_time)
            begin = datetime.datetime.utcnow()
            while datetime.datetime.utcnow() - begin < calculation_delta:
                board = no_thanks.Board(self.n_players,
                                        min_card = self.min_card,
                                        max_card = self.max_card,
                                        start_coins = self.start_coins,
                                        n_omit_cards = self.n_omit_cards)
                self.run_simulation(state, board)
                games += 1

        percent_wins, action = max(
            (100 * self.get_plays_wins(player, state, action)[1] /
             self.get_plays_wins(player, state, action)[0],
             action)
            for action in legal_actions
        )

        for x in sorted(
            ((100 * self.get_plays_wins(player, state, action)[1] / self.get_plays_wins(player, state, action)[0], 
                self.get_plays_wins(player, state, action)[1],
                self.get_plays_wins(player, state, action)[0], action)
            for action in legal_actions),
            reverse=True
        ):
            pass
            print("{3}: {0:.2f}% ({1} / {2})".format(*x))

        print("Player", player)
        print("Legal actions:", legal_actions)
        print("State: ", state)

        return action

    def run_simulation(self, state, board):

        visited_actions = set()
        player = board.current_player(state)

        expand = True

        session = self.Session()

        coins, cards, details = state
        card_in_play, coins_in_play, n_cards_in_deck, current_player = details

        phase = "selection"

        for t in range(1, self.max_moves + 1):
            # print("Move", t)
            # print("Player", player)
            # print("State: ", state)

            legal_actions = board.legal_actions(state)

            plays_wins = {}
            for action in legal_actions:
                plays_wins[action] = self.get_plays_wins(player, state, action)
                # print("Action:", action, "plays:", plays_wins[action][0], "wins:", plays_wins[action][1])

            if all(plays_wins[x] for x in plays_wins) and all(plays_wins[x][0] for x in plays_wins): # x[0] is plays for this node
                print(plays_wins)
                # if we have stats on all of the legal moves here, use them
                log_total = log(sum(plays_wins[x][0] for x in plays_wins))

                chosen_value, chosen_action = max(
                    ((plays_wins[x][1] / plays_wins[x][0]) + self.C * sqrt(log_total / plays_wins[x][0]), action) 
                        for x in plays_wins
                )
            else:
                if phase == "selection":
                    phase = "expansion"
                # otherwise, just pick a random one
                chosen_action = random.choice(legal_actions)

            # states_copy.append(state)

            plays_wins = self.get_plays_wins(player, state, chosen_action)
            # print("phase", phase, "plays_wins", plays_wins)
            if phase == "expansion" and plays_wins is None: # check if we have stats on this state
                # print("here")
                self.create_state_action_entry(player, state, chosen_action)
                if t > self.max_depth:
                    self.max_depth = t
                phase = "end_expansion"

            if phase == "selection" or "phase" == "expansion":
                visited_actions.add((player, state, chosen_action))
            if phase == "end_expansion":
                visited_actions.add((player, state, chosen_action))
                phase = "simulation"

            # move to next state
            state = board.next_state(state, chosen_action)
            # print(state)

            player = board.current_player(state)
            winner = board.winner(state)
            if winner is not None:
                break

        for player, state, action in visited_actions:
            plays, wins = self.get_plays_wins(player, state, action)
            self.update_state_action_entry(player, state, action, plays + 1, wins + (player == winner))


    def write(self, filepath):
        output_object = {"wins": self.wins,
                      "plays": self.plays}
        with open(filepath, "wb") as output_file:
            pickle.dump(output_object, output_file)
    
    def load_from(self, filepath):
        with open(filepath, "rb") as input_file:
            input_object = pickle.load(input_file)
            self.plays = input_object["plays"]
            self.wins = input_object["wins"]


if __name__ == "__main__":
    mcts_player = MCTSPlayer()
    mcts_player.train(seconds = 10)