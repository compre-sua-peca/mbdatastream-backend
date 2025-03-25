from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from flask_migrate import Migrate

# Initialize the standard SQLAlchemy instance
db = SQLAlchemy()
migrate = Migrate()

# Function to setup async SQLAlchemy once app is created
def setup_async_sqlalchemy(app):
    # Get the database URI from Flask config
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    
    # Convert database URIs to their async equivalents
    if db_uri.startswith('sqlite:'):
        async_uri = db_uri.replace('sqlite:', 'sqlite+aiosqlite:')
    elif db_uri.startswith('postgresql:'):
        async_uri = db_uri.replace('postgresql:', 'postgresql+asyncpg:')
    elif db_uri.startswith('mysql:'):
        async_uri = db_uri.replace('mysql:', 'mysql+aiomysql:')
    elif db_uri.startswith('mysql+pymysql:'):
        async_uri = db_uri.replace('mysql+pymysql:', 'mysql+aiomysql:')
    else:
        # Default case
        async_uri = db_uri
    
    # print(f"Original URI: {db_uri}")
    # print(f"Async URI: {async_uri}")
    
    # Create async engine
    async_engine = create_async_engine(
        async_uri,
        echo=app.config.get('SQLALCHEMY_ECHO', False),
        future=True
    )
    
    # Create async session factory
    async_session_factory = sessionmaker(
        async_engine,
        expire_on_commit=False,
        class_=AsyncSession
    )
    
    # Add async session to db instance
    db.async_session = async_session_factory
    
    return async_engine