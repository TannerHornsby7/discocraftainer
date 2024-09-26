#!/.venv/bin/python
from aws_cdk import App 
from aws_cdk import Environment
from lib.server import Discocraftainer
import os
import dotenv

dotenv.load_dotenv()

# set up account and region for the app
account=os.environ["AWS_ACCOUNT_ID"]
region=os.environ["AWS_REGION"]

app = App()
Discocraftainer(app, "Discocraftainer", env=Environment(account=account, region=region))

app.synth()