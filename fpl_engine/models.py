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
