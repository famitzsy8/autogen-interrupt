import sys, os
sys.path.append(os.getcwd() + "/congressMCP")
from util.fetch_util import _get_CR_Subsections
import json


dates = ["2023-04-10", "2022-04-27", "2021-02-23", "2020-08-06", "2019-03-27", "2018-06-26", "2016-04-28"]
full_data = {}

for date in dates:

    data = _get_CR_Subsections(date)
    filtered_granules = []
    for gran in data["granules"]:
        fgran = {}
        fgran["title"] = gran["granuleClass"] + ":" + gran["title"]
        filtered_granules.append(fgran)
    full_data[date] = filtered_granules

with open("crec_analysis_granules.json", "w") as f:
    json.dump(full_data, f, indent=4)