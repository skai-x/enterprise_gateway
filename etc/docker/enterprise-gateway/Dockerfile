# Build the elastic-jupyter-operator binary
FROM golang:1.17.6-alpine as builder

WORKDIR /workspace
# Copy the Go Modules manifests
COPY go.mod go.mod
COPY go.sum go.sum

# Download libs first to use docker buildx caching
RUN go mod download
RUN go mod verify

# Copy the go source
COPY cli/ cli/
COPY api/ api/

# Build
RUN CGO_ENABLED=0 go build -a -o kubeflow-launcher cli/main.go

# Build the enterprise_gateway
FROM python:3.9.9-slim-bullseye

LABEL org.opencontainers.image.source https://github.com/skai-x/enterprise_gateway

USER root

# Remove the kernels since we are using KernelSpec CRD to mount the kernels 
# into the enterprise gateway.
# ADD jupyter_enterprise_gateway_kernelspecs*.tar.gz /usr/local/share/jupyter/kernels/
# ADD jupyter_enterprise_gateway_kernel_image_files*.tar.gz /usr/local/bin/
# The file is compiled from https://github.com/tkestack/elastic-jupyter-operator/blob/master/cli/main.go
COPY --from=builder /workspace/kubeflow-launcher /usr/local/bin/
COPY enterprise_gateway/etc/docker/enterprise-gateway/start-enterprise-gateway.sh /usr/local/bin/

ARG NB_USER="jovyan"
ARG NB_UID="1000"
RUN useradd -l -m -s /bin/bash -N -u "${NB_UID}" "${NB_USER}"

RUN mkdir -p /usr/local/share/jupyter && \
    chown jovyan:users /usr/local/bin/start-enterprise-gateway.sh && \
	chmod 0755 /usr/local/bin/start-enterprise-gateway.sh && \
	touch /usr/local/share/jupyter/enterprise-gateway.log && \
	chown -R jovyan:users /usr/local/share/jupyter /usr/local/bin/kubeflow-launcher && \
	chmod 0666 /usr/local/share/jupyter/enterprise-gateway.log && \
	rm -f /usr/local/bin/bootstrap-kernel.sh

# Install Enterprise Gateway wheel and kernelspecs
COPY enterprise_gateway/dist/jupyter_enterprise_gateway*.whl /tmp/
RUN pip install /tmp/jupyter_enterprise_gateway*.whl && \
	rm -f /tmp/jupyter_enterprise_gateway*.whl

USER jovyan

CMD ["/usr/local/bin/start-enterprise-gateway.sh"]

EXPOSE 8888

WORKDIR /usr/local/bin
