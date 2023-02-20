#!/usr/bin/python3
"""
This script performs data checks according to
the specification: https://github.com/tradingview-pine-seeds/pine-seeds-docs/blob/main/data.md
"""


import json
from os import getenv
from os.path import exists, isfile
from sys import exit as sys_exit
from datetime import datetime


def fail(msg):
    """ report about fail and exit with non-zero exit code"""
    print(msg)
    print("!!!! checks haven't passed !!!")
    sys_exit(1)


def check_symbol_fields(sym_file):
    """ check symbol file fields """
    errors = []
    if not (exists(sym_file) and isfile(sym_file)):
        return [], [F'symbol info file "{sym_file}" does not exist']
    with open(sym_file) as file:
        sym_data = json.load(file)
    expected_fields = set(("symbol", "description", "pricescale", "currency"))
    exists_fields = set(sym_data.keys())
    if exists_fields != expected_fields:
        if expected_fields.issubset(exists_fields):
            errors.append(F"JSON file {sym_file} contains unexpected fields: {', '.join(exists_fields.difference(expected_fields))}")
        else:
            errors.append(F"JSON file {sym_file} doesn't have required fields: {', '.join(i for i in expected_fields.difference(exists_fields))}")
    symbols = sym_data.get("symbol", [])
    descriptions = sym_data.get("description", [])
    pricescale = sym_data.get("pricescale", [])
    if len(symbols) != len(descriptions):
        errors.append(F'number of symbols not equal to number of symbol descriptions in JSON file {sym_file}')
    if len(symbols) != len(pricescale):
        errors.append(F'number of symbols not equal to number of pricescales in JSON file {sym_file}')
    return symbols, errors


def check_line_data(data_line, file_path, i):
    """ check values of data file's line """
    messages = []
    date = None
    if data_line.startswith("#"):
        messages.append(F'{file_path} has comment in line {i}')
        return messages, date
    if len(data_line.strip()) == 0:
        messages.append(F'{file_path} line {i} is empty')
        return messages, date
    vals = data_line.split(',')
    if len([i for i in vals if len(i) != len(i.strip())]) > 0:
        messages.append(F'{file_path} contains spaces in line {i}')
    if len(vals) != 6:  # YYYYMMDDT, o, h, l, c, v
        messages.append(F'{file_path}:{i} contains wrong number of elements (6 expected, actual {len(vals)})')
        return messages, date
    try:
        open_price, high_price, low_price, close_price = float(vals[1]), float(vals[2]), float(vals[3]), float(vals[4])
        _, volume = datetime.strptime(vals[0], '%Y%m%dT'), float(vals[5])
        if len(vals[0]) != 9:  # value '202291T' is considered as correct date 2022/09/01 by datetime.strptime but specification require zero-padded values
            raise ValueError
    except (ValueError, TypeError):
        messages.append(F'{file_path}:{i} contains wrong values types. Types must be: string(YYYYMMDDT), float, float, float, float, float')
    else:
        date = vals[0]
        if not (open_price <= high_price >= close_price >= low_price <= open_price and high_price >= low_price):
            messages.append(F'{file_path}:{i} contains wrong o h l c values. Values must stratify rules: h >= o, h >= l, h >= c, l <= o, l <= c)')
        if volume < 0:
            messages.append(F'{file_path}:{i} contains wrong volume value. It must be positive')
    return messages, date


def main():
    """ main routine """
    group = getenv("GROUP")
    if group == "":
        fail("ERROR: Environment variable GROUP is not set")
    symbols, sym_errors = check_symbol_fields(F"symbol_info/{group}.json")
    problems = {"errors": sym_errors, "missed_files": []}
    for symbol in symbols:
        file_path = F'data/{symbol}.csv'
        if not exists(file_path):
            problems["missed_files"].append(symbol)
            continue
        dates = set()
        last_date = ""
        double_dates = False
        unordered_dates = False
        with open(file_path) as file:
            for i, line in enumerate(l.rstrip('\n') for l in file):
                wrong, date = check_line_data(line, file_path, i+1)
                problems["errors"].extend(wrong)
                if date is not None:
                    if not double_dates and (date in dates):
                        double_dates = True
                        problems["errors"].append(F'{file_path} contains duplicates in dates. First double: {date} in line {i+1}')
                    if not unordered_dates and (date < last_date):
                        unordered_dates = True
                        problems["errors"].append(F'{file_path} has unordered dates. First unordered: {date} in line {i+1}', )
                    last_date = date
                    dates.add(date)
    if len(problems["missed_files"]) > 0:
        print(F'WARNING: following symbols have no corresponding .CSV file in data folder: {", ".join(problems["missed_files"])}')
    if len(problems["errors"]) > 0:
        fail('ERROR: following problems was found repository files:\n ' + ("\n ".join(problems["errors"])))
    print("All checks successfully passed")


if __name__ == "__main__":
    main()
