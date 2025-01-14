import argparse
import logging
from os import mkdir
from os.path import expanduser, join
from shutil import rmtree

from dateutil.relativedelta import relativedelta
from hdx.data.dataset import Dataset
from hdx.facades.keyword_arguments import facade
from hdx.utilities.dateparse import now_utc
from hdx.utilities.dictandlist import write_list_to_csv

from mixpanel_downloads import get_mixpanel_downloads

logger = logging.getLogger()

lookup = "hdx-analysis-scripts"


def main(output_dir, mixpanel_config_yaml, **ignore):
    rmtree(output_dir, ignore_errors=True)
    mkdir(output_dir)

    today = now_utc()
    five_years_ago = today - relativedelta(years=5)

    logger.info("Getting downloads from MixPanel")
    dataset_downloads = get_mixpanel_downloads(
        mixpanel_config_yaml, five_years_ago, today
    )

    logger.info("Examining all datasets")
    datasets = Dataset.get_all_datasets()
    rows = [
        (
            "name",
            "title",
            "downloads all time",
            "downloads last 5 years",
            "date created",
            "date metadata updated",
            "date data updated",
            "dataset start date",
            "dataset end date",
            "update frequency",
            "organisation",
            "data link",
            "url",
            "is cod",
            "tags",
            "private",
            "requestable",
            "updated by script",
            "archived",
        )
    ]
    created_per_month = dict()
    metadata_updated_per_month = dict()
    data_updated_per_month = dict()
    for dataset in datasets:
        dataset_id = dataset["id"]
        name = dataset["name"]
        title = dataset["title"]
        downloads_5years = dataset_downloads.get(dataset_id, 0)
        downloads_alltime = dataset.get("total_res_downloads", "")
        updated_by_script = dataset.get("updated_by_script", "")
        created = dataset["metadata_created"]
        metadata_updated = dataset["metadata_modified"]
        data_updated = dataset["last_modified"]
        if not updated_by_script:
            year_month = created[:7]
            created_per_month[year_month] = created_per_month.get(year_month, 0) + 1
            year_month = metadata_updated[:7]
            metadata_updated_per_month[year_month] = metadata_updated_per_month.get(year_month, 0) + 1
            year_month = data_updated[:7]
            data_updated_per_month[year_month] = data_updated_per_month.get(year_month, 0) + 1
        date_of_dataset = dataset.get_date_of_dataset()
        startdate = date_of_dataset["startdate_str"]
        if date_of_dataset["ongoing"]:
            enddate = "ongoing"
        else:
            enddate = date_of_dataset["enddate_str"]
        update_frequency = dataset.get("data_update_frequency", "")
        org = dataset.get("organization")
        if org:
            org = org["title"]
        else:
            org = "NONE!"
        requestable = dataset.is_requestable()
        if requestable:
            data_link = ""
            requestable = "Y"
        else:
            data_link = dataset.get_resource()["url"]
            requestable = "N"
        url = dataset.get_hdx_url()
        tags = dataset.get_tags()
        if "common operational dataset - cod" in tags:
            is_cod = "Y"
        else:
            is_cod = "N"
        tags = ", ".join(tags)
        private = "Y" if dataset["private"] else "N"
        archived = "Y" if dataset["archived"] else "N"
        row = (
            name,
            title,
            downloads_alltime,
            downloads_5years,
            created,
            metadata_updated,
            data_updated,
            startdate,
            enddate,
            update_frequency,
            org,
            data_link,
            url,
            is_cod,
            tags,
            private,
            requestable,
            updated_by_script,
            archived,
        )
        rows.append(row)
    if rows:
        filepath = join(output_dir, "datasets.csv")
        logger.info(f"Writing rows to {filepath}")
        write_list_to_csv(filepath, rows, headers=1)
    keys = set(created_per_month.keys())
    keys.update(metadata_updated_per_month.keys())
    keys.update(data_updated_per_month.keys())
    rows = [("Year Month", "Created", "Metadata Updated", "Data Updated")]
    for key in sorted(keys):
        row = (key, created_per_month.get(key, ""), metadata_updated_per_month.get(key, ""), data_updated_per_month.get(key, ""))
        rows.append(row)
    if rows:
        filepath = join(output_dir, "non_script_updates.csv")
        logger.info(f"Writing rows to {filepath}")
        write_list_to_csv(filepath, rows, headers=1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Datasets Info script")
    parser.add_argument("-od", "--output_dir", default="output", help="Output folder")
    args = parser.parse_args()
    home_folder = expanduser("~")
    facade(
        main,
        hdx_read_only=True,
        hdx_site="prod",
        user_agent_config_yaml=join(home_folder, ".useragents.yml"),
        user_agent_lookup=lookup,
        project_config_yaml=join("config", "project_configuration.yml"),
        output_dir=args.output_dir,
        mixpanel_config_yaml=join(home_folder, ".mixpanel.yml"),
    )
