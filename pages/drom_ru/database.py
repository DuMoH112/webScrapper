from tools.SQLite import connect_to_sqllite

DATABASE = 'pages/drom_ru/card.db'


@connect_to_sqllite(DATABASE)
def migration(sqlite):
    sqlite.insert_data("""
        CREATE TABLE IF NOT EXISTS cards(
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            card_id INTEGER UNIQUE,
            time_create INTEGER,
            name TEXT,
            year INTEGER,
            model TEXT,
            price INTEGER,
            url TEXT,
            image BLOB
        );
    """)

    return True
