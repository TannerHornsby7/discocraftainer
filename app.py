#!/.venv/bin/python
from aws_cdk import App 
from lib.server import DiscoCraftainer

app = App()
DiscoCraftainer(app, "Discocraftainer")

app.synth()