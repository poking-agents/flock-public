ARG PYTHON_VERSION=3.11.11

FROM python:${PYTHON_VERSION}-bookworm

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

ARG UV_VERSION=0.6.6
RUN curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh \
    | env UV_INSTALL_DIR=/opt/uv UV_UNMANAGED_INSTALL=true sh \
 && echo 'eval "$(/opt/uv/uv generate-shell-completion bash)"' >> /etc/bash_completion.d/uv
ENV PATH=/opt/uv:$PATH

ARG APP_USER=flock
ARG APP_DIR=/home/${APP_USER}/app
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} ${APP_USER} \
&& useradd -m -u ${USER_ID} -g ${APP_USER} -s /bin/bash ${APP_USER} \
&& mkdir -p ${APP_DIR} \
&& chown -R ${USER_ID}:${GROUP_ID} ${APP_DIR} /home/${APP_USER}

WORKDIR ${APP_DIR}
COPY --chown=${APP_USER}:${GROUP_ID} pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    uv sync \
        --all-extras \
        --all-groups \
        --locked \
        --no-install-project

COPY --chown=${APP_USER}:${GROUP_ID} . .
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    uv sync \
        --all-extras \
        --all-groups \
        --locked

USER ${APP_USER}
