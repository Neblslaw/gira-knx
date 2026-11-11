

docker build -f Dockerfile.ubuntu -t gira-python:ubuntu .
docker run --rm --network host gira-python:ubuntu


docker build -f Dockerfile.python -t gira-python:python .          
docker run --rm --network host gira-python:python










