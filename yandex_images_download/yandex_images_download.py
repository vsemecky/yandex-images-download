import os
import time
import logging
import sys
from multiprocessing import Pool
import yaml
from .downloader import YandexImagesDownloader, get_driver, download_single_image, save_json
from .parse import parse_args


def scrap(args):
    output_dir = os.getcwd() + "/dataset"

    # Read YAML configuration for the dataset
    project = yaml.load(open(args.project))
    # Default values for items missing in project file
    if 'num_workers' not in project.keys() or project['num_workers'] is None:
        project['num_workers'] = 4

    keywords = project['images']

    driver = get_driver(args.browser, args.driver_path)

    try:
        pool = Pool(project['num_workers'])

        downloader = YandexImagesDownloader(
            driver=driver,
            output_directory=output_dir,
            limit=project['limit'],
            isize=project['isize'],
            iorient=project['iorient'],
            extension=project['extension'],
            pool=pool,
            similar_images=True)

        start_time = time.time()
        downloader_result = downloader.download_images(keywords, single_output_dir=project['single_output_dir'])
        total_errors = sum(keyword_result.errors_count for keyword_result in downloader_result.keyword_results)
    finally:
        driver.quit()
        pool.close()
        pool.join()

    total_time = time.time() - start_time

    logging.info("\nEverything downloaded!")
    logging.info(f"Total errors: {total_errors}")
    logging.info(f"Total files downloaded: {len(keywords) * project['limit'] - total_errors}")
    logging.info(f"Total time taken: {total_time} seconds.")
    save_json(f"{output_dir}/yandex.json", downloader_result)


def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    selenium_logger = logging.getLogger('seleniumwire')
    selenium_logger.setLevel(logging.WARNING)


def main():
    try:
        args = parse_args()
        setup_logging()
        scrap(args)

    except KeyboardInterrupt as e:
        logging.error("KeyboardInterrupt")
        sys.exit(1)

    except Exception as e:
        logging.error(e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
