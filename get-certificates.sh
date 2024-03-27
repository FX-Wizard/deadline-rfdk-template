# Use AWS CLI to download RCS certificate to connect to Deadline

# get tls certificate
TLS_KEY_SECRET_NAME=`aws secretsmanager list-secrets --filter Key=name,Values=RfdkDeadlineTemplateStack/RenderQueue/TlsRcsCertBundle --query "SecretList[].Name[] | [0]"`
eval "aws secretsmanager get-secret-value --secret-id ${TLS_KEY_SECRET_NAME} --query SecretBinary --output text | base64 --decode > deadline_rcs_rfdk_client.pfx"

# get password key
TLS_PASSWORD_SECRET_NAME=`aws secretsmanager list-secrets --filter Key=name,Values=RenderQueueTlsRcsCertBundle --query "SecretList[].Name | [0]"`
eval "aws secretsmanager get-secret-value --secret-id ${TLS_PASSWORD_SECRET_NAME} --query SecretString"

# render node ca certificate
ROOT_CA_CERT=`aws secretsmanager list-secrets --output json | jq -r '.SecretList[] | select(.Name | test("RootCA-X.509-Certificate")) | .Name'`
eval "aws secretsmanager get-secret-value --secret-id ${ROOT_CA_CERT} --query SecretString --output text > ca.crt"