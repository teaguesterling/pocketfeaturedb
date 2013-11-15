#!/usr/bin/env python

from werkzeug import secure_filename
from wtforms import TextField
from wtforms.validators import DataRequired
from flask_wtf import Form
from flask_wtf.file import FileField


class PickPocketForm(Form):
    
