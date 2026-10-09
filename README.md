Welcome to Rubby, the trash picking event organization webapp

In order to use the webapp, docker should be installd : look into docker/README.md

The webapp when run is located in [localhost:5000](http://localhost:5000/)

## Teams and event feeds

Logged-in users can open **Teams**, join or leave a team, and use **Events →
My team leaders** to see upcoming events created by the leaders of teams they
have joined. The **Subscribed users** view remains separate and shows events
created by accounts followed from the **Users** page.

The home page also shows the team leaderboard. A team's score is the total
number of attendance records for events created by its leader and attended by
team members, divided by the number of team members (including the leader)
times the number of events created by the leader, then multiplied by 100. It
therefore represents the average percentage of leader-created events attended
by a team member.

## Decisions

* events will be deleted after a year from the database. BUT each account will have a field named no_of_events (or something like that) that will keep track of how active they have been. The same for the cities. 
