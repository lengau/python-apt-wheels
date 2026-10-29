ARCH ?= $(shell dpkg --print-architecture 2>/dev/null || uname -m)
SERIES ?= jammy
CONTAINER_ENGINE ?= $(if $(GITHUB_ACTIONS),docker,podman)
BUILD_ENGINE ?= $(if $(GITHUB_ACTIONS),docker buildx,$(CONTAINER_ENGINE))

ifeq ($(ARCH),x86_64)
CONTAINER_ARCH = amd64
else ifeq ($(ARCH),aarch64)
CONTAINER_ARCH = arm64
else ifeq ($(ARCH),armhf)
CONTAINER_ARCH = arm/v7
else ifeq ($(ARCH),ppc64el)
CONTAINER_ARCH = ppc64le
else
CONTAINER_ARCH = $(ARCH)
endif

PLATFORM ?= linux/$(CONTAINER_ARCH)
IMAGE_TAG ?= python-apt:$(SERIES)
TAG_ARG = $(if $(IMAGE_TAG),-t $(IMAGE_TAG),)
IMAGE_REF ?= $(if $(IMAGE_TAG),$(IMAGE_TAG),python-apt:$(SERIES))

ifeq ($(ARCH),$(shell dpkg --print-architecture 2>/dev/null))
QEMU_PARAMS += -enable-kvm
endif
ifeq ($(ARCH),arm64)
QEMU_PARAMS += -machine
QEMU_PARAMS += virt
endif

.PHONY: build-image
build-image:
	$(BUILD_ENGINE) build --platform $(PLATFORM) $(TAG_ARG) -f Dockerfile.$(SERIES) $(BUILD_ARGS) .

.PHONY: pull-image
pull-image:
	$(CONTAINER_ENGINE) pull --platform $(PLATFORM) $(IMAGE_REF)

.PHONY: wheel
wheel:
	$(CONTAINER_ENGINE) run --platform $(PLATFORM) -e ARCH=$(ARCH) -v $(PWD):/github/workspace $(IMAGE_REF)

prepare-image:
	rm -f $(SERIES)-server-cloudimg-$(ARCH).img
	wget https://cloud-images.ubuntu.com/$(SERIES)/current/$(SERIES)-server-cloudimg-$(ARCH).img
	qemu-img resize $(SERIES)-server-cloudimg-$(ARCH).img +10G

qemu-wheel:
	qemu-system-$(ARCH) -nographic -m 4G \
	    -nic user,model=virtio $(QEMU_PARAMS) \
	    -drive media=disk,if=virtio,file=$(SERIES)-server-cloudimg-$(ARCH).img \
	    -smp cpus=4 \
	    -boot menu=off -boot order=c -kernel /boot/vmlinuz -append "recovery"
