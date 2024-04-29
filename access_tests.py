import sqlite3
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import os
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import brownie
import brownie.project
import pytest
from utils.parsers import parse_cov_lines
import subprocess
import re
import csv


import sqlite3

prompt = 2

def setup_result_database():
    conn = sqlite3.connect('results.db')
    cur = conn.cursor()
    # Create an OverallStatistics table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS OverallStatistics (
            contract_id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT,
            model_name TEXT,
            contract_address TEXT,
            crashed INTEGER,
            failed INTEGER,
            succ INTEGER,
            UNIQUE(prompt, model_name,  contract_address)
        )
    ''')
    # Create a FunctionCoverage table without a foreign key to OverallStatistics
    cur.execute('''
        CREATE TABLE IF NOT EXISTS FunctionCoverage (
            coverage_id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT,
            model_name TEXT,
            contract_address TEXT,
            function_name TEXT,
            coverage FLOAT,
            UNIQUE(prompt, model_name, contract_address, function_name)
        )
    ''')
    conn.commit()
    conn.close()

def insert_overall_statistics(prompt, model_name, contract_address, crashed, failed, succ):
    conn = sqlite3.connect('results.db')
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT OR REPLACE INTO OverallStatistics (prompt, model_name ,contract_address, crashed, failed, succ)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (prompt, model_name, contract_address, crashed, failed, succ))
        conn.commit()
    except sqlite3.IntegrityError as e:
        print(f"Failed to insert data into OverallStatistics due to: {e}")
    finally:
        conn.close()

def insert_function_coverage(prompt, model_name, contract_address, function_name, coverage):
    conn = sqlite3.connect('results.db')
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT OR REPLACE INTO FunctionCoverage (prompt,  model_name , contract_address, function_name, coverage)
            VALUES (?, ?, ?, ?, ?)
        ''', (prompt, model_name, contract_address, function_name, coverage))
        conn.commit()
    except sqlite3.IntegrityError as e:
        print(f"Failed to insert data into FunctionCoverage due to: {e}")
    finally:
        conn.close()


setup_result_database()


def parse_coverage(contract_address, input, model_name, prompt):
    # Regular expression to match function names and coverage percentages
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    input = ansi_escape.sub('',input)
    pattern = re.compile(r"([a-zA-Z0-9_.]+)\s+-\s+(\d+\.\d+%)")

    for match in re.finditer(pattern, input):
        function_name = match.group(1)
        coverage = match.group(2)
        insert_function_coverage(prompt, model_name, contract_address, function_name, coverage)  # Ensure 'contract_address' is defined
    


def parse_succ_fail(contract_address, input, model_name, prompt):
    # Regular expression to match function names and coverage percentages
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    input = ansi_escape.sub('',input)
    crashCount = 0
    succCount = 0

    assertionErrorCount = input.count('- AssertionError:')

    pattern = re.compile(r"(\d+)\s+(failed)")
    # Find all matches and write each to the file
    for match in re.finditer(pattern, input):
        crashCount = int(match.group(1)) - assertionErrorCount


    pattern = re.compile(r"(\d+)\s+(passed)")
    # Find all matches and write each to the file
    for match in re.finditer(pattern, input):
        succCount = match.group(1)

    insert_overall_statistics(prompt, model_name, contract_address, crashCount,assertionErrorCount, succCount)  # Ensure 'contract_address' is defined
    






def retrieve_all_test_codes():
    if prompt == 1:
        database= 'tests.db'
    else:
        database = "tests_newPrompt.db"
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute("SELECT contract_index,  model_name, test_code FROM contract_tests")
    all_rows = cursor.fetchall()
    conn.close()
    return all_rows



table = pq.read_table('slither-audited-smart-contracts/data/raw/contracts0.parquet')


test_codes = retrieve_all_test_codes()
for test_code in test_codes:
    index = test_code[0]
    model= test_code[1]
    if model== "gpt-3.5-turbo":
        model_name="gpt35"
    elif model == "gpt-4-turbo":
        model_name = "gpt4"
    else:
        raise TypeError("unknown model name")
    brownie_test_code = test_code[2]
    # dataset = load_dataset("mwritescode/slither-audited-smart-contracts")
    # Convert the file to a pandas dataframe
    pd_table = table.to_pandas()
    contract = pd_table.iloc[index]
    source_code = contract.iloc[1]
    contract_address = contract.iloc[0]
    if contract_address != "27702a26126e0b3702af63ee09ac4d1a084ef628":
        continue
    print(contract_address)

    project_directory = f"brownie_projects/{model_name}/{prompt}/p_{contract_address}"
    
    # Check if the project directory exists
    if not os.path.isdir(project_directory):
        os.makedirs(project_directory)
        brownie.project.new(project_directory)
        with open(f"{project_directory}/contracts/Contract.sol", "w") as f:
            f.write(source_code)
    #else:
    #    continue
    # 

    with open(f"{project_directory}/tests/llm_test.py", "w") as f:
        f.write(brownie_test_code)

    

    # Load & Compile project using Brownie
    try:
        b_project = brownie.project.load(project_directory, name=model_name + str(contract_address))
    except Exception as e:
        print(f"{e}") 
        
    absolute_project_directory = os.path.abspath(project_directory)

    project_directory = absolute_project_directory

    # Run Brownie tests with coverage
    result = subprocess.run(
        ["brownie", "test", "--coverage"],
        cwd=project_directory,
        capture_output=True,
        text=True
    )

    # Now, `result.stdout` contains the output from the test run, including coverage information
    print(result.stdout)
    #text= "contract: TransparentProxy - 37.5% Proxy._setImplementation - 75.0% TransparentProxy.changeProxyAdmin - 0.0%"
    parse_coverage(contract_address, result.stdout, model_name, prompt)
    parse_succ_fail(contract_address, result.stdout, model_name, prompt)
    print("Contract Index:", test_code[0])
    print("Model Name:", test_code[1])


