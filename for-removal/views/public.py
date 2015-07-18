# -*- coding: utf-8 -*-
'''Public section, including homepage and signup.'''
from flask import (
    Blueprint,
    flash,
    redirect,
    request,
    render_template,
    url_for,
)


blueprint = Blueprint('public', __name__, static_folder="../static")


@blueprint.route("/about/")
def about():
    return render_template("public/about.html")
