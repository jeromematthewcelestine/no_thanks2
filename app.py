from flask import Flask, render_template, redirect, url_for, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import json
import random
from datetime import datetime
import os, psutil
import sys
from MCTSPlayerOnline import MCTSPlayerOnline

mcts_player_3p = MCTSPlayerOnline(n_players = 3, thinking_time = 0.3)
mcts_player_4p = MCTSPlayerOnline(n_players = 4, thinking_time = 0.3)

if "DATABASE_URL" in os.environ:
    DATABASE_URL = os.environ['DATABASE_URL']
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    import local_config
    DATABASE_URL = local_config.DATABASE_URL
    APP_SECRET_KEY = local_config.APP_SECRET_KEY

def log_memory():
    process = psutil.Process(os.getpid())
    print("memory (MB): ", process.memory_info().rss / 1000000)  # in MB

app = Flask(__name__)
app.secret_key = APP_SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
db = SQLAlchemy(app)

migrate = Migrate(app, db)

def ai01_get_action(legal_actions):
    return random.choice(legal_actions)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.Text)
    username = db.Column(db.Text)
    status = db.Column(db.Text)

class CompletedGame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime, default=datetime.utcnow)
    human_player = db.Column(db.String(50))
    human_score = db.Column(db.Integer)
    ai_1_score = db.Column(db.Integer)
    ai_2_score = db.Column(db.Integer, nullable=True)
    ai_3_score = db.Column(db.Integer, nullable=True)
    num_ai_players = db.Column(db.Integer)
    human_won = db.Column(db.Boolean)

def record_completed_game(game_state):
    print("Recording completed game")
    num_ai_players = len(game_state['players']) - 1
    human_player = game_state['players'][game_state['human_player_id']]['name']
    human_score = game_state['players'][game_state['human_player_id']]['score']

    human_player_id = game_state['human_player_id']
    human_won = (human_player_id in game_state['winners'])
    
    completed_game = CompletedGame(human_player=human_player,
                                    human_score=human_score,
                                    num_ai_players=num_ai_players,
                                    human_won=human_won)
    db.session.add(completed_game)
    db.session.commit()

def initialize_game(player_name = "Bob", num_opponents = 3):

    deck = list(range(3, 35+1))
    random.shuffle(deck)

    start_chips = 11
    omit_cards = 9

    table_chips = 0
    omitted_cards = [deck.pop() for _ in range(omit_cards)]
    print("len omitted_cards", len(omitted_cards))
    table_card = deck.pop()
    
    human_player = {"type": "human", "name": player_name, "cards": [], "chips": start_chips}
    players = [human_player]
    for i in range(num_opponents):
        ai_player = {"type": "ai01", "name": f"Player {i+1}", "cards": [], "chips": start_chips}
        players.append(ai_player)

    # randomize player order
    random.shuffle(players)
    for player in players:
        player["id"] = players.index(player)
    human_player_id = players.index(human_player)

    game_state = {
        "is_game_over": False,
        "active_player_id": 0,
        "deck": deck,
        "table_card": table_card,
        "table_chips": table_chips,
        "players": players,
        "human_player_id": human_player_id,
    }
    game = Game(state = json.dumps(game_state),
                username = "jeromew",
                status = "active")
    db.session.add(game)
    db.session.commit()
    return game.id

@app.route('/rules')
def rules_page():
    return render_template('rules.html')

@app.route('/new-game')
def new_game():
    return render_template('new_game.html')

@app.route('/create-game/', methods = ['POST'])
def create_game():
    print("create game")
    # print(request.json)
    game_id = initialize_game(player_name = request.json["player_name"],
                              num_opponents = request.json["num_ai_players"])
    session['game_id'] = game_id
    return jsonify({"success": True, "game_id": game_id})
    # return redirect(url_for('game_template', game_id=game_id))


@app.route('/about')
def about_page():
    return render_template('about.html')

@app.route('/list-games')
def list_games():
    games = Game.query.all()
    return render_template('list_games.html', games=games)

@app.route('/')
def home():
    return redirect(url_for('game_page'))
    
@app.route('/game')
def game_page():
    # if session has a game_id, redirect to that game
    # otherwise, redirect to new game
    if "game_id" in session:
        return render_template('game.html', game_id = session["game_id"])
    else:
        return redirect(url_for('new_game'))

@app.route('/game/<game_id>/resign', methods = ['POST'])
def game_resign(game_id):
    game = Game.query.filter(Game.id == game_id).first()
    game_state = json.loads(game.state)

    if game.status == "active" and not game_state["is_game_over"]:
        game_state["is_game_over"] = True
        # game_state["messages"].append("Resigned")
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
    # print(game_state)
    response = {
        "game_state": game_state
    }
    # print(jsonify(response))
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
        mcts_state = create_mcts_state(mcts_player_3p, game_state, active_player_id)
        mcts_legal_actions = create_mcts_legal_actions(legal_actions)
        mcts_action = mcts_player_3p.get_action(mcts_state, mcts_legal_actions)
        mcts_to_action = {0: "TAKE_CARD", 1: "PAY_CHIP"}
        action = mcts_to_action[mcts_action]
    elif (len(game_state["players"]) == 4):
        mcts_state = create_mcts_state(mcts_player_4p, game_state, active_player_id)
        mcts_legal_actions = create_mcts_legal_actions(legal_actions)
        mcts_action = mcts_player_4p.get_action(mcts_state, mcts_legal_actions)
        mcts_to_action = {0: "TAKE_CARD", 1: "PAY_CHIP"}
        action = mcts_to_action[mcts_action]
    else:
        action = random.choice(["TAKE_CARD", "PAY_CHIP"])

    game_state = do_action(game_state, action)

    game.state = json.dumps(game_state)
    db.session.commit()

    log_memory()

    # print(game_state)

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

    # print(response)

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

        # game_state["messages"].append(f"Player {active_player_id} paid a chip.")


    elif action_type == "TAKE_CARD":
        game_state["players"][active_player_id]["chips"] += game_state["table_chips"]
        game_state["table_chips"] = 0
        game_state["players"][active_player_id]["cards"].append(game_state["table_card"])
        game_state["players"][active_player_id]["cards"].sort()
        game_state["players"][active_player_id]["last_card"] = game_state["table_card"]

        # game_state["messages"].append(f"Player {active_player_id} took the {game_state['table_card']} card.")
        
        # Check if deck is empty. If empty, game over.
        if game_state["deck"]:
            game_state["table_card"] = game_state["deck"].pop()
            active_player_id = (active_player_id + 1) % len(game_state["players"])
            game_state["active_player_id"] = active_player_id

        else:
            game_state["table_card"] = None
            game_state["is_game_over"] = True
            game_state = calculate_scores_and_winners(game_state)
            record_completed_game(game_state)

    return game_state

@app.route('/stats')
def stats():
    stats_data = []
    for player_count in range(3, 5):
        games = CompletedGame.query.filter_by(num_ai_players=player_count-1).all()
        n_games = len(games)
        print("n_games: ", n_games)
        human_wins = len([game for game in games if game.human_won])
        ai_wins = n_games - human_wins
        if n_games:
            win_rate = str(round(human_wins / n_games, 2))
        else:
            win_rate = "N/A"
        stats_data.append({
            "player_count": player_count,
            "n_games": n_games,
            "human_wins": human_wins,
            "ai_wins": ai_wins,
            "win_rate": win_rate,
        })

    # Get the top 10 lowest scores for human players
    low_scores = []
    for game in CompletedGame.query.filter_by(human_won=True).order_by(CompletedGame.human_score).limit(10):
        date_str = game.time.strftime("%Y-%m-%d")
        low_scores.append({
            "name": game.human_player,
            "date": date_str,
            "score": game.human_score
        })

    return render_template('stats.html', stats_data=stats_data, low_scores=low_scores)


def create_mcts_state(mcts_player, game_state, active_player_id):
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

if __name__ == '__main__':
    app.run(port = 7001, debug=True)
