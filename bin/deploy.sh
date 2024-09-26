# set the environment variables (AWS_ACCOUNT_ID, AWS_REGION, SERVER_PORT)
source .env
if [ -z "$AWS_ACCOUNT_ID" ]; then
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    export AWS_ACCOUNT_ID
fi

if [ -z "$AWS_REGION" ]; then
    AWS_REGION=$(aws configure get region)
    export AWS_REGION
fi

if [ -z "$SERVER_PORT" ]; then
    SERVER_PORT=25565
    export SERVER_PORT
fi

cdk synth
cdk deploy --all