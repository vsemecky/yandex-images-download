import glob
import os
import re
import time
import sys
from multiprocessing import Pool
import traceback
from pprint import pprint

import yaml
from termcolor import colored

from .downloader import YandexImagesDownloader, get_driver, save_json
from .parse import parse_args

threads = 32  # Number of threads for downloading (not scraping)


def scrap(args):
    project_name = os.path.splitext(args.project)[0]
    print(f"project_name: '{project_name}'")
    output_dir = os.getcwd() + "/" + project_name
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output dir: '{output_dir}'")

    # Read YAML configuration for the dataset
    project = yaml.load(open(args.project), Loader=yaml.FullLoader)

    if 'negative' not in project or type(project['negative']) is not list:
        project['negative'] = []

    print("Project: negative IDs:", len(project['negative']))

    # negative_files = glob.glob(os.getcwd() + '/*.*')
    for negative_file in glob.glob(os.getcwd() + '/**/*.*', recursive=True):
        slug = os.path.basename(os.path.splitext(negative_file)[0])
        if re.match('^[a-z0-9]{56}$', slug):
            # print(slug, "OK")
            project['negative'].append(slug)

    # Dedupe negatives
    project['negative'] = list(set(project['negative']))

    print("Existing files:", len(project['negative']))
    # pprint(project['negative'])

    # Default values for items missing in project file
    if 'browser' not in project.keys() or project['browser'] is None:
        project['browser'] = "Chrome"

    # Keywords or URLs?
    if 'keywords' in project and 'urls' in project:
        raise Exception('Config error', "Use either 'keywords' or 'urls', not both!")
    elif 'keywords' in project:
        keywords = project['keywords']
        similar_images = False
    elif 'urls' in project:
        keywords = project['urls']
        similar_images = True
    else:
        raise Exception('Config error', "Either 'keywords' or 'urls' should be specified in the config!")

    # Driver
    driver = get_driver(project['browser'])

    try:
        pool = Pool(processes=threads)

        downloader = YandexImagesDownloader(
            driver=driver,
            output_directory=output_dir,
            limit=project['limit'],
            isize=project['isize'],
            min_width=project['min_width'],
            min_height=project['min_height'],
            iorient=project['iorient'],
            extension=project['extension'],
            pool=pool,
            similar_images=similar_images,
            negative=project['negative'])

        start_time = time.time()
        downloader_result = downloader.download_images(keywords, single_output_dir=project['single_output_dir'])
        # total_errors = sum(keyword_result.errors_count for keyword_result in downloader_result.keyword_results)
        # fix:
        total_errors = sum(result.errors_count for result in downloader_result.keyword_results if result.errors_count is not None)
    finally:
        driver.quit()
        pool.close()
        pool.join()

    total_time = time.time() - start_time

    print("\nEverything downloaded!")
    print(f"Total errors: {total_errors}")
    print(f"Total files downloaded: {len(keywords) * project['limit'] - total_errors}")
    print(f"Total time taken: {total_time} seconds.")
    save_json(f"{output_dir}/../{project_name}.json", downloader_result)
    # @todo Tady to zapsat znova a tentokrát do turbo.txt souboru a jenom URL, která se úspěšně povedla (nebo jsou EXIST), ale ne faily, a ne negative.


def main():
    try:
        args = parse_args()
        scrap(args)
    except Exception as e:
        print(colored(e, 'red'))
        print(colored(traceback.format_exc(), 'yellow'))
        sys.exit(1)


if __name__ == "__main__":
    main()
