# -*- coding: utf-8 -*-

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask.ext import login

from drake.data.user import (
    actions,
    forms,
)
from .helpers import flash_errors


blueprint = Blueprint("user", __name__, url_prefix='/users', static_folder="../static")


@blueprint.route('/register', methods=('GET', 'POST'))
def register_user():
    form = forms.RegisterForm(request.form, csrf_enabled=True)
    if form.validate_on_submit():
        user = actions.create_user(username=form.username.data,
                                   email=form.email.data,
                                   password=form.password.data,
                                   first_name=form.first_name.data,
                                   last_name=form.last_name.data)
        if user.active:
            message = "Your account has been activated. You may no login in."
        else:
            message ="Your account as been created. Please check your email to confirm your registration"
        flash(message, 'success')
        return redirect(url_for('public.home'))
    else:
        flash_errors(form)
    return render_template('users/register.html', form=form)


@blueprint.route('/login', methods=('GET', 'POST'))
def login_user():
    form = forms.LoginForm(request.form, csrf_enabled=True)
    if request.method == 'POST':
        if form.validate_on_submit():
            user = form.user
            remember = form.remember
            next_url = request.args.get('next') or url_for('.')
            actions.login_user(user=user, remember=remember)
            flash("Successfully logged in as {username}".format(username=user.username), 'success')
            return redirect(next_url)
        else:
            flash_errors(form)
    return render_template('users/login.html', login_form=form)


@blueprint.route('/logout')
@login.login_required
def logout_user():
    actions.logout_user()


