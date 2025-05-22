GOARCH=$(shell go env GOARCH)
ARCH=$(shell dpkg --print-architecture)
SERIES=jammy

ifeq ($(ARCH),$(shell dpkg --print-architecture))
QEMU_PARAMS += -enable-kvm
endif
ifeq ($(ARCH),arm64)
QEMU_PARAMS += -machine
QEMU_PARAMS += virt
endif

.PHONY: build-image
build-image:
	docker build --platform linux/$(GOARCH) -t python-apt:$(SERIES) -f Dockerfile.$(SERIES) .

.PHONY: wheel
wheel:
	docker run --platform linux/$(GOARCH) -v $(PWD):/github/workspace python-apt:$(SERIES)

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
