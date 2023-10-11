# Use AWS CLI to download RCS certificate to connect to Deadline

# get tls certificate
$TLS_KEY_SECRET_NAME = aws secretsmanager list-secrets --filter Key=name,Values=RfdkDeadlineTemplateStack/RenderQueue/TlsRcsCertBundle --query "SecretList[].Name[] | [0]"
aws secretsmanager get-secret-value --secret-id $TLS_KEY_SECRET_NAME --query SecretBinary --output text | certutil -decode > deadline_rcs_rfdk_client.pfx

# get password key
$TLS_PASSWORD_SECRET_NAME = aws secretsmanager list-secrets --filter Key=name,Values=RenderQueueTlsRcsCertBundle --query "SecretList[].Name | [0]"
aws secretsmanager get-secret-value --secret-id $TLS_PASSWORD_SECRET_NAME
