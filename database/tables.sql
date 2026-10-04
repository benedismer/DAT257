CREATE TABLE Events(
	id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	event_name TEXT,
	country TEXT,
    city TEXT,
	time Time,
    date DATE,
	latitude DOUBLE PRECISION,
	longitude DOUBLE PRECISION
);

CREATE TABLE Users(
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username TEXT,											
    role TEXT												-- account type: user/organizer
);

CREATE TABLE Subscriptions(
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    subscriber_id INTEGER,									-- subscriber
    organizer_id INTEGER									-- account that gets subscription
);

INSERT INTO Users (username, role)
VALUES ('Dummy User', 'user');								-- test account

INSERT INTO Users (username, role)
VALUES ('Dummy Organizer', 'organizer');					-- test account 2
