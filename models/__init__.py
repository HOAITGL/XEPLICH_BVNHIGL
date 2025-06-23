from extensions import db
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
from .user import User
from .shift import Shift
from .schedule import Schedule
from .ca import Ca
from .ca_config import CaConfiguration
from .clinic_room import ClinicRoom


