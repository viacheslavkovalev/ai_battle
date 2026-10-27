PRAGMA foreign_keys = ON;
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    token TEXT NOT NULL UNIQUE
);
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE memberships (
    user_id INTEGER NOT NULL REFERENCES users(id),
    project_id INTEGER NOT NULL REFERENCES projects(id),
    role TEXT NOT NULL CHECK (role IN ('viewer', 'editor', 'admin')),
    PRIMARY KEY (user_id, project_id)
);
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    title TEXT NOT NULL,
    body TEXT NOT NULL
);
INSERT INTO users VALUES
    (1, 'marina', 'demo-marina-token'),
    (2, 'oleg', 'demo-oleg-token'),
    (3, 'irina', 'demo-irina-token'),
    (4, 'pavel', 'demo-pavel-token'),
    (5, 'nina', 'demo-nina-token'),
    (6, 'roman', 'demo-roman-token');
INSERT INTO projects VALUES (17, 'Finance'), (29, 'People');
INSERT INTO memberships VALUES
    (1, 17, 'editor'),
    (2, 17, 'viewer'),
    (3, 29, 'admin'),
    (4, 29, 'editor'),
    (5, 17, 'viewer'),
    (5, 29, 'editor');
INSERT INTO documents VALUES
    (2001, 17, 'Budget draft', 'Finance budget: 120 synthetic units.'),
    (2002, 17, 'Quarterly forecast', 'Finance forecast for the next quarter.'),
    (3001, 29, 'Staffing plan', 'People staffing: 8 synthetic positions.');
