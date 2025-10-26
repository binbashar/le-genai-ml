#!/usr/bin/env python3
import aws_cdk as cdk
from stack import CognitoStack

app = cdk.App()
CognitoStack(app)
app.synth()