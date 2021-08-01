import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=str, help="Project file *.yml")
    args = parser.parse_args()

    # Print command-line arguments
    for arg in vars(args):
        print("{0:<16} {1:<16}".format(arg, str(getattr(args, arg))))
    print("---------------------------------------")

    return args
