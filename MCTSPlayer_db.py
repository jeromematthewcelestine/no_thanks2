import random
from itertools import cycle
import datetime
from math import log, sqrt
import pickle
import no_thanks
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os, psutil

class MCTSPlayer():
    def __init__(self, n_players = 3, thinking_time = 1, min_card = 3, max_card = 33, start_coins = 11, filepath = None):

        self.thinking_time = thinking_time
        self.max_moves = 200

        self.min_card = 3
        self.max_card = 33
        self.start_coins = 11
        self.n_players = n_players
        self.C = 1.4

        self.engine = create_engine("postgresql://jeromew:sclub8@localhost:5432/testdatabase")
        self.Session = sessionmaker(bind=self.engine)
        self.Base = declarative_base()

        class GameNode(self.Base):
            __tablename__ = 'GameNode'
            id = Column(Integer, primary_key=True)
            player = Column(Integer)
            n_cards_in_deck = Column(Integer)
            coins_in_play = Column(Integer)
            card_in_play = Column(Integer)
            coins0 = Column(Integer)
            coins1 = Column(Integer)
            coins2 = Column(Integer)
            cards0 = Column(String)
            cards1 = Column(String)
            cards2 = Column(String)
            action = Column(Integer)

        self.GameNode = GameNode
        self.Base.metadata.create_all(self.engine)
        print("done")

        session = self.Session()
        new_row = self.GameNode(player=33)
        session.add(new_row)
        session.commit()
        session.close()

        

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
            board = no_thanks.Board(self.n_players, min_card = self.min_card, max_card = self.max_card, start_coins = self.start_coins)
            initial_state = board.pack_state(board.starting_state())
            self.run_simulation(initial_state, board)
            games += 1

        print("Games played: ", games)
        print("Maximum depth searched:", self.max_depth)
        
    def get_action(self, state, legal_actions):
        self.max_depth = 0

        board = no_thanks.Board(self.n_players, min_card = self.min_card, max_card = self.max_card, start_coins = self.start_coins)
        
        player = state[2][3]
        # legal_actions = self.board.legal_actions(state)

        if not legal_actions:
            return
        if len(legal_actions) == 1:
            return legal_actions[0]
        
        if self.thinking_time > 0:
            games = 0
            calculation_delta = datetime.timedelta(seconds = self.thinking_time)
            begin = datetime.datetime.utcnow()
            while datetime.datetime.utcnow() - begin < calculation_delta:
                board = no_thanks.Board(self.n_players, min_card = self.min_card, max_card = self.max_card, start_coins = self.start_coins)
                self.run_simulation(state, board)
                games += 1

        max_percent_wins = 0
        max_action = None
        for action in legal_actions:
            plays = self.plays.get((player, state, action), 1)
            wins = self.wins.get((player, state, action), 0)
            percent_wins = 100 * wins / plays
            print(f'Action {action}: {percent_wins:.2f}% ({wins} / {plays}')
            if percent_wins > max_percent_wins:
                max_percent_wins = percent_wins
                max_action = action

        # for x in sorted(
        #     ((100 * self.wins.get((player, state, action), 0) / self.plays.get((player, state, action), 1), 
        #         self.wins.get((player, state, action), 0),
        #         self.plays.get((player, state, action), 0), action)
        #     for action in legal_actions),
        #     reverse=True
        # ):
        #     pass
        #     print("{3}: {0:.2f}% ({1} / {2})".format(*x))

        print("Player", player)
        print("Legal actions:", legal_actions)
        print("State: ", state)
        key = (player, state, 0)
        for i, key in enumerate(self.plays):
            print("Stored plays:", key, self.plays[key])
            if i > 10:
                break
        # if key in self.plays:
            # print("Stored plays:", self.plays[key])
        print("Stored plays:", self.plays.get((player, state, 0), 1))
        print("Stored wins:", self.wins.get((player, state, 0), 0))

        return action

    def run_simulation(self, state, board):
        plays, wins = self.plays, self.wins

        visited_actions = set()
        # states_copy = self.states[:]
        # state = states_copy[-1]
        player = board.current_player(state)

        expand = True

        session = self.Session()

        coins, cards, details = state
        card_in_play, coins_in_play, n_cards_in_deck, current_player = details
        

        for t in range(1, self.max_moves + 1):
            legal_actions = board.legal_actions(state)

            result = session.query(MyTable).filter_by(player=player, 
                n_cards_in_deck=n_cards_in_deck, coins_in_play=coins_in_play,
                card_in_play=card_in_play,
                coins0=coins[0], coins1=coins[1], coins2=coins[2],
                cards0=str(cards[0]), cards1=str(cards[1]), cards2=str(cards[2])).first()
            plays = 

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
                # otherwise, just pick a random one
                action = random.choice(legal_actions)

            # states_copy.append(state)

            if expand and (player, state, action) not in plays:
                expand = False
                plays[(player, state, action)] = 0
                wins[(player, state, action)] = 0
                if t > self.max_depth:
                    self.max_depth = t

            visited_actions.add((player, state, action))

            # move to next state
            state = board.next_state(state, action)

            player = board.current_player(state)
            winner = board.winner(state)
            if winner is not None:
                break


        for player, state, action in visited_actions:
            if (player, state, action) not in plays:
                continue
            plays[(player, state, action)] += 1
            if player == winner:
                wins[(player, state, action)] += 1

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