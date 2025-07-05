from extensions import db
from flask_sqlalchemy import SQLAlchemy
from .shift_rate_config import ShiftRateConfig
from .leave_request import LeaveRequest

db = SQLAlchemy()
from .user import User
from .shift import Shift
from .schedule import Schedule
from .ca import Ca
from .ca_config import CaConfiguration
from .clinic_room import ClinicRoom


