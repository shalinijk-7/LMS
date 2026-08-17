# Import the SQLAlchemy extension for Flask to enable Object-Relational Mapping (ORM)
from flask_sqlalchemy import SQLAlchemy

# Initialize the SQLAlchemy database instance
db = SQLAlchemy()

# Import all models to ensure they are registered with the SQLAlchemy metadata
# and discovered during database migrations or application startup
from .all_models import *