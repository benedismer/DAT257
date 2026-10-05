
CREATE TABLE Accounts (
	id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	username TEXT UNIQUE NOT NULL,
	password_hash TEXT NOT NULL,
	isOrganiser BOOLEAN NOT NULL DEFAULT FALSE -- account type: user/organizer
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
    organizer_id INTEGER,									-- account that gets subscription
	UNIQUE (subscriber_id, organizer_id),
	CHECK (subscriber_id <> organizer_id)
);

CREATE TABLE EventAttendance (
	id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	eventid INTEGER NOT NULL REFERENCES Events(id) ON DELETE CASCADE,
	username TEXT NOT NULL REFERENCES Accounts(username) ON DELETE CASCADE,
	UNIQUE (eventid, username)
);
