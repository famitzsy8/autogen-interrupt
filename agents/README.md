# Directory of the Agents

Here you can find the following files:

- `agent_test.py`: The file where I do smaller tests, and get a grasp for the CrewAI framework
- `api_util.py`: The file that handles the API authentication
- `prototype_multiagent.py`: The prototype multi-agent experiment, that helps me design the next stage of the system

## Prototype Multi-Agent System

Here we have a multi-agent system that **sequentially** goes through pre-defined tasks, each agent responsible for ONE task.

- `actions_agent`: Fetches the legislative actions from the Congress MCP server
- `interests_scanner_agent`: Looks at all the legislative actions, amendments and committees involved and returns a list of all those elements (e.g. an amendment or a committee referral) that need further inspection
- `committee_agent`: Looks at all the committees involved, scrutinizes its members and their relation to the bill and the company's interests and looks at the actions taken in the committee itself
- `amendment_agent`: Examines the text of the amendments, looks at the relevant sections and returns those that influence the company the most
- `parent_agent`: Aggregates all the findings into a lobbying "heat-map"

As for the tasks...

- `fetch_actions_task`: Uses the `actions_agent` to fetch the legislative actions of the specific bill
- `scan_hotspots_task`: Uses the `interests_scanner_agents` to identify the congressional elements to inspect further
- `committee_task`: Uses the `committee_agent` to report on committee influence on the advancements of the company's interests
- `amendment_task`: Uses the `amendment_agent` to look for sections in the amendments that propose interesting changes for the company
- `final_report_task`: Uses `parent_agent` to write the final report

