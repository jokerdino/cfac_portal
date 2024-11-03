import calendar
from datetime import datetime

import humanize
from babel.numbers import format_decimal


def indian_number_format(input_number):
    return format_decimal(input_number, format="#####,##,##,##0.00", locale="en_IN")


def humanize_datetime(input_datetime):
    return humanize.naturaltime(datetime.now() - input_datetime)


def datetime_format(value, format="%H:%M %d-%m-%y", result="default"):
    return_value = datetime.strptime(value, format)
    if result == "default":
        return return_value
    elif result == "current":
        res = calendar.monthrange(return_value.year, return_value.month)
        date_string = f"{res[1]}/{return_value.month:02}/{return_value.year}"
        return date_string
    elif result == "previous":
        date_string = f"01/{return_value.month:02}/{return_value.year}"
        # if return_value.month - 1 == 0:
        #     res = calendar.monthrange(return_value.year - 1, 12)
        #     date_string = f"{res[1]}/12/{return_value.year-1}"
        # else:
        #     res = calendar.monthrange(return_value.year, return_value.month - 1)
        #     date_string = f"{res[1]}/{return_value.month - 1:02}/{return_value.year}"
        return date_string
