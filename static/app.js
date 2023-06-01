class InstructionBanner extends React.Component {
  render() {
    const { game_state, active_player_id, makeMove, newGame, legal_actions } = this.props;
    const activePlayer = game_state.players.find(player => player.id === active_player_id);
    const playerName = activePlayer.name;
    const isHumanPlayer = activePlayer.id === game_state.human_player_id;
    const isGameOver = game_state.is_game_over;
    // const canPass = activePlayer
    let winner;
    let winnerNameSpanClass
    console.log('legal_actions', legal_actions)
    if (isGameOver) {
      winner = game_state.players.find(player => player.final_status === "winner");
      winnerNameSpanClass = 'player-name-' + winner.id;
    }
    const playerNameSpanClass = 'player-name-' + active_player_id;

    let you_must_message;
    if (legal_actions && isHumanPlayer && legal_actions.includes('PAY_CHIP')) {
      you_must_message = 
      <div>
        <span className={playerNameSpanClass}>{playerName}</span>, it is your turn. <br/>You must{" "}
        <button className="banner-button" onClick={() => makeMove('PAY_CHIP')}>PASS</button> or
        <button className="banner-button" onClick={() => makeMove('TAKE_CARD')}>TAKE CARD</button>.
      </div>
    } else {
      if (legal_actions && isHumanPlayer) {
        you_must_message =
        <div>
          <span className={playerNameSpanClass}>{playerName}</span>, it is your turn. <br/>You must
          <button className="banner-button" onClick={() => makeMove('TAKE_CARD')}>TAKE CARD</button>.
        </div>
      }
    }



    return (
      <div className="player-turn-banner">
        
        {isGameOver ? (
          <div>Game over. <span className={winnerNameSpanClass}>{winner.name}</span> wins!{" "}
            <button className="banner-button" onClick={() => newGame()}>New Game</button>
          </div>
        ) : isHumanPlayer ? (
          you_must_message
        ) : (
          <div>It is <span className={playerNameSpanClass}>{playerName}</span>'s turn.</div>
        )}
        
      </div>
    );
  }
}

class CommonArea extends React.Component {

  render() {
    let current_card;

    if (this.props.game_state.table_card) {
      const card_div_class = 'card card-value-' + this.props.game_state.table_card + ' ';
      current_card = (<div className={card_div_class}>
          <div className="card-text">{this.props.game_state.table_card}</div> 
        </div>)
    } else {
      current_card = <div className="card card-empty"></div>
    }

  return (
    <div className="commonArea">
      <div className="deck">
        {this.props.game_state.deck.length >= 3 &&
        <div className="card deck-card"></div>}
        {this.props.game_state.deck.length >= 2 &&
        <div className="card deck-card"></div>}
        {this.props.game_state.deck.length >= 1 ?
          (<div className="card deck-card"><div className="card-count">{this.props.game_state.deck.length}</div></div>) :
          (<div className="card card-empty"><div className="card-count">{this.props.game_state.deck.length}</div></div>)}
      </div>

      {current_card}

      <div className="commonArea_chipsArea">
        <div className="chips-counter">
          {this.props.game_state.table_chips}
        </div>
      </div>
    </div>)
  }
}

class PlayerInfo extends React.Component {
  isConsecutive(card1, card2) {
    return card2 - card1 === 1;
  }

  render() {
    const player = this.props.player;
    let is_active = null;

    let profile_image = null;
    if (this.props.player.id === this.props.game_state.active_player_id && !this.props.game_state.is_game_over) {
      is_active = true;
      if (this.props.player.id !== this.props.game_state.human_player_id) {
        profile_image = <img src="/static/Spinner-2.4s-34px.svg" id="loading-spinner" height="24"></img>
      } else {
        profile_image = <img src="/static/user-filled-svgrepo-com.svg" height="24" id="loading-spinner"></img>
      }
    } else {
      is_active = false;
      if (this.props.player.id !== this.props.game_state.human_player_id) {
        profile_image = <img src="/static/robot-icon.svg" id="loading-spinner" height="24" ></img>
      } else {
        profile_image = <img src="/static/user-filled-svgrepo-com.svg" height="24" id="loading-spinner"></img>
      }
    }

    const cardsList = player.card_groups.map((card_group) => {

      if (card_group && card_group.length == 0) {
        return (<div className="card-group"></div>)
      }

      const cards = card_group.map((card, index) => {
        const cardClass = 'card ' + (index > 0 ? ' underlapping-card' : '');
        const zIndex = 50 - index;
        
        return (
          <div className={cardClass} style={{"zIndex": zIndex}}>
            {card}
          </div>
        );
      });

      return (
        <div className="card-group">
          {cards}
        </div>)
    });

    // const cardsList = player.cards.map((card, index) => {
    //   let card_div_class = 'card card-value-' + card + ' ';
    //   if (player.last_card == card) card_div_class += ' last-chosen'

    //   let zIndex = 50
    //   if (index > 0 && this.isConsecutive(player.cards[index - 1], card)) {
    //     card_div_class += ' overlapping-card';
    //     zIndex = (50 - index)
    //   } else {
    //     zIndex = 50
    //   }

    //   return (
    //       <div className={card_div_class} key={index} style={{"zIndex": zIndex}}>
    //         <div className="card-text">{card}</div> 
    //       </div>
    //     )
    // });

    let chips_display;
    if (player.id == this.props.game_state.human_player_id || this.props.game_state.is_game_over) {
      chips_display = player.chips
    } else {
      chips_display = "?"
    }

    return (
      <div className={`playerArea ${is_active ? ' playerAreaActive' : ''}`}>
        <div className="playerArea_TopArea">
          <div className="playerArea_TopArea_ProfileImageArea">
            {profile_image}
          </div>
          <div className="playerArea_TopArea_NameArea">
            <span className={`player-name player-name-${this.props.player.id}`}>
              {player.name}
            </span>
          </div>
          <div className="playerArea_TopArea_ChipsArea">
            <div className="chips-counter">{chips_display}</div>
          </div>

          {(this.props.game_state.is_game_over &&
          <div className="playerArea_TopArea_ScoreArea">
            <div className="score-container">
              <img src="/static/star.svg" height="34" width="34" className="score-icon"></img>
              <div className="score-text-container">
                <span className={(player.final_status=="winner"?"score-bold":"score-normal")}>{player.score}</span>
              </div>
            </div>
          </div>)}

        </div>

      <div className="playerArea_BottomArea">
        <div className="playerArea_BottomArea_CardsArea">{cardsList}</div>
      </div>
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

      if (game_state.active_player_id !== game_state.human_player_id) {
        this.requestNext()
      } else {
        const response2 = await fetch(`/game-state/${game_id}/player/${game_state.active_player_id}`);
        const { game_state: game_state2, legal_actions: legal_actions } = await response2.json();
    
        this.setState({ legal_actions })
        this.setState({ game_state });
        this.setState({ active_player_id: game_state.active_player_id });
      }
    }
  }

  // async resign() {
  //   console.log("resign")
  //   const response = await fetch(`/game/${game_id}/resign`, {method: "POST"});
  //   const {success, game_state} = await response.json();

  //   if (success) {
  //     this.setState({ game_state })
  //   }
  // }

  newGame() {
    window.location.href = "/new-game"
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

    if (game_state.active_player_id !== game_state.human_player_id) {
      this.requestNext()
    }
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
          
            <InstructionBanner
              game_state={game_state} 
              active_player_id={active_player_id}
              makeMove={this.makeMove.bind(this)}
              newGame={this.newGame.bind(this)} 
              legal_actions={legal_actions}/>
          
            <CommonArea game_state={game_state} />
          
            {playerInfos}
          
          </div>
        
        </div>
      </div>
    );
  }
}

ReactDOM.render(<GameState />, document.getElementById('root'));