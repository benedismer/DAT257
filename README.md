Welcome to Rubby, the trash picking event organization webapp

In order to use the webapp, docker should be installd : look into docker/README.md

The webapp when run is located in [localhost:5000](http://localhost:5000/)

## Decisions

* events will be deleted after a year from the database. BUT each account will have a field named no_of_events (or something like that) that will keep track of how active they have been. The same for the cities. 
