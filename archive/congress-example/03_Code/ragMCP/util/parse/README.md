# MCP Server Parsing Utility Functions

These files and functions cover the parsing logic for transforming the data obtained. It is in some ways the bedrock of the entire MCP server. We divided the logic into the following subfiles:

- `amendment.py`: Contains the very intricate logic to search for the amendment text inside the Congressional Record (through the GovInfo API)
- `committee.py`: Contains functions to search the committee membership files we have in `../../data/committees`
- `crep.py`: Contains all the parsing logic for Committee Reports
- `parse.py`: The very basic functions that handle calls and responses to API endpoints
- `text_parse.py`: The parsing logic to extract text from obtained links
- `votes.py`: Helper functions for scraping the votes from the Clerk's website

