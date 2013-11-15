#!/usr/bin/env python

from __future__ import print_function, division

from flask import (
    Flask,
    request,
    render_template
)

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/submit')
def submit():
    return render_template('submit/full-comparison.html')


if __name__ == '__main__':
   app.run(host='0.0.0.0', debug=True) 
