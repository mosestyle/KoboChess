import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

CHESS_JS = (ROOT / "lib" / "chess.min.js").read_text(encoding="utf-8")

piece_dir = ROOT / "pieces" / "wikipedia"
piece_files = [
    "wP.png","wN.png","wB.png","wR.png","wQ.png","wK.png",
    "bP.png","bN.png","bB.png","bR.png","bQ.png","bK.png"
]

piece_data = {}
for name in piece_files:
    data = (piece_dir / name).read_bytes()
    piece_data[name] = "data:image/png;base64," + base64.b64encode(data).decode("ascii")

html_template = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>KoboChess Offline</title>
  <style>
    body{
      margin:0;
      padding:12px;
      font-family:Arial,Helvetica,sans-serif;
      background:#f4f4f4;
      color:#111;
    }
    .wrap{
      max-width:700px;
      margin:0 auto;
    }
    h1{
      margin:0 0 10px 0;
      text-align:center;
      font-size:28px;
    }
    .row{
      margin-bottom:8px;
      overflow:hidden;
    }
    .half{
      width:49%;
      float:left;
    }
    .half.right{
      float:right;
    }
    button,select{
      width:100%;
      min-height:48px;
      font-size:18px;
      border:2px solid #222;
      border-radius:8px;
      background:#fff;
      color:#000;
    }
    .status{
      border:2px solid #222;
      background:#fff;
      border-radius:8px;
      padding:10px;
      min-height:54px;
      font-size:18px;
      margin-bottom:10px;
    }
    #boardWrap{
      width:100%;
      border:3px solid #222;
      background:#000;
      margin-bottom:10px;
    }
    #boardTable{
      width:100%;
      border-collapse:collapse;
      table-layout:fixed;
    }
    #boardTable td{
      padding:0;
      margin:0;
      text-align:center;
      vertical-align:middle;
      border:none;
      overflow:hidden;
    }
    #boardTable img{
      display:block;
      width:90%;
      height:90%;
      margin:0 auto;
      object-fit:contain;
      pointer-events:none;
      user-select:none;
      -webkit-user-select:none;
    }
    .light{
      background:#e8e8e8;
    }
    .dark{
      background:#bdbdbd;
    }
    .selected{
      outline:3px solid #000;
      outline-offset:-3px;
    }
    .legal{
      box-shadow:inset 0 0 0 3px #777;
    }
    .hint{
      box-shadow:inset 0 0 0 3px #444;
    }
    .small{
      font-size:15px;
      line-height:1.35;
      margin-top:10px;
      opacity:.85;
    }
    .footer{
      margin-top:10px;
      font-size:14px;
      text-align:center;
      opacity:.8;
    }
    .clear{
      clear:both;
    }
    #menuWrap{
      margin-bottom:10px;
    }
  </style>
</head>
<body>
<div class="wrap">
  <h1>KoboChess Offline</h1>

  <div class="row">
    <button id="toggleMenuBtn">Hide Menu</button>
  </div>

  <div id="menuWrap">
    <div class="row">
      <div class="half">
        <select id="difficulty">
          <option value="1">Difficulty 1</option>
          <option value="2">Difficulty 2</option>
          <option value="3">Difficulty 3</option>
          <option value="4">Difficulty 4</option>
          <option value="5" selected>Difficulty 5</option>
          <option value="6">Difficulty 6</option>
          <option value="7">Difficulty 7</option>
          <option value="8">Difficulty 8</option>
          <option value="9">Difficulty 9</option>
        </select>
      </div>
      <div class="half right">
        <select id="sideSelect">
          <option value="w" selected>Play as White</option>
          <option value="b">Play as Black</option>
        </select>
      </div>
      <div class="clear"></div>
    </div>

    <div class="row">
      <div class="half">
        <button id="newGameBtn">New Game</button>
      </div>
      <div class="half right">
        <button id="undoBtn">Undo</button>
      </div>
      <div class="clear"></div>
    </div>

    <div class="row">
      <button id="hintBtn">Hint</button>
    </div>

    <div id="status" class="status">Loading offline build...</div>
  </div>

  <div id="boardWrap">
    <table id="boardTable"></table>
  </div>

  <div class="small">
    Offline Kobo version.<br>
    Your game auto-saves.
  </div>
  <div class="footer">kobo-offline.html v1</div>
</div>

<script>
__CHESS_JS__
</script>

<script>
(function () {
  var PIECE_DATA = __PIECE_DATA__;

  var boardTable = document.getElementById("boardTable");
  var boardWrap = document.getElementById("boardWrap");
  var statusEl = document.getElementById("status");
  var undoBtn = document.getElementById("undoBtn");
  var hintBtn = document.getElementById("hintBtn");
  var newGameBtn = document.getElementById("newGameBtn");
  var difficultyEl = document.getElementById("difficulty");
  var sideSelectEl = document.getElementById("sideSelect");
  var toggleMenuBtn = document.getElementById("toggleMenuBtn");
  var menuWrap = document.getElementById("menuWrap");

  var PIECE_FILES = {
    wp:"wP.png", wn:"wN.png", wb:"wB.png", wr:"wR.png", wq:"wQ.png", wk:"wK.png",
    bp:"bP.png", bn:"bN.png", bb:"bB.png", br:"bR.png", bq:"bQ.png", bk:"bK.png"
  };

  var FILES = ["a","b","c","d","e","f","g","h"];

  var game = new Chess();
  var selected = null;
  var legalTargets = [];
  var hintSquares = [];
  var flipped = false;
  var playerColor = "w";
  var botBusy = false;
  var menuVisible = false;

  function botColor() {
    return playerColor === "w" ? "b" : "w";
  }

  function saveState() {
    var data = {
      moves: game.history(),
      playerColor: playerColor,
      difficulty: difficultyEl.value,
      menuVisible: menuVisible
    };
    localStorage.setItem("koboOfflineState_v1", JSON.stringify(data));
  }

  function loadState() {
    try {
      var raw = localStorage.getItem("koboOfflineState_v1");
      if (!raw) return false;

      var data = JSON.parse(raw);

      playerColor = data.playerColor || "w";
      sideSelectEl.value = playerColor;
      difficultyEl.value = data.difficulty || "5";

      if (typeof data.menuVisible !== "undefined") {
        menuVisible = data.menuVisible;
      }

      game = new Chess();
      var moves = data.moves || [];
      for (var i = 0; i < moves.length; i++) {
        game.move(moves[i]);
      }

      selected = null;
      legalTargets = [];
      hintSquares = [];
      botBusy = false;
      flipped = playerColor === "b";

      applyMenuVisibility();
      renderBoard();
      updateStatus();
      return true;
    } catch (err) {
      return false;
    }
  }

  function applyMenuVisibility() {
    menuWrap.style.display = menuVisible ? "block" : "none";
    toggleMenuBtn.textContent = menuVisible ? "Hide Menu" : "Show Menu";
  }

  function getOrderedRanks() {
    return flipped ? [1,2,3,4,5,6,7,8] : [8,7,6,5,4,3,2,1];
  }

  function getOrderedFiles() {
    if (!flipped) return FILES.slice(0);
    return FILES.slice(0).reverse();
  }

  function pieceImgHtml(square) {
    var piece = game.get(square);
    if (!piece) return "&nbsp;";
    var key = piece.color + piece.type;
    var file = PIECE_FILES[key];
    return '<img src="' + PIECE_DATA[file] + '" alt="' + key + '">';
  }

  function isLightSquare(fileIndex, rankIndex) {
    return ((fileIndex + rankIndex) % 2 === 0);
  }

  function resizeBoardCells() {
    var width = boardWrap.clientWidth;
    var size = Math.floor(width / 8);
    var cells = boardTable.getElementsByTagName("td");
    for (var i = 0; i < cells.length; i++) {
      cells[i].style.width = size + "px";
      cells[i].style.height = size + "px";
    }
  }

  function renderBoard() {
    var html = "";
    var files = getOrderedFiles();
    var ranks = getOrderedRanks();

    for (var r = 0; r < ranks.length; r++) {
      html += "<tr>";
      for (var f = 0; f < files.length; f++) {
        var square = files[f] + ranks[r];
        var cls = isLightSquare(f, r) ? "light" : "dark";

        if (selected === square) cls += " selected";
        if (legalTargets.indexOf(square) !== -1) cls += " legal";
        if (hintSquares.indexOf(square) !== -1) cls += " hint";

        html += '<td class="' + cls + '" data-square="' + square + '">' + pieceImgHtml(square) + '</td>';
      }
      html += "</tr>";
    }

    boardTable.innerHTML = html;

    var cells = boardTable.getElementsByTagName("td");
    for (var i = 0; i < cells.length; i++) {
      cells[i].onclick = onSquareClick;
    }

    resizeBoardCells();
  }

  function updateStatus(extra) {
    if (extra) {
      statusEl.textContent = extra;
      return;
    }

    if (game.in_checkmate()) {
      statusEl.textContent = "Checkmate. " + (game.turn() === "w" ? "Black" : "White") + " wins.";
      return;
    }

    if (game.in_draw()) {
      statusEl.textContent = "Draw.";
      return;
    }

    if (botBusy) {
      statusEl.textContent = "Bot is thinking...";
      return;
    }

    if (game.turn() === playerColor) {
      statusEl.textContent = "Your move (" + (playerColor === "w" ? "White" : "Black") + ")." +
        (game.in_check() ? " Check." : "");
    } else {
      statusEl.textContent = "Bot to move." + (game.in_check() ? " Check." : "");
    }
  }

  function evaluateBoard(aiColor) {
    if (game.in_checkmate()) {
      if (game.turn() === aiColor) return -99999;
      return 99999;
    }

    if (game.in_draw()) return 0;

    var values = {
      p:100,
      n:320,
      b:330,
      r:500,
      q:900,
      k:20000
    };

    var score = 0;

    for (var fi = 0; fi < FILES.length; fi++) {
      for (var rank = 1; rank <= 8; rank++) {
        var sq = FILES[fi] + rank;
        var piece = game.get(sq);
        if (!piece) continue;

        var value = values[piece.type] || 0;

        if (piece.type === "p") {
          if (piece.color === "w") value += rank * 5;
          else value += (9 - rank) * 5;
        }

        if (piece.type === "n" || piece.type === "b") {
          if (sq === "d4" || sq === "e4" || sq === "d5" || sq === "e5") value += 15;
        }

        if (piece.color === aiColor) score += value;
        else score -= value;
      }
    }

    return score;
  }

  function minimax(depth, alpha, beta, aiColor) {
    if (depth === 0 || game.game_over()) {
      return evaluateBoard(aiColor);
    }

    var moves = game.moves();
    var maximizing = (game.turn() === aiColor);
    var i, value, best;

    if (maximizing) {
      best = -999999;
      for (i = 0; i < moves.length; i++) {
        game.move(moves[i]);
        value = minimax(depth - 1, alpha, beta, aiColor);
        game.undo();

        if (value > best) best = value;
        if (best > alpha) alpha = best;
        if (beta <= alpha) break;
      }
      return best;
    } else {
      best = 999999;
      for (i = 0; i < moves.length; i++) {
        game.move(moves[i]);
        value = minimax(depth - 1, alpha, beta, aiColor);
        game.undo();

        if (value < best) best = value;
        if (best < beta) beta = best;
        if (beta <= alpha) break;
      }
      return best;
    }
  }

  function sortMovesDescending(a, b) {
    return b.score - a.score;
  }

  function chooseMoveForColor(aiColor, level) {
    var moves = game.moves();
    if (!moves.length) return null;

    if (level === 1) {
      return moves[Math.floor(Math.random() * moves.length)];
    }

    var depth = (level >= 5) ? 2 : 1;
    var scored = [];
    var i, move, score;

    for (i = 0; i < moves.length; i++) {
      move = moves[i];
      game.move(move);
      score = minimax(depth - 1, -999999, 999999, aiColor);
      game.undo();
      scored.push({ move: move, score: score });
    }

    scored.sort(sortMovesDescending);

    if (level === 2) {
      return scored[Math.floor(Math.random() * Math.min(8, scored.length))].move;
    }
    if (level === 3) {
      return scored[Math.floor(Math.random() * Math.min(5, scored.length))].move;
    }
    if (level === 4) {
      return scored[0].move;
    }
    if (level === 5) {
      return scored[Math.floor(Math.random() * Math.min(4, scored.length))].move;
    }
    if (level === 6) {
      return scored[Math.floor(Math.random() * Math.min(2, scored.length))].move;
    }

    return scored[0].move;
  }

  function requestBotMove() {
    if (botBusy) return;
    if (game.game_over()) return;

    botBusy = true;
    updateStatus("Bot is thinking...");

    setTimeout(function () {
      var level = Number(difficultyEl.value);
      var move = chooseMoveForColor(botColor(), level);

      if (move) {
        game.move(move);
      }

      botBusy = false;
      hintSquares = [];
      renderBoard();
      updateStatus();
      saveState();
    }, 50);
  }

  function requestHint() {
    if (botBusy) return;
    if (game.game_over()) return;
    if (game.turn() !== playerColor) return;

    updateStatus("Finding best move...");

    setTimeout(function () {
      var move = chooseMoveForColor(playerColor, 6);

      if (!move) {
        updateStatus();
        return;
      }

      var verboseMoves = game.moves({ verbose: true });
      var i;
      for (i = 0; i < verboseMoves.length; i++) {
        if (verboseMoves[i].san === move) {
          hintSquares = [verboseMoves[i].from, verboseMoves[i].to];
          break;
        }
      }

      renderBoard();
      updateStatus("Hint: " + move);
    }, 50);
  }

  function onSquareClick() {
    if (botBusy) return;
    if (game.turn() !== playerColor) return;

    var square = this.getAttribute("data-square");
    hintSquares = [];

    if (!selected) {
      var piece = game.get(square);
      if (!piece) return;
      if (piece.color !== playerColor) return;

      selected = square;
      var moves = game.moves({ square: square, verbose: true });
      legalTargets = [];
      for (var i = 0; i < moves.length; i++) {
        legalTargets.push(moves[i].to);
      }
      renderBoard();
      updateStatus("Selected " + square);
      return;
    }

    if (selected === square) {
      selected = null;
      legalTargets = [];
      renderBoard();
      updateStatus();
      return;
    }

    var move = game.move({
      from: selected,
      to: square,
      promotion: "q"
    });

    if (!move) {
      var piece2 = game.get(square);
      if (piece2 && piece2.color === playerColor) {
        selected = square;
        var moves2 = game.moves({ square: square, verbose: true });
        legalTargets = [];
        for (var j = 0; j < moves2.length; j++) {
          legalTargets.push(moves2[j].to);
        }
        renderBoard();
        updateStatus("Selected " + square);
      } else {
        selected = null;
        legalTargets = [];
        renderBoard();
        updateStatus("Illegal move");
      }
      return;
    }

    selected = null;
    legalTargets = [];
    renderBoard();
    updateStatus();
    saveState();

    if (!game.game_over() && game.turn() === botColor()) {
      requestBotMove();
    }
  }

  function startGame() {
    game = new Chess();
    selected = null;
    legalTargets = [];
    hintSquares = [];
    botBusy = false;
    playerColor = sideSelectEl.value;
    flipped = playerColor === "b";

    renderBoard();
    updateStatus();
    saveState();

    if (playerColor === "b") {
      requestBotMove();
    }
  }

  undoBtn.onclick = function () {
    if (botBusy) return;

    var moveCount = game.history().length;
    if (moveCount >= 2) {
      game.undo();
      game.undo();
    } else if (moveCount === 1) {
      game.undo();
    }

    selected = null;
    legalTargets = [];
    hintSquares = [];
    renderBoard();
    updateStatus();
    saveState();
  };

  hintBtn.onclick = function () {
    selected = null;
    legalTargets = [];
    renderBoard();
    requestHint();
  };

  newGameBtn.onclick = startGame;
  sideSelectEl.onchange = startGame;

  toggleMenuBtn.onclick = function () {
    menuVisible = !menuVisible;
    applyMenuVisibility();
    saveState();
    resizeBoardCells();
  };

  window.onresize = resizeBoardCells;

  applyMenuVisibility();

  if (!loadState()) {
    startGame();
  } else {
    resizeBoardCells();
  }
})();
</script>
</body>
</html>
'''

html = html_template.replace("__CHESS_JS__", CHESS_JS)
html = html.replace("__PIECE_DATA__", json.dumps(piece_data))

out = ROOT / "kobo-offline.html"
out.write_text(html, encoding="utf-8")

print("Created:", out)
print("Copy this file to your Kobo:", out.name)
