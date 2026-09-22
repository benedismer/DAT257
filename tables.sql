CREATE TABLE Events(
	id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
	event_name TEXT,
	country TEXT,
    city TEXT,
	time Time,
    date DATE
);