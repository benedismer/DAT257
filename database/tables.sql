CREATE TABLE Accounts (
	id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	username TEXT UNIQUE NOT NULL,
	password_hash TEXT NOT NULL,
	isOrganiser BOOLEAN NOT NULL DEFAULT FALSE
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

CREATE TABLE Subscriptions (
	id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	user_subscribed INTEGER NOT NULL REFERENCES Accounts(id) ON DELETE CASCADE,
	user_from_which_the_other_user_is_subscribed_to INTEGER NOT NULL REFERENCES Accounts(id) ON DELETE CASCADE,
	UNIQUE (user_subscribed, user_from_which_the_other_user_is_subscribed_to),
	CHECK (user_subscribed <> user_from_which_the_other_user_is_subscribed_to)
);

CREATE TABLE EventAttendance (
	id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	eventid INTEGER NOT NULL REFERENCES Events(id) ON DELETE CASCADE,
	username TEXT NOT NULL REFERENCES Accounts(username) ON DELETE CASCADE,
	UNIQUE (eventid, username)
);