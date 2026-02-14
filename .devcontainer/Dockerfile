FROM "mcr.microsoft.com/devcontainers/python:3.12"

# Install uv for Python environment management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN PROTOBUF_VERSION=$(curl -s "https://api.github.com/repos/protocolbuffers/protobuf/releases" | grep -Po 'tag_name": "v\K29\.[0-9]+' | sort -V | tail -1) \
    && curl -OL "https://github.com/protocolbuffers/protobuf/releases/download/v${PROTOBUF_VERSION}/protoc-${PROTOBUF_VERSION}-linux-x86_64.zip" \
    && unzip "protoc-${PROTOBUF_VERSION}-linux-x86_64.zip" -d protoc \
    && mv protoc/bin/protoc /usr/local/bin/protoc \
    && mv protoc/include/* /usr/local/include/ \
    && rm -rf protoc "protoc-${PROTOBUF_VERSION}-linux-x86_64.zip"
