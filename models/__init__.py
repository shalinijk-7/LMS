from flask_sqlalchemy import SQLAlchemy
# Initializes the database and imports all application models.
db = SQLAlchemy()

from .all_models import *
