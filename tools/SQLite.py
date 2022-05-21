import sqlite3


class SQLite_db:
    def __init__(self, path_db):
        self.conn = self.connect(path_db)

    def __init_cursor(func):
        def the_wrapper_around_the_original_function(self, *args, **kwargs):
            cursor = self.conn.cursor()
            self.conn.commit()
            return func(self, *args, **kwargs, cursor=cursor)
        return the_wrapper_around_the_original_function

    def connect(self, path_db):
        conn = sqlite3.connect(path_db)
        return conn

    def close(self):
        if self.conn:
            self.conn.close()
        return True

    @__init_cursor
    def select_data(self, execute, cursor):
        cursor.execute(execute)
        return cursor.fetchall()

    @__init_cursor
    def select_data_iterable(self, execute, cursor):
        cursor.execute(execute)
        return cursor

    @__init_cursor
    def insert_data(self, execute, cursor, data_tuple = None):
        if data_tuple:
            cursor.execute(execute, data_tuple)
        else:
            cursor.execute(execute)
        return True
    
    @__init_cursor
    def insert_data_with_response(self, execute, cursor, data_tuple = None):
        if data_tuple:
            cursor.execute(execute, data_tuple)
        else:
            cursor.execute(execute)
        return cursor.fetchall()


def connect_to_sqllite(db_path):
    def decorator_the_wrapper_around_the_original_function(func):
        def the_wrapper_around_the_original_function(*args, **kwargs):
            sqlite = SQLite_db(db_path)
            try:
                result = func(*args, **kwargs, sqlite=sqlite)
            finally:
                if sqlite:
                    sqlite.close()

            return result

        the_wrapper_around_the_original_function.__name__ = func.__name__
        return the_wrapper_around_the_original_function
    return decorator_the_wrapper_around_the_original_function
