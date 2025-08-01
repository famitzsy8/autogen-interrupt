# This file contains the messages we use in the tool_call_exp.py file

def get_messages():
    msg1 = """The result of executing the extractBillActions tool: \"
    [FunctionExecutionResult(content='{\n  "actions": [\n    {\n      "date": "\\n    2017-07-27\\n   ",\n      "text": "\\n    Read twice and referred to the Committee on Finance.\\n   ",\n      "type": "\\n    IntroReferral\\n   "\n    },\n    {\n      "date": "\\n    2017-07-27\\n   ",\n      "text": "\\n    Introduced in Senate\\n   ",\n      "type": "\\n    IntroReferral\\n   "\n    }\n  ],\n  "debug": [\n    "Extracted 2 actions for bill {\'congress\': 115, \'bill_type\': \'s\', \'bill_number\': 1663}"\n  ]\n}', name='extractBillActions', call_id='call_Oix1ZBpsQ8ZLFeZOLoLyyS3C', is_error=False)]
    \"

    I want you to extract the members of all the committees.

    """
    msg2 = """
    The result of executing the extractBillActions tool: \"
    [\n    {\n      "date": "\\n    2017-07-27\\n   ",\n      "text": "\\n    Read twice and referred to the Committee on Finance.\\n   ",\n      "type": "\\n    IntroReferral\\n   "\n    },\n    {\n      "date": "\\n    2017-07-27\\n   ",\n      "text": "\\n    Introduced in Senate\\n   ",\n      "type": "\\n    IntroReferral\\n   "\n    }\n  ],\n ]
    \"
    I want you to extract the members of all the committees.

    """

    msg3 = """
    Extract the members of the Senate Committee on Finance.
    """

    return {
        "raw": msg1,
        "filtered": msg2,
        "trivial": msg3,
    }