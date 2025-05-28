from database import engine, Base
import models

# Create all tables in the database
Base.metadata.create_all(bind=engine)

print("Tables created successfully!")
