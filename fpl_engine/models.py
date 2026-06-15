from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    second_name = db.Column(db.String(100))
    now_cost = db.Column(db.Float)
    transfers_in = db.Column(db.Integer)
    selected_by_percent = db.Column(db.Float)

    total_points = db.Column(db.Integer, default=0)
    goals = db.Column(db.Integer, default=0)
    assists = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    photo = db.Column(db.String(20))
    team_code = db.Column(db.Integer)

    # ── NEW ──
    form = db.Column(db.Float, default=0.0)        # last 5 gameweek form
    element_type = db.Column(db.Integer, default=0) # 1=GK 2=DEF 3=MID 4=FWD

    def __repr__(self):
        return f'<Player {self.second_name}>'

class UsageLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    endpoint = db.Column(db.String(100))       # e.g. 'index', 'player_page'
    path = db.Column(db.String(255))           # e.g. '/player/123'
    method = db.Column(db.String(10))          # GET / POST
    query_string = db.Column(db.String(255))   # e.g. 'q=Saliba&pos=DEF'

    def __repr__(self):
        return f'<UsageLog {self.method} {self.path} @ {self.timestamp}>'


class PlayerSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    now_cost = db.Column(db.Float)
    transfers_in = db.Column(db.Integer)
    selected_by_percent = db.Column(db.Float)
    total_points = db.Column(db.Integer)
    form = db.Column(db.Float)
    z_score = db.Column(db.Float)

    def __repr__(self):
        return f'<PlayerSnapshot player={self.player_id} @ {self.timestamp}>'