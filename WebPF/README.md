Drake Discovery
===============================

A Flask Webserver for FEATURE DB


Quickstart
----------

First, set your app's secret key as an environment variable. For example, example add the following to ``.bashrc`` or ``.bash_profile``.

    export FEATUREDB_SECRET = 'something-really-secret'


Next run the following commands retrieve the source code: 
(Make sure you've registered a public key with github first: https://github.com/settings/ssh)

    cd YOUR_PROJECT_ROOT
    git clone git@github.com:teaguesterling/pocketfeaturedb pocketfeaturedb
    cd pocketfeaturedb
    
Then create a virtual environment to maintain a custom Python instance for this project:
(If the virtualenv command is not available try installing the python-virtualenv package 
or running `sudo pip install virtualenv`)  
    
    virtualenv --prompt="fdb" fdb
    
Finally, run the following commands to switch to and bootstrap your development environment
 
    source fdb/bin/activate
    pip install -r requirements/dev.txt
    
The following commands initialize a (sqlite) development database and start a test server:

    python manage.py db init
    python manage.py db migrate
    python manage.py db upgrade
    python manage.py server


Deployment
----------

In your production environment, make sure the ``FEATUREDB_ENV`` environment variable is set to ``"prod"``.


Shell
-----

To open the interactive shell, run:

    python manage.py shell

By default, you will have access to ``app``, ``db``, and the ``User`` model.


Running Tests
-------------

To run all tests, run:

    python manage.py test


Migrations
----------

Whenever a database migration needs to be made. Run the following commmands:
::

    python manage.py db migrate

This will generate a new migration script. Then run:
::

    python manage.py db upgrade

To apply the migration.

For a full migration command reference, run ``python manage.py db --help``.
