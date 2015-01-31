from flask_wtf import Form
from wtforms import (
    BooleanField,
    PasswordField,
    StringField,
)
from wtforms import validators as check

from .models import User

__all__ = [
    'RegisterForm',
    'LoginForm',
]


class RegisterForm(Form):
    username = StringField('Username',
                    validators=[check.DataRequired(),
                                check.Length(min=3, max=25)])
    email = StringField('Email',
                    validators=[check.DataRequired(),
                                check.Email(),
                                check.Length(min=6, max=40)])
    password = PasswordField('Password',
                    validators=[check.DataRequired(),
                                check.Length(min=6, max=40)])
    confirm = PasswordField('Verify password',
                    validators=[check.DataRequired(),
                                check.EqualTo('password', message='Passwords must match')])

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        self.user = None

    def validate(self):
        initial_validation = super(RegisterForm, self).validate()
        if not initial_validation:
            return False
        uniqueness_validation = True
        existence_checks = {
            'username': self.username,
            'email': self.email,

        }
        for prop, field in existence_checks.items():
            existing = User.Query.filter_by(**{prop: field.data}).first()
            if existing:
                field.errors.append("{property} already registered".format(property=prop))
                uniqueness_validation = False
        return uniqueness_validation



class LoginForm(Form):
    username = StringField('Username', validators=[check.required()])
    password = PasswordField('Password', validators=[check.required()])
    remember = BooleanField('Remember', description="Remember me on this computer")

    @property
    def user(self):
        return User.query.filter_by(username=self.username.data).first()

    def validate(self):
        initial_validation = super(LoginForm, self).validate()
        if not initial_validation:
            return False
        if not self.user:
            self.password.errors.append("Invalid password (or incorrect username)")
            return False
        if not self.user.check_password(self.password.data):
            self.password.errors.append("Invalid password (or incorrect username)")
            return False
        return True
