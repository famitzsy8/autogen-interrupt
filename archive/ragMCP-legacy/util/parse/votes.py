from math import log10

def _parse_roll_call_number_house(roll:int):

    return "0"*(2 - int(log10(roll))) + str(roll)