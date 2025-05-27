FROM "mcr.microsoft.com/devcontainers/python:3.12"

RUN curl -OL https://github.com/protocolbuffers/protobuf/releases/download/v24.4/protoc-24.4-linux-x86_64.zip \
    && unzip protoc-24.4-linux-x86_64.zip -d protoc \
    && mv protoc/bin/protoc /usr/local/bin/protoc \
    && mv protoc/include/* /usr/local/include/ \
    && rm -rf protoc protoc-24.4-linux-x86_64.zip