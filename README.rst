monassis-server-sync
====================

Synchronisation service for the network of Monassis instances.


Development
-----------

 * Setup a virtualenv: ``virtualenv venv``
 * Activate it: ``source venv/bin/activate``
 * Install requirements into it: ``pip install -r requirements.txt``
 * ``initialize_db development.ini``
 * ``pserve development.ini --reload``

To run functional and unittests, first install:

  ``env/bin/pip install nose webtest``

the switch to the tests branch:

  ``git checkout tests``

then run:

  ``env/bin/nosetests``

To run volatile tests, you need two databases, namely test_sync_client
and test_sync_server, so create these in psql. Then:

 * ``cd tests``
 * ``./run_tests.sh``

Remember to copy the database.cfg.example file to database.cfg so that the nosetests can run.


Production
----------

The API uses HTTP basic authentication and must be accessed over SSL:

 * username: syncserver
 * password: BCMe7crxG-z_Wk_

The SSL certificate is self-signed, so a browser will complain that it doesn't look legitimate.
That's okay, we're only using it to secure the communication, not verify each party.

The recommended production setup is to use a combination of nginx and gunicorn. Nginx is the
frontend and handles badly behaved clients, SSL and HTTP Basic authentication. It proxies requests
to a collection of gunicorn servers on the local host.


Setup
-----

First, setup the basics.

 * ensure Python and pip are installed using the normal means
 * ensure virtualenv is installed:
   ``pip install virtualenv``
 * install git and other dependencies:
   ``sudo apt-get install libpq-dev python-dev git``

Setup the postgres database:

- use normal procedure here
- create the ``syncserver`` database and ``syncserver`` user.

Then create the syncserver user and clone the repo.

- ``sudo useradd -d /home/syncserver -m syncserver``
- ``sudo su - syncserver``
- ``git clone https://github.com/Siyavula/monassis-server-sync.git``
- ``cd monassis-server-sync``
- ``git checkout develop``

Setup the environment:

- ``virtualenv venv``
- ``source venv/bin/activate``
- ``pip install -r requirements.txt``
- ``python setup.py develop``

If this is the first time the database has been setup, run:

- ``initialize_db production.ini``

Copy the database.cfg.example file to database.cfg and ensure that the values are correct.


nginx
-----

Install nginx:

``sudo apt-get install nginx``

Link in the syncserver config:

``sudo ln -s /home/syncserver/monassis-server-sync/resources/nginx/syncserver.conf /etc/nginx/sites-enabled/``

And restart nginx:

``sudo service nginx restart``


upstart
-------

Tell upstart about the syncserver gunicorn server:

``sudo ln -s /home/syncserver/monassis-server-sync/resources/upstart/syncserver.conf /etc/init/``
``sudo initctl reload-configuration``

And start it:

``sudo start syncserver``


Logging
-------

nginx's production logs are in ``~syncserver/log/access.log``

The syncserver application logs are in ``~syncserver/log/syncserver.log``


Deploying changes
-----------------

To deploy changes to the service,

- make the changes elsewhere and commit to git
- ``git pull`` on the production server
- tell upstart to restart syncserver: ``sudo restart syncserver``

If you have made changes to the nginx config, you'll need to restart nginx too:

``sudo service nginx restart``


IP Whitelisting
---------------

See ``resources/nginx/syncserver.conf`` for info on how to whitelist IPs.
