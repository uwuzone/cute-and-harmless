# show help
default:
	just --list

# build lambda docker
build-lambda:
    docker buildx build . -f build/Dockerfile.lambda --tag twitterscraper:lambda

# run the lambda using lambda emulator
run-lambda:
    docker run --rm -it -p 9000:8080 twitterscraper:lambda

# send test trigger to lambda emulator (run `just run-lambda` first)
trigger-lambda:
    curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'
