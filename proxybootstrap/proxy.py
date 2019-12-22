import argparse
import asyncio
import logging
import os
import pathlib
import pprint
import shutil
import subprocess
import sys
import tempfile

import jinja2
import pkg_resources

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

assert sys.version_info >= (3, 6, 0), "cors-reverse-dev-proxy requires Python 3.6+"

current_dir = os.path.dirname(os.path.realpath(__file__))
default_config = dict(server_name="localhost", locations=list())


def is_valid_file(_parser, file):
    if os.path.isfile(file):
        return os.path.realpath(file)
    _parser.error(f"The file {file} does not exist")


def is_valid_dir(_parser, _dir):
    if os.path.isdir(_dir):
        return os.path.realpath(_dir)
    _parser.error(f"The directory {_dir} does not exist")


def packaged(module, file):
    try:
        return pkg_resources.resource_filename(module, file)
    except ModuleNotFoundError:
        return pathlib.Path() / file


class Proxy:
    @staticmethod
    def build_container(tag, source, build_args, verbose=True):
        logger.info(
            f'Building container tagged "{tag}" from {source} with arguments {str(", ").join(build_args)} ...'
        )
        build_cmd = f'docker build -t "{tag}" {source} {str(" ").join(build_args)} {" > /dev/null" if not verbose else ""}'
        logger.debug(build_cmd)
        build = subprocess.Popen(build_cmd, shell=True)
        build.communicate()
        if build.returncode != 0:
            logger.fatal(
                f"Attempt to build {tag} returned non-zero exit code. Aborting."
            )
            sys.exit(1)

    @staticmethod
    def compile_config(config, output, variables=None):
        variables = variables or dict()
        loader = jinja2.FileSystemLoader(os.path.dirname(config))
        env = jinja2.Environment(loader=loader)

        # Input template
        with open(config, "r") as template_file:
            template = env.from_string(template_file.read())

        # Rendered output config
        with open(output, "w") as output_file:
            output_file.write(template.render(**variables))

    @staticmethod
    async def run_container(tag, port, run_args, verbose=True, run_async=True):
        logger.info(
            f'Starting container tagged "{tag}" on localhost:{port} ({"async" if run_async else "sync"}) ...'
        )
        run_cmd = f'docker run -p {port}:80 {str(" ").join(run_args)} {tag} {" > /dev/null" if not verbose else ""}'
        logger.debug(run_cmd)
        if run_async:
            run = await asyncio.create_subprocess_exec(
                *["bash", "-c", run_cmd], stdout=asyncio.subprocess.PIPE
            )
            if verbose:
                while True:
                    _processUpdate = await run.stdout.readline()
                    if not _processUpdate:
                        break
                    else:
                        print(_processUpdate.decode("utf-8"))
            await run.wait()
        else:
            run = subprocess.Popen(run_cmd, shell=True)
            run.communicate()
        if run.returncode != 0:
            logger.fatal(
                f"Attempt to start image {tag} returned non-zero exit code. Aborting."
            )
            sys.exit(1)

    def __init__(self, **kwargs):
        self.loop = asyncio.get_event_loop()
        self.args = kwargs
        self.prepare_container()
        self.container = asyncio.gather(
            self.run_container(
                self.args["tag"],
                self.args["port"],
                run_args=['--network="host"'],
                verbose=self.args["verbose"],
                run_async=not self.args["sync"],
            )
        )

    def prepare_container(self):
        """Renders the containers config and builds the container"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            logger.debug(f"Creating temporary build context at {tmp_dir} ...")

            config_name = os.path.basename(self.args["config"])
            src, dest = self.args["config"], os.path.join(tmp_dir, config_name)

            logger.info(
                f"Compiling configuration to temporary build context at {dest} ..."
            )
            template_variables = {**default_config, **self.args}
            logger.debug(
                f"Using template variables: {pprint.pformat(template_variables)}"
            )
            self.compile_config(src, dest, template_variables)
            with open(dest, "r") as rendered_config:
                logger.debug(rendered_config.read())
            shutil.copyfile(
                self.args["dockerfile"], os.path.join(tmp_dir, "Dockerfile")
            )

            self.build_container(
                self.args["tag"],
                tmp_dir,
                build_args=["--no-cache", f"--build-arg nginx_config={config_name}"],
                verbose=self.args["verbose"],
            )

    async def shutdown(self):
        """Cancel tasks gracefully"""
        await asyncio.sleep(1)
        self.container.cancel()

    def start(self):
        """Start the container"""
        try:
            self.loop.run_until_complete(self.container)
        except KeyboardInterrupt:
            print("\n")
            logger.warning(
                "Received keyboard KeyboardInterrupt. Attempting to stop gracefully ..."
            )
            self.loop.run_until_complete(self.shutdown())
        finally:
            self.loop.close()
            logger.info("Done.")


def main():
    parser = argparse.ArgumentParser(
        description="Reverse proxy wrapper to handle CORS protection measures"
    )
    parser.add_argument(
        "locations",
        type=str,
        action="append",
        nargs="+",
        help="service locations to proxy",
    )
    parser.add_argument(
        "--port", type=int, help="listening port for the reverse proxy", default=5000
    )
    parser.add_argument(
        "--verbose",
        dest="verbose",
        action="store_true",
        help="enable verbose output",
        default=False,
    )
    parser.add_argument(
        "--sync",
        dest="sync",
        action="store_true",
        help="force synchronous communication with the proxy",
        default=False,
    )
    parser.add_argument(
        "--tag",
        type=str,
        help="docker tag for the reverse proxy container",
        default="dev/cors-reverse-proxy",
    )
    parser.add_argument(
        "--dockerfile",
        type=lambda d: is_valid_file(parser, d),
        help="dockerfile for building the container",
        default=packaged("proxybootstrap", "Dockerfile.jinja2"),
    )
    parser.add_argument(
        "-c",
        "-config",
        dest="config",
        type=lambda d: is_valid_file(parser, d),
        help="proxy server config jinja2 template file to substitute",
        default=packaged("proxybootstrap", "nginx.default.jinja2"),
    )

    # Parse known arguments and include any additional arguments to be passed to the templating engine
    args, unknown = parser.parse_known_args()
    for arg in unknown:
        if arg.startswith(("-", "--")):
            parser.add_argument(arg, type=str)
    args = parser.parse_args()

    logger.info(f"Using {args.config} as reverse proxy template ...")

    flattened_unparsed_locations = [
        item for sublist in args.locations for item in sublist
    ]
    try:
        args.locations = [
            dict(path=location.split("@")[0], backend=location.split("@")[1])
            for location in flattened_unparsed_locations
        ]
    except IndexError:
        sys.exit(
            f"Invalid locations {flattened_unparsed_locations}. "
            "Entries must be formatted like path@backend (e.g. /api@http:127.0.0.1:4000)"
        )

    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    print(vars(args))
    Proxy(**vars(args)).start()


if __name__ == "__main__":
    main()
