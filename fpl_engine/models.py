from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Player(db.Model):
    # Унікальний ID гравця з API FPL
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    second_name = db.Column(db.String(100))
    # Поточна ціна та кількість трансферів
    now_cost = db.Column(db.Float)
    transfers_in = db.Column(db.Integer)
    # Показник власності (Ownership %)
    selected_by_percent = db.Column(db.Float)
    # Час, коли ми зберегли цей запис
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Player {self.second_name} at {self.timestamp}>'