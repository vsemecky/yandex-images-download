import argparse
import logging
from .downloader import DRIVER_NAME_TO_CLASS


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("browser",
                        help=("browser with WebDriver"),
                        type=str,
                        choices=list(DRIVER_NAME_TO_CLASS))

    parser.add_argument("-dp",
                        "--driver-path",
                        help=("path to brower's WebDriver"),
                        type=str,
                        default=None)

    parser.add_argument("--project",
                        help="Project file *.yml",
                        type=str,
                        default=None)

    parser.add_argument("--json",
                        help="save results information to json file",
                        type=str,
                        default=True)

    args = parser.parse_args()

    # Print command-line arguments
    for arg in vars(args):
        print("{0:<16} {1:<16}".format(arg, str(getattr(args, arg))))
    print("---------------------------------------")

    return args
