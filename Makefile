ARCH=$(shell go env GOARCH)
SERIES=jammy

.DEFAULT_GOAL := wheel

.PHONY: build-image
build-image:
	docker build --platform linux/$(ARCH) -t python-apt:$(SERIES) -f Dockerfile.$(SERIES) .

.PHONY: wheel
wheel: build-image
	docker run --platform linux/$(ARCH) -v $(PWD):/github/workspace python-apt:$(SERIES)
