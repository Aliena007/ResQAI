import os

from app import create_app, db
from app.model import IncidentReport, User  # noqa: F401


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")