docker build -f Dockerfile.ubuntu -t gira-python:ubuntu .
docker run -d --rm --network host --name gira_knx_lab2 -v "$(pwd)/data/dane.csv:/app/data/dane.csv" gira-python:ubuntu 
cat data/dane.csv

docker rmi gira-python:ubuntu
