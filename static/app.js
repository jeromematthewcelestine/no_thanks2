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
      <div className="player">
        <div className="player-info">
          <div className="player-name">{(player.id == 0) ? (player.name) : "Player "+player.id}</div>
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

  async componentDidMount() {
    // Fetch the initial game state from the server
    const response1 = await fetch(`/game-state/${game_id}`);
    const { game_state } = await response1.json();
    this.setState({ game_state: game_state, active_player_id: game_state.active_player_id });
    // console.log("active_player_id", this.state.active_player_id)

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
        <h1 align="center"> </h1>
        <div className="gameArea">
          <CommonArea game_state={game_state} />
          
          {playerInfos}
          
          {game_state.is_game_over &&
            <div>
              <p>Game over.</p>
            </div>}
          {!game_state.is_game_over && active_player_id == 0 && legal_actions &&
            <div>
              <p>It is your turn.</p>
              <button onClick={() => this.makeMove('TAKE_CARD')} disabled={!legal_actions.includes('TAKE_CARD')}>Take Card</button>
              <button onClick={() => this.makeMove('PAY_CHIP')} disabled={!legal_actions.includes('PAY_CHIP')}>Pay Chip</button>
            </div>}
          {!game_state.is_game_over && active_player_id != 0 &&
            <div>
              <p>It is Player {active_player_id}'s turn.</p>
              <button onClick={() => this.requestNext()}>Next</button>
            </div>
          }
          <div>
            <button onClick={() => this.resign()}>Resign</button>
          </div>
          </div>
          
          <div className="logArea">
            <GameLog game_state={game_state}/>
          </div>
          
      </div>
    );
  }
}

ReactDOM.render(<GameState />, document.getElementById('root'));