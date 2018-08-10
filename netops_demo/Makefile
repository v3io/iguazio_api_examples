.PHONY: py
py:
	cd py && docker build . -t netops-py:latest

.PHONY: golang
golang:
	cd golang && docker build -f Dockerfile \
		--tag netops-golang:latest \
		--build-arg NUCLIO_BUILD_OFFLINE=true \
		--build-arg NUCLIO_BUILD_IMAGE_HANDLER_DIR=github.com/v3io/demos \
		src/github.com/v3io/demos

.PHONY: all
all: golang py
