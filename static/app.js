class PlayerTurnBanner extends React.Component {
  render() {
    const { game_state, active_player_id, makeMove, newGame } = this.props;
    const activePlayer = game_state.players.find(player => player.id === active_player_id);
    const playerName = activePlayer.id === 0 ? activePlayer.name : `Player ${activePlayer.id}`;
    const isHumanPlayer = activePlayer.id === 0;
    const isGameOver = game_state.is_game_over;
    let winnerName;
    if (isGameOver) {
      winnerName = game_state.players.find(player => player.final_status === "winner").name;
    }

    return (
      <div className="player-turn-banner">
        {isGameOver ? (
          <div>Game over. {winnerName} wins!{" "}
            <button className="banner-button" onClick={() => newGame()}>New Game</button>
          </div>
        ) : isHumanPlayer ? (
          <div>
            {playerName}, it is your turn. You must{" "}
            <button className="banner-button" onClick={() => makeMove('PAY_CHIP')}>PASS</button> or{" "}
            <button className="banner-button" onClick={() => makeMove('TAKE_CARD')}>TAKE CARD</button>.
          </div>
        ) : (
          <div>It is {playerName}'s turn.</div>
        )}
      </div>
    );
  }
}





class GameLog extends React.Component {

  render() {

    const messageItems = this.props.game_state.messages.slice(0).reverse().map((message, idx) => 
      <div key={idx}>{message}</div>
    );
    
    
    return (
      <div className="log">
        {messageItems}
      </div>)

  }
}

class CommonArea extends React.Component {

  render() {
    let current_card;

    if (this.props.game_state.table_card) {
      current_card = <div className="card">{this.props.game_state.table_card}</div>
    } else {
      current_card = <div className="card card-empty"></div>
    }

  return (
    <div className="commonArea">
      <div className="deck">
        <div className="card"></div>
        <div className="card"></div>
        <div className="card">{this.props.game_state.deck.length}</div>
      </div>

      {current_card}

      <div className="chips-counter">
        {this.props.game_state.table_chips}
      </div>

    </div>)
  }
}

class PlayerInfo extends React.Component {
  render() {
    const player = this.props.player;
    let is_active = null;

    if (this.props.player.id === this.props.game_state.active_player_id) {
      is_active = true;
    } else {
      is_active = false;
    }

    const cardsList = player.cards.map((card, index) => {
      let card_div_class = 'card'
      if (player.last_card == card) card_div_class += ' last-chosen'
      return (
        <div className={card_div_class} >
          {card} 
        </div>
      )
    });

    return (
      <div className={`player${is_active ? ' active-player' : ''}`}>
        <div className={`player-info${is_active ? ' active-player' : ''}`}>
          <div className={`player-name${is_active ? ' active-player' : ''}`}>{(player.id == 0) ? (player.name) : "Player "+player.id}</div>
          <div className="score-counter">{player.score} {(player.final_status=="winner"?"*":"")}</div>
          <div className="chips-counter">{(player.id == 0) ? player.chips : "??"}</div>
        </div>
        <div className="player-cards">{cardsList}</div>
      </div>
      )
  }
}

class GameState extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      game_state: null,
      legal_actions: null,
      active_player_id: null
    };
  }

  async requestNext() {
    const next_response = await fetch(`/game/${game_id}/next`, {method: 'GET'});
    let {success: next_success, game_state } = await next_response.json();

    if (next_success) {
      this.setState({ game_state });
      this.setState({ active_player_id: game_state.active_player_id });
    }
  }

  async resign() {
    console.log("resign")
    const response = await fetch(`/game/${game_id}/resign`, {method: "POST"});
    const {success, game_state} = await response.json();

    if (success) {
      this.setState({ game_state })
    }
  }

  async makeMove(action_type) {
    console.log("makeMove")

    const action_response = await fetch(`/game/${game_id}/action`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ "action_player_id": this.state.active_player_id, "action_type": action_type })
    });
    let { success: action_success, game_state } = await action_response.json();

    const response2 = await fetch(`/game-state/${game_id}/player/${game_state.active_player_id}`);
    const { game_state: game_state2, legal_actions: legal_actions } = await response2.json();

    this.setState({ legal_actions })
    this.setState({ game_state });
    this.setState({ active_player_id: game_state.active_player_id });

    await this.requestNext()
    await this.requestNext()
  }

  async newGame() {
    window.location.href = "/new-game";
  }

  async componentDidMount() {
    // Fetch the initial game state from the server
    const response1 = await fetch(`/game-state/${game_id}`);
    const { game_state } = await response1.json();
    this.setState({ game_state: game_state, active_player_id: game_state.active_player_id });

    const response2 = await fetch(`/game-state/${game_id}/player/${game_state.active_player_id}`);
    const { game_state: game_state2, legal_actions: legal_actions } = await response2.json();
    console.log("response2")

    this.setState({ legal_actions })
  }

  render() {
    const { game_state, legal_actions, active_player_id  } = this.state;
    if (!game_state) {
      return (<div>Loading...</div>);
    }
    
    console.log(game_state.players)
    
    let playerInfos = game_state.players.map((player) => <PlayerInfo player={player} game_state={game_state} />);

    return (
      <div className="container">
        <div className="gameArea">
          <div className="gameWrapper">
          
            <PlayerTurnBanner
              game_state={game_state} 
              active_player_id={active_player_id}
              makeMove={this.makeMove.bind(this)}
              newGame={this.newGame.bind(this)} />
          
            <CommonArea game_state={game_state} />
          
            {playerInfos}
          
            <div className="bottomButtons">
              <button className="bottom-button" onClick={() => this.resign()}>Resign</button>
            </div>
          </div>
        
        </div>
      </div>
    );
  }
}

ReactDOM.render(<GameState />, document.getElementById('root'));