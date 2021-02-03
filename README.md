## CORS reverse development proxy
[![Build Status](https://github.com/romnn/proxybootstrap/workflows/test/badge.svg)](https://github.com/romnn/proxybootstrap/actions)
[![PyPI License](https://img.shields.io/pypi/l/proxybootstrap)](https://pypi.org/project/proxybootstrap/)
[![PyPI Version](https://img.shields.io/pypi/v/proxybootstrap)](https://pypi.org/project/proxybootstrap/)
[![PyPI Python versions](https://img.shields.io/pypi/pyversions/proxybootstrap)](https://pypi.org/project/proxybootstrap/)

A simple yet extensible python wrapper script for templating a proxy `nginx` configuration
that functions as host mapped reverse proxy container. 

#### Why and when to use?
Modern browsers enforce CORS policy and [won't let you](https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS) make requests
from your frontend running on `localhost:8080` to your backend at 
`localhost:4000`. To solve this problem, start a proxy at `localhost:5000`
(or any other spare port) and proxy requests based on paths:
- `localhost:5000/api` and `localhost:5000/buy` will be routed to the backend `localhost:4000`
- `localhost:5000/` will be routed to the frontend `localhost:8080`

#### Installation and usage
```bash
pip install proxybootstrap # using pip
```
**Note**: You will need `docker` for running the proxy container

Start the proxy server with your configuration
```bash
proxybootstrap \
    --port 5000 \
    /api@http://127.0.0.1:4000 /buy@http://127.0.0.1:4000 /@http://127.0.0.1:8080
```

#### Customization
| Option                | Description                                       | Default 
| ----------------------|:--------------------------------------------------|---------
| `locations`           | service locations to proxy.                       | None
| `-c` / `-config`      | `nginx` config template file                      | `./config/default.conf`
| `--port`              | listening port for the reverse proxy              | 5000
| `--verbose`           | enable verbose output                             | `False`
| `--sync`              | force synchronous communication with the proxy    | `False`
| `--tag`               | docker tag for the reverse proxy container        | dev/cors-reverse-proxy
| `--dockerfile`        | dockerfile for building the container             | `./Dockerfile`


Under the hood, configuration options are applied to the `--config` template
file and rendered using `jinja2`. If you wish, you can pass additional arguments and use
them in the config template.
Example:
```bash
proxybootstrap \
    -my_var1 Test1 \
    --my_var2 Test2 \
    --port 5000 \
    /@http://127.0.0.1:8080
```
can be accessed in a template with
```
{{ my_var1 }}
{{ my_var2 }}
```

#### Alternatives
- Write a custom proxy configuration for `nginx` or other proxy servers like
`trafik`, `envoy` or `haproxy`
- When using webpack or another popular tool there might be some plugins like 
[devserver-proxy](https://cli.vuejs.org/config/#devserver-proxy) for [vuejs](https://vuejs.org)
- Mess around with headers to allow specific CORS requests

#### Development
If you do not have `pipx` and `pipenv`, install with
```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install pipenv
```

Install all dependencies with
```bash
pipenv install --dev
```

To format, sort imports and check PEP8 conformity, run
```bash
pipenv run black .
pipenv run isort
pipenv run flake8
```
(These are also configured as a git pre commit hook)

#### Notice
This configuration is very minimal and intended for development use only.
