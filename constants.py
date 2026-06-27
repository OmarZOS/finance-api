

import os
from enum import Enum

# # getting a list of scylla node names ["node1","node2"]
# SCYLLA_NODES = os.getenv("SCYLLA_NODES").split(",")
# SCYLLA_KEYSPACE = os.getenv("SCYLLA_DEFAULT_KEYSPACE")


SQL_SCHEMA = os.getenv("SQL_SCHEMA","mysql+pymysql")
SQL_HOST = os.getenv("SQL_HOST","127.0.0.1")
SQL_USER = os.getenv("SQL_USER","root")
SQL_PASSWORD = os.getenv("SQL_PASSWORD","dev_password")
SQL_DATABASE = os.getenv("SQL_DATABASE","gluttex")
SQL_PORT= os.getenv("SQL_PORT","3308")
DB_URI = f"{SQL_SCHEMA}://{SQL_USER}:{SQL_PASSWORD}@{SQL_HOST}:{SQL_PORT}/{SQL_DATABASE}"


GOOGLE_CLIENT_ID = os.getenv("API_GOOGLE_CLIENT_ID",'')
GOOGLE_CLIENT_SECRET = os.getenv("API_GOOGLE_CLIENT_SECRET",'')
FACEBOOK_CLIENT_ID = os.getenv("API_FACEBOOK_CLIENT_ID",'')
FACEBOOK_CLIENT_SECRET = os.getenv("API_FACEBOOK_CLIENT_SECRET",'')
INSTAGRAM_CLIENT_ID = os.getenv("API_INSTAGRAM_CLIENT_ID",'')
INSTAGRAM_CLIENT_SECRET = os.getenv("API_INSTAGRAM_CLIENT_SECRET",'')

API_ALGORITHM = os.getenv("API_ALGORITHM",'')
API_SECRET_KEY = os.getenv("API_SECRET_KEY",'')

AUTH_ALGORITHM = os.getenv("AUTH_ALGORITHM",'')
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY",'')


ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES",'')
REFRESH_TOKEN_EXPIRE_DAYS = os.getenv("REFRESH_TOKEN_EXPIRE_DAYS",'')



AUTH_SERVER_PROTOCOLE=os.getenv("AUTH_SERVER_PROTOCOLE",'http')
AUTH_SERVER_NAME =  os.getenv("AUTH_SERVER_NAME",'gluttex-auth')
AUTH_PORT = os.getenv("AUTH_PORT",9090)
AUTH_REGISTRATION_ENDPOINT = os.getenv("AUTH_REGISTRATION_ENDPOINT",'/auth/register')
AUTH_LOGIN_ENDPOINT = os.getenv("AUTH_LOGIN_ENDPOINT",'/auth/login')
AUTH_CHANGE_ENDPOINT = os.getenv("AUTH_CHANGE_ENDPOINT",'/auth/change-password')
AUTH_DELETE_ENDPOINT = os.getenv("AUTH_DELETE_ENDPOINT",'/auth/delete-user')


FILE_UPLOAD_ENDPOINT= os.getenv("FILE_UPLOAD_ENDPOINT",'')
FS_HOST= os.getenv("FS_HOST",'')
FS_PORT= os.getenv("FS_PORT",'')


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
BASE_URL = os.getenv("BASE_URL", "http://localhost:9000/api")



# ---------- OPENAI CONFIG ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", 'test-key-for-testing')
OPENAI_TEXT_MODELS="gpt-4.1-mini,gpt-4o-mini,gpt-4o,gpt-4.1,o3-mini,o3"
OPENAI_IMG_TEXT_MODELS="gpt-4o-mini,gpt-4o,gpt-4.1,o3"

MAX_TOKENS = 4000                   # safe max for responses
TEMPERATURE = 0.2                   # stable answers
TOP_P = 1
RETRIES = 3

# COMPUTING_SERVER_BASE_URL = os.getenv("COMPUTING_SERVER_BASE_URL","gluttex") 

ORDER_STATUSES = {'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELED'}

RULE_STATUSES = {'PENDING', 'REJECTED', 'SUSPENDED', 'OBSOLETE', 'ACTIVE'}

class RuleFlags:
    CAN_VIEW = 1 << 0          # 1
    CAN_EDIT = 1 << 1          # 2
    CAN_DELETE = 1 << 2        # 4
    CAN_APPROVE = 1 << 3       # 8
    CAN_EXPORT = 1 << 4        # 16

class ReactionType(str, Enum):
    PRODUCT = "product"
    RECIPE = "recipe"
    PROVIDER = "provider"
    COMMENT = "comment"

PRODUCT_REACTION_IDS = {1,2,3,4,5}
RECIPE_REACTION_IDS = {1,6,7,8,4}
PROVIDER_REACTION_IDS = {3,9,10,5,8}
COMMENT_REACTION_IDS = {1,3,8}

AMQP_HOST=os.getenv("RABBITMQ_HOST",'localhost')
AMQP_PORT=os.getenv("RABBITMQ_PORT",5672)
AMQP_VIRTUAL_HOST=os.getenv("RABBITMQ_VHOST",'/gluttex')
AMQP_USER=os.getenv("RABBITMQ_USER","dev_user")
AMQP_PASS=os.getenv("RABBITMQ_PASS","dev_pass")


DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD")

