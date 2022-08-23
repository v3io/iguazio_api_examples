# Copyright 2017 Iguazio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
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
