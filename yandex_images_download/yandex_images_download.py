import glob
import os
import time
import sys
from multiprocessing import Pool
from pprint import pprint

import yaml
from .downloader import YandexImagesDownloader, get_driver, save_json
from .parse import parse_args


def scrap(args):
    output_dir = os.getcwd() + "/dataset"
    negative_dir = os.getcwd() + "/negative"

    # Read YAML configuration for the dataset
    project = yaml.load(open(args.project), Loader=yaml.FullLoader)

    # Load negative IDs, @todo Implementovat načítání URL z configu
    project['negative'] = []  # stačí tohle disablovat a zůstanou tam url z configu
    negative_files = glob.glob(negative_dir + '/*.*')
    for negative_file in negative_files:
        project['negative'].append(os.path.basename(os.path.splitext(negative_file)[0]))
    print("Negative count:", len(project['negative']))

    # Default values for items missing in project file
    if 'num_workers' not in project.keys() or project['num_workers'] is None:
        project['num_workers'] = 4
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
        raise Exception('Config error', "Either 'keywords' or 'urls' should be specified in config!")

    # Driver
    driver = get_driver(project['browser'])

    try:
        pool = Pool(project['num_workers'])

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
        total_errors = sum(keyword_result.errors_count for keyword_result in downloader_result.keyword_results)
    finally:
        driver.quit()
        pool.close()
        pool.join()

    total_time = time.time() - start_time

    print("\nEverything downloaded!")
    print(f"Total errors: {total_errors}")
    print(f"Total files downloaded: {len(keywords) * project['limit'] - total_errors}")
    print(f"Total time taken: {total_time} seconds.")
    save_json(f"{output_dir}/../yandex.json", downloader_result)


def main():
    try:
        args = parse_args()
        scrap(args)

    except KeyboardInterrupt as e:
        print("KeyboardInterrupt")
        sys.exit(1)

    except Exception as e:
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
