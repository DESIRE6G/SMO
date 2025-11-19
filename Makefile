CONTAINER_TOOL ?= docker
TAG ?= $(shell git describe --dirty --long --always)

.PHONY: all images so sc oe topology help
.DEFAULT_GOAL: images

# Determine if we should push
ifdef REGISTRY
PUSH_FLAG = --push
IMAGE_PREFIX = $(REGISTRY)/
DEPLOY = GITHUB_ACCESS_TOKEN
else
PUSH_FLAG =
IMAGE_PREFIX =
DEPLOY = PLACEHOLDER
endif

so:
	$(CONTAINER_TOOL) build $(PUSH_FLAG) -t $(IMAGE_PREFIX)desire6g-so:$(TAG) -f components/service-orchestrator/Dockerfile components/service-orchestrator

sc:
	$(CONTAINER_TOOL) build $(PUSH_FLAG) -t $(IMAGE_PREFIX)desire6g-service-catalog:$(TAG) -f components/service-catalog/Dockerfile components/service-catalog

oe:
	$(CONTAINER_TOOL) build $(PUSH_FLAG) -t $(IMAGE_PREFIX)desire6g-oe:$(TAG) -f components/optimization-engine/Dockerfile components/optimization-engine

topology:
	$(CONTAINER_TOOL) build $(PUSH_FLAG) -t $(IMAGE_PREFIX)desire6g-topology:$(TAG) -f components/topology/Dockerfile components/topology

mlfo:
	$(CONTAINER_TOOL) build $(PUSH_FLAG) -t $(IMAGE_PREFIX)desire6g-mlfo:$(TAG) -f components/mlfo/Dockerfile components/mlfo


images: so sc oe topology mlfo
	@echo "Images built successfully:"
	@echo "- $(IMAGE_PREFIX)desire6g-so:$(TAG)"
	@echo "- $(IMAGE_PREFIX)desire6g-service-catalog:$(TAG)"
	@echo "- $(IMAGE_PREFIX)desire6g-oe:$(TAG)"
	@echo "- $(IMAGE_PREFIX)desire6g-topology:$(TAG)"
	@echo "- $(IMAGE_PREFIX)desire6g-mlfo:$(TAG)"
	@if [ -n "$(REGISTRY)" ]; then echo "Images pushed to: $(REGISTRY)"; else echo "Note: Images were not pushed (REGISTRY is unset)"; fi

deploy:
	@rm -fr deployment/deploy
	@cp -r deployment/template deployment/deploy
	@rm -f deployment/deploy/docker-compose.yaml
	@sed -i '' -e "s|DEFAULTTAG|$(TAG)|g" -e "s|IMAGE_PREFIX|$(IMAGE_PREFIX)|g" deployment/deploy/*.yaml

local:
	@echo "Generating Docker Compose file for local deployment"
	@rm -fr deployment/compose
	@mkdir -p deployment/compose
	@cp deployment/template/docker-compose.yaml deployment/compose
	@sed -i '' -e "s|DEFAULTTAG|$(TAG)|g" -e "s|IMAGE_PREFIX|$(IMAGE_PREFIX)|g" -e "s|PLACEHOLDER|$(DEPLOY)|g" deployment/compose/docker-compose.yaml
