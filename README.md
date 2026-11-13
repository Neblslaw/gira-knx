

docker build -f Dockerfile.ubuntu -t gira-python:ubuntu .
docker run -d --rm --network host --name gira_knx_lab2 gira-python:ubuntu 


docker rmi gira-python:ubuntu
