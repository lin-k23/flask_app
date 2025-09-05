from flask import Blueprint, jsonify, request

pegboard_bp = Blueprint("pegboard", __name__)
ROWS, COLS = 10, 15


def is_hole(r, c):
    if r in (0, ROWS - 1):
        return 3 <= c <= 11
    return 0 <= c < COLS


# None 无孔；0 空；'h1'/'h2'/'h3'/'h4' 占用
board = [[(0 if is_hole(r, c) else None) for c in range(COLS)] for r in range(ROWS)]
TYPES = {"h1", "h2", "h3", "h4"}


@pegboard_bp.route("/api/pegboard", methods=["GET"])
def get_board():
    return jsonify(board)


@pegboard_bp.route("/api/pegboard", methods=["POST"])
def update_board():
    d = request.get_json() or {}
    r, c = int(d.get("row", -1)), int(d.get("col", -1))
    state = d.get("state", 0)

    if not (0 <= r < ROWS and 0 <= c < COLS and is_hole(r, c)):
        return jsonify(ok=False, error="invalid position"), 400

    # 兼容数字 1~4
    if isinstance(state, int):
        if state == 0:
            board[r][c] = 0
        elif 1 <= state <= 4:
            board[r][c] = f"h{state}"
        else:
            board[r][c] = 0
    elif isinstance(state, str):
        state = state.strip().lower()
        if state in TYPES:
            board[r][c] = state
        elif state in {"0", "empty", "erase"}:
            board[r][c] = 0
        elif state in {"1", "2", "3", "4"}:
            board[r][c] = f"h{state}"
        else:
            board[r][c] = 0
    else:
        board[r][c] = 0

    return jsonify(ok=True, value=board[r][c])
