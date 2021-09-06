import os
import time
import sys
from multiprocessing import Pool
import yaml
from .downloader import YandexImagesDownloader, get_driver, download_single_image, save_json
from .parse import parse_args


def scrap(args):
    output_dir = os.getcwd() + "/yandex"

    # Read YAML configuration for the dataset
    project = yaml.load(open(args.project))

    # Default values for items missing in project file
    if 'num_workers' not in project.keys() or project['num_workers'] is None:
        project['num_workers'] = 4
    if 'browser' not in project.keys() or project['browser'] is None:
        project['browser'] = "Chrome"

    keywords = project['images']

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
            similar_images=True)

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
    save_json(f"{output_dir}/yandex.json", downloader_result)


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
