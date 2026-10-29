FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION=1.1.1
ARG BUILD_ARCH=amd64

# Python + Bibliotheken aus den Alpine-Paketen (keine Kompilierung nötig)
RUN apk add --no-cache \
        python3 \
        py3-pip \
        py3-aiohttp \
        py3-pillow \
        py3-fonttools \
        py3-defusedxml \
        tzdata \
    && pip3 install --no-cache-dir --break-system-packages --no-deps "fpdf2==2.8.*"

COPY app /app
COPY run.sh /
RUN chmod a+x /run.sh

LABEL \
    io.hass.name="My TrackView" \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="aarch64|amd64"

CMD [ "/run.sh" ]
