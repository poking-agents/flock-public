ARG PYTHON_VERSION=3.11.11
ARG UV_VERSION=0.8.12

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-bookworm AS python
ARG UV_PROJECT_ENVIRONMENT=/opt/python
ENV PATH=${UV_PROJECT_ENVIRONMENT}/bin:$PATH

FROM python AS builder
COPY --from=uv /uv /uvx /usr/local/bin/
ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_INSTALLER_METADATA=1
ENV UV_LINK_MODE=copy

WORKDIR /source
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync \
        --all-extras \
        --all-groups \
        --locked \
        --no-install-project

FROM python
RUN --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
 && apt-get install -y --no-install-recommends \
        bash-completion \
        groff \
        jq \
        less \
        nano \
        rsync

COPY --from=uv /uv /uvx /usr/local/bin/
RUN echo 'eval "$(uv generate-shell-completion bash)"' > /etc/bash_completion.d/uv

ARG APP_USER=flock
ARG APP_DIR=/home/${APP_USER}/app
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} ${APP_USER} \
 && useradd -m -u ${USER_ID} -g ${APP_USER} -s /bin/bash ${APP_USER} \
 && mkdir -p ${APP_DIR} /home/${APP_USER}/.config \
 && chown -R ${USER_ID}:${GROUP_ID} ${APP_DIR} /home/${APP_USER}

COPY --from=builder --chown=${APP_USER}:${GROUP_ID} ${UV_PROJECT_ENVIRONMENT} ${UV_PROJECT_ENVIRONMENT}

WORKDIR ${APP_DIR}
COPY --chown=${APP_USER}:${GROUP_ID} . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync \
        --all-extras \
        --all-groups \
        --locked \
 && chown -R ${USER_ID}:${GROUP_ID} ${UV_PROJECT_ENVIRONMENT}

USER ${APP_USER}
