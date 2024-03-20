import aws_cdk as cdk
import aws_rfdk as rfdk

class RFDKParentStack(cdk.Stack):
  def __init__(self, scope: cdk.Construct, id: str, **kwargs):
    super().__init__(scope, id, **kwargs)
