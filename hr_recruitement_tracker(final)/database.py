from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
import mysql.connector



from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

def get_db_connection():
    server = '127.0.0.1'
    database = 'u759228348_smartrecruit'
    user_name='root'
    password = quote_plus('1234')  # Encodes @ to %40

    engine = create_engine(
        f"mysql+pymysql://{user_name}:{password}@{server}/{database}",
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        echo=False
    )
    return engine

engine = get_db_connection()



        