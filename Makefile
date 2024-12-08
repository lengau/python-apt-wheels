ARCH=$(shell go env GOARCH)
SERIES=jammy

.PHONY: build-image
build-image:
	docker build --platform linux/$(ARCH) -t python-apt:$(SERIES) -f Dockerfile.$(SERIES) .

.PHONY: wheel
wheel:
	docker run --platform linux/$(ARCH) -v $(PWD):/github/workspace python-apt:$(SERIES)
