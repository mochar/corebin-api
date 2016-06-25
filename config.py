import os

basedir = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = '\x13\xae6\xc7\xc4\xb1\xbf\x164\xe7H\xf5\x7fw9\xd7X\xe0\xb5\x90\xc5\x9c\xce\x01'
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = False
DEBUG = False
HOST = '0.0.0.0'
