# k12-hello

A small HTTP service for testing the K12 deployment system: the host builds only `main`, a person approves and signs with a YubiKey, and the host verifies the signature before deployment.

Python's standard library keeps the service and its tests free of external dependencies.

Run locally with Python 3:

```sh
VERSION=dev COMMIT=local python3 -B app.py
```

The service listens on port 8080. `GET /` returns a greeting and version, `GET /healthz` returns `ok`, and `GET /version` returns JSON with the version and commit. SIGTERM triggers graceful shutdown. Run as a non-root user (as the container does).

Run tests with `make test`.

Build and run with a container engine, substituting the desired version and commit:

```sh
docker build -f Containerfile --build-arg VERSION=1.0.0 --build-arg COMMIT=abcdef -t k12-hello .
docker run --rm --read-only -p 8080:8080 k12-hello
```

The development VM had neither Podman nor Docker, so the container build was not tested there.
