NETOPS_TAG := $(if $(NETOPS_TAG),$(NETOPS_TAG),latest)
NETOPS_REGISTRY_URL := $(if $(NETOPS_REGISTRY_URL),$(NETOPS_REGISTRY_URL),iguaziodocker)

.PHONY: default
default: golang py

.PHONY: py
py:
	cd py && docker build . -t netops-demo-py:$(NETOPS_TAG)

.PHONY: golang
golang:
	cd golang/src/github.com/v3io/demos && docker build \
		--tag netops-demo-golang:$(NETOPS_TAG) \
		--build-arg NUCLIO_BUILD_OFFLINE=true \
		--build-arg NUCLIO_BUILD_IMAGE_HANDLER_DIR=github.com/v3io/demos \
		.

.PHONY: push
push:
	docker tag netops-demo-py:$(NETOPS_TAG) $(NETOPS_REGISTRY_URL)/netops-demo-py:$(NETOPS_TAG)
	docker tag netops-demo-golang:$(NETOPS_TAG) $(NETOPS_REGISTRY_URL)/netops-demo-golang:$(NETOPS_TAG)
	docker push $(NETOPS_REGISTRY_URL)/netops-demo-py:$(NETOPS_TAG)
	docker push $(NETOPS_REGISTRY_URL)/netops-demo-golang:$(NETOPS_TAG)
