from flask import Blueprint

cpu_standby_bp = Blueprint('cpu_standby', __name__)

def init_standby_service(*args, **kwargs):
    return None
