kubectl create secret docker-registry infra-github-registry --docker-server=docker.pkg.github.com --docker-username=palfrey --docker-password=ghp_sometoken --docker-email=palfrey@tevps.net --output=yaml --dry-run=client

sudo apt-get install apache2-utils
echo somepassword | htpasswd -i -c auth palfrey
kubectl create secret generic portal-basic-auth --from-file=auth --output=yaml --dry-run=client > portal-basic-auth-Secret.yaml
