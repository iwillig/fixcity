BikeRaction aka BuildMeABikeRack aka Fixcity
============================================

This project has been through several names already. Sorry :)

If you see "bmabr" in code, it's just an acronym for "Build Me A Bike
Rack". Don't worry about it.


The canonical source code is at http://github.com/iwillig/fixcity


Installation
============

Just run `python setup.py develop`, preferably in a virtualenv to
avoid installing stuff into your global python site-packages.


Bootstrapping a Database
========================

This application requires a PostGIS database and some shape data. To
get started:

 1) Copy the config.ini.in file to config.ini.  Edit database settings
    in config.ini as needed.  You MUST change the value of the
    'SECRET_KEY' setting.

 2) Create your database:

  createdb -T template_postgis bmabr

 3) Load the data:

   psql -d bmabr < fixcity/sql/gis_community_board.sql

 4) Bootstrap the django models:

  cd fixcity
  ./manage.py syncdb


 5) Visit the /admin/sites/site UI to change the domain name and
    display name of the website. These are used eg. in account
    confirmation email sent to users who register.


Deployment
==========

If you want to deploy under mod_wsgi, there's an appropriate handler
script in fixcity/wsgi/.  Point your apache config at it, something
like this:


 <VirtualHost ...>
 ServerName ...
 
 <Directory /PATH/TO/fixcity/wsgi/>
    Order allow,deny
    Allow from all
 </Directory>
 
 WSGIScriptAlias / /PATH/TO/fixcity/wsgi/fixcity.wsgi

 </VirtualHost>


