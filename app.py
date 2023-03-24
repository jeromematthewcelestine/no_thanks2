from flask import Flask, render_template, redirect, url_for, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import json
import random

import sys
sys.path.append("..")
sys.path.append("../mcts_no_thanks")
from MCTSPlayer import MCTSPlayer



mcts_player_3p = MCTSPlayer(thinking_time = 1, filepath = "../mcts_no_thanks/mcts_classic_3p_20230221_05.model")
print(mcts_player_3p.n_players)
print(mcts_player_3p.C)
print(len(mcts_player_3p.plays))

app = Flask(__name__)
app.secret_key = 'md3yTHuujFsD7En72cQP'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nothanks.db'
db = SQLAlchemy(app)

migrate = Migrate(app, db)

def ai01_get_action(legal_actions):
    return random.choice(legal_actions)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.Text)
    username = db.Column(db.Text)
    status = db.Column(db.Text)

def initialize_game(player_name = "Bob", num_opponents = 3):

    deck = list(range(3, 33))
    random.shuffle(deck)

    start_chips = 11
    omit_cards = 9

    table_chips = 0
    omitted_cards = [deck.pop() for _ in range(omit_cards)]
    print("len omitted_cards", len(omitted_cards))
    table_card = deck.pop()
    
    human_player = {"id": 0, "type": "human", "name": player_name, "cards": [], "chips": start_chips}
    players = [human_player]
    for i in range(num_opponents):
        ai_player = {"id": i+1, "type": "ai01", "name": f"Player {i+1}", "cards": [], "chips": start_chips}
        players.append(ai_player)

    game_state = {
        "is_game_over": False,
        "active_player_id": 0,
        "deck": deck,
        "table_card": table_card,
        "table_chips": table_chips,
        "players": players,
        "messages": ["Game started."]
    }
    game = Game(state = json.dumps(game_state),
                username = "jeromew",
                status = "active")
    db.session.add(game)
    db.session.commit()
    return game.id


# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         name = request.form['name']
#         session['name'] = name
#         return redirect(url_for('list_games'))
#     else:
#         return '''
#             <form method="post">
#                 <label for="name">Choose a nickname:</label>
#                 <input type="text" name="name" id="name">
#                 <input type="submit" value="Submit">
#             </form>
#         '''

# Define the logout page
# @app.route('/logout')
# def logout():
#     session.pop('name', None)
#     return redirect(url_for('login'))

@app.route('/list-games')
def list_games():
    games = Game.query.all()
    return render_template('list_games.html', games=games)

@app.route('/')
def home():
    # return ""

    if "game_id" in session:
        print("game_id in session")
        print("session game_id", session["game_id"])
        return redirect(url_for('game_template', game_id=session['game_id']))
    else:
        print("game id not in session")
        return redirect(url_for('new_game'))
    
@app.route('/new-game')
def new_game():
    return render_template('new_game.html')

@app.route('/create-game/', methods = ['POST'])
def create_game():
    print("create game")
    print(request.json)
    game_id = initialize_game(player_name = request.json["player_name"],
                              num_opponents = request.json["num_ai_players"])
    session['game_id'] = game_id
    return jsonify({"success": True, "game_id": game_id})
    # return redirect(url_for('game_template', game_id=game_id))

@app.route('/game/<game_id>')
def game_template(game_id):
    return render_template('game.html', game_id = game_id)

@app.route('/game/<game_id>/resign', methods = ['POST'])
def game_resign(game_id):
    game = Game.query.filter(Game.id == game_id).first()
    game_state = json.loads(game.state)

    if game.status == "active" and not game_state["is_game_over"]:
        game_state["is_game_over"] = True
        game_state["messages"].append("Resigned")
        session.pop("game_id", None)

        game.state = json.dumps(game_state)
        game.status = "resigned"
        
        db.session.commit()
        success = True
    else:
        success = False

    return jsonify({"success": success, "game_state": game_state})

@app.route('/game-state/<game_id>')
def game_state(game_id):
    print(f"/game-state/{game_id}")
    game = Game.query.filter(Game.id == game_id).first()
    # if not game.username == session['name']:
        # return jsonify({'message': 'Not authorized.'}), 400

    game_state = json.loads(game.state)
    print(game_state)
    response = {
        "game_state": game_state
    }
    print(jsonify(response))
    return jsonify(response)
    # return render_template('game.html', game_id = game_id)



@app.route('/game-state/<game_id>/player/<player_id>')
def game_state_for_player(game_id, player_id):
    print(f"/game-state/{game_id}/player/{player_id}")

    game = Game.query.filter(Game.id == game_id).first()
    game_state = json.loads(game.state)
    active_player_id = game_state["active_player_id"]

    if int(player_id) == int(active_player_id):
        legal_actions = get_legal_actions(game_state, active_player_id)
    else:
        legal_actions = None
    
    response = {
        "game_state": game_state,
        "legal_actions": legal_actions
    }
    
    return jsonify(response)


@app.route('/game/<game_id>/next', methods = ['GET'])
def get_next(game_id):
    print(f"/game/{game_id}/next")
    game = Game.query.filter(Game.id == game_id).first()
    game_state = json.loads(game.state)

    active_player_id = game_state["active_player_id"]

    if game_state["players"][active_player_id]["type"] == "human":
        return jsonify({ "success": False, "game_state": game_state })
    if game_state["is_game_over"]:
        return jsonify({ "success": False, "game_state": game_state })
    
    legal_actions = get_legal_actions(game_state, active_player_id)

    if (len(game_state["players"]) == 3):
        mcts_state = create_mcts_state(game_state, active_player_id)
        mcts_legal_actions = create_mcts_legal_actions(legal_actions)
        mcts_action = mcts_player_3p.get_action(mcts_state, mcts_legal_actions)
        mcts_to_action = {0: "TAKE_CARD", 1: "PAY_CHIP"}
        action = mcts_to_action[mcts_action]
    else:
        action = random.choice(["TAKE_CARD", "PAY_CHIP"])

    game_state = do_action(game_state, action)

    game.state = json.dumps(game_state)
    db.session.commit()

    print(game_state)

    return jsonify({ "success": True, "game_state": game_state })


@app.route('/game/<game_id>/action', methods = ['POST'])
def game_action(game_id):
    print(f"/game/{game_id}/action")
    game = Game.query.filter(Game.id == game_id).first()
    game_state = json.loads(game.state)

    active_player_id = game_state["active_player_id"]
    is_game_over = game_state["is_game_over"]

    action_player_id = request.json["action_player_id"]
    action_type = request.json["action_type"]

    legal_actions = get_legal_actions(game_state, active_player_id)
    # print("legal: ", legal_actions)

    if (action_player_id == active_player_id and 
        action_type in legal_actions and 
        not is_game_over):

        game_state = do_action(game_state, action_type)

        # game_state = do_computer_moves(game_state)

        game.state = json.dumps(game_state)
        db.session.commit()
        response = { "success": True, "game_state": game_state }
        
    else:
        response = { "success": False, "game_state": game_state }

    print(response)

    return jsonify(response)


def get_legal_actions(game_state, active_player_id):
    active_player = game_state["players"][active_player_id]
    legal_actions = ["TAKE_CARD"]
    if active_player["chips"] > 0:
        legal_actions.append("PAY_CHIP")
    return legal_actions

def check_winner(game_state):
    winner = None
    highest_score = -100

    for i, player in enumerate(game_state["players"]):
        score = calculate_score(player)
        if score > highest_score:
            winner = i

    return winner

def calculate_scores_and_winners(game_state):
    min_score = 1000
    winners = []
    min_scorers = []
    for player in game_state["players"]:
        score = calculate_score(player)
        player["score"] = score
        if score < min_score:
            min_score = score
            winners = [player["id"]]
        elif score == min_score:
            winners.append(player["id"])
    game_state["winners"] = winners

    for player in game_state["players"]:
        if player["id"] in winners:
            player["final_status"] = "winner"
        else:
            player["final_status"] = "loser"

    return game_state

def calculate_score(player):
    cards_sorted = set(player["cards"])
    card_sum = 0
    for card in cards_sorted:
        if card - 1 in cards_sorted:
            pass
        else:
            card_sum += card
    score = card_sum - player["chips"]

    return score

def do_action(game_state, action_type):
    active_player_id = game_state["active_player_id"]

    if action_type == "PAY_CHIP":
        message = "Pay chip successful"
        game_state["players"][active_player_id]["chips"] -= 1
        game_state["table_chips"] += 1
        game_state["players"][active_player_id]["last_card"] = None

        game_state["active_player_id"] = (active_player_id + 1) % len(game_state["players"])

        game_state["messages"].append(f"Player {active_player_id} paid a chip.")


    elif action_type == "TAKE_CARD":
        game_state["players"][active_player_id]["chips"] += game_state["table_chips"]
        game_state["table_chips"] = 0
        game_state["players"][active_player_id]["cards"].append(game_state["table_card"])
        game_state["players"][active_player_id]["cards"].sort()
        game_state["players"][active_player_id]["last_card"] = game_state["table_card"]

        game_state["messages"].append(f"Player {active_player_id} took the {game_state['table_card']} card.")
        
        # Check if deck is empty. If empty, game over.
        if game_state["deck"]:
            game_state["table_card"] = game_state["deck"].pop()
            active_player_id = (active_player_id + 1) % len(game_state["players"])
            game_state["active_player_id"] = active_player_id

        else:
            game_state["table_card"] = None
            game_state["is_game_over"] = True
            game_state = calculate_scores_and_winners(game_state)

    return game_state


def create_mcts_state(game_state, active_player_id):
    coins = [player["chips"] for player in game_state["players"]]
    cards = [player["cards"] for player in game_state["players"]]
    card_in_play = game_state["table_card"]
    coins_in_play = game_state["table_chips"]
    n_cards_in_deck = len(game_state["deck"])
    current_player = active_player_id

    mcts_packed = mcts_player.make_state_packed(coins, cards, card_in_play, coins_in_play, n_cards_in_deck, current_player)
    return mcts_packed
    # mcst_player.make_state_packed(coins, cards, card_in_play, coins_in_play, n_cards_in_deck, current_player)

def create_mcts_legal_actions(legal_actions):
    action_to_mcts = {"TAKE_CARD": 0, "PAY_CHIP": 1}
    mcts_to_action = {0: "TAKE_CARD", 1: "PAY_CHIP"}
    return [action_to_mcts[action] for action in legal_actions]

def do_computer_moves(game_state):
    while True:
        # loop through computer players
        active_player_id = game_state["active_player_id"]
        # if human player's turn, break
        if game_state["players"][active_player_id]["type"] == "human":
            break
        if game_state["is_game_over"]:
            break

        legal_actions = get_legal_actions(game_state, active_player_id)

        mcts_state = create_mcts_state(game_state, active_player_id)
        mcts_legal_actions = create_mcts_legal_actions(legal_actions)
        mcts_action = mcts_player.get_action(mcts_state, mcts_legal_actions)
        mcts_to_action = {0: "TAKE_CARD", 1: "PAY_CHIP"}
        action = mcts_to_action[mcts_action]

        # action = ai01_get_action(legal_actions)

        game_state = do_action(game_state, action)

    return game_state


if __name__ == '__main__':
    app.run(port = 8000, debug=True)
