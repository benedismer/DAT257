
CREATE TABLE Accounts (
	id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	username TEXT UNIQUE NOT NULL,
	password_hash TEXT NOT NULL,
	isTeam BOOLEAN NOT NULL DEFAULT FALSE, -- account type: user/team
	bio TEXT
);

CREATE TABLE Events(
	id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	event_name TEXT,
	country TEXT,
    city TEXT,
	time Time,
    date DATE,
	latitude DOUBLE PRECISION,
	longitude DOUBLE PRECISION,
	username TEXT NOT NULL REFERENCES Accounts(username) ON DELETE CASCADE
);

CREATE TABLE Subscriptions(
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    subscriber_id INTEGER,									-- subscriber
    team_id INTEGER,									-- account that gets subscription
	UNIQUE (subscriber_id, team_id),
	CHECK (subscriber_id <> team_id)
);

CREATE TABLE EventAttendance (
	id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	eventid INTEGER NOT NULL REFERENCES Events(id) ON DELETE CASCADE,
	username TEXT NOT NULL REFERENCES Accounts(username) ON DELETE CASCADE,
	UNIQUE (eventid, username)
);

CREATE TABLE Teams (
	id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	admin_id INTEGER NOT NULL UNIQUE REFERENCES Accounts(id) ON DELETE CASCADE,
	name TEXT NOT NULL,
	city TEXT,
	country TEXT
);

CREATE TABLE TeamMembers (
	id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	team_id INTEGER NOT NULL REFERENCES Teams(id) ON DELETE CASCADE,
	member_id INTEGER NOT NULL REFERENCES Accounts(id) ON DELETE CASCADE,
	UNIQUE (team_id, member_id),
	UNIQUE (member_id)
);

CREATE TABLE Trash (
	event_id INTEGER REFERENCES Events(id),
	account_name TEXT REFERENCES Accounts(username),
	amount INTEGER NOT NULL,
	type TEXT NOT NULL,
	UNIQUE (event_id, account_name, type)
);
	
