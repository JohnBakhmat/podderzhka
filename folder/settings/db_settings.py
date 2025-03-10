# URL = 'postgresql://postgres:password@localhost:9991/mark-tech'
import os
URL = os.environ.get("DATABASE_URL", "database url was not provided")
