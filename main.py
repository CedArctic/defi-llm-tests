import re
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import solcx
from py_solidity_parser.main import from_standard_output
import sqlite3

from utils.prompt import prompt_template
from utils.compile_sol import compile_contract_standard
from utils.filters import CONTRACTS_FILTER
from utils.placeholders import ph_llm_response, ph_contract_source
import json
import openai
from openai import OpenAI
import sqlite3
import brownie

Model = "gpt-3.5-turbo"
last_pointer=160
range_begin = 160
range_end = 190
promptNum = 2

def initialize_test_database():
  # Connect to SQLite database
  if promptNum == 2:
    conn = sqlite3.connect('tests_newPrompt.db')
  elif promptNum ==1:
    conn = sqlite3.connect('tests.db')   

  # Create a cursor object
  cursor = conn.cursor()

  cursor.execute('''
  CREATE TABLE IF NOT EXISTS contract_tests (
      id INTEGER PRIMARY KEY,
      contract_index INTEGER,
      model_name TEXT,
      test_code TEXT
  )
  ''')

  # Commit the changes and close the connection
  conn.commit()
  conn.close()


def insert_test_code(contract_index, model_name, test_code):
  # Connect to SQLite database
  if promptNum == 2:
    conn = sqlite3.connect('tests_newPrompt.db')
  elif promptNum ==1:
    conn = sqlite3.connect('tests.db')   
  
  cursor = conn.cursor()
  cursor.execute("INSERT INTO contract_tests (contract_index, model_name, test_code) VALUES (?, ?, ?)",
                  (contract_index, model_name, test_code))
  conn.commit()
  conn.close()




initialize_test_database()

for index in range(range_begin,range_end+1):
  # dataset = load_dataset("mwritescode/slither-audited-smart-contracts")
  # Read a random parquet file
  table = pq.read_table('slither-audited-smart-contracts/data/raw/contracts0.parquet')

  # Convert the file to a pandas dataframe
  pd_table = table.to_pandas()


  # Sample a random contract entry
  # contract = pd_table.sample()
  # print(contract)

  contract = pd_table.iloc[index]
  # Get source code.
  source_code = contract.iloc[1]
  # TODO: Remove temporary placeholder source code used for testing
  #source_code = ph_contract_source

  # print(source_code)

  # Check if there exists a recommended version of the compiler. If not, default to the latest
  pragma_res = re.search(r'pragma solidity \^?(\d+\.\d+\.?\d*);', source_code)
  if pragma_res:
      compiler_version = pragma_res.groups()[0]
  else:
      compiler_version = '0.8.25'

  # Check if the compiler version is installed. If not, install it
  installed_compilers = [str(version) for version in solcx.get_installed_solc_versions()]
  if compiler_version not in installed_compilers:
      solcx.install_solc(compiler_version)

  # Switch the required compiler version
  solcx.set_solc_version(compiler_version)

  # Compile the contract and get compiler standard output JSON
  try:
    compiler_out_json = compile_contract_standard(source_code)
  except:
     continue

  # Generate Abstract Syntax Tree (AST) using the standard output JSON
  nodes = from_standard_output(compiler_out_json)[0]

  # Get contract nodes
  contract_nodes = [node for node in nodes if node.nodeType == 'ContractDefinition']

  # Filter out known libraries
  contract_nodes = [contract for contract in contract_nodes if contract.name not in CONTRACTS_FILTER]
  if len(contract_nodes) == 0:
      raise AssertionError('No base contract found.')

  # Get main contract. We're using the heuristic of filtering out popular libraries, and getting the 
  # contract that appears last in the source code. This is mostly needed so that we can stay in the LLM context limit
  main_contract = contract_nodes[-1]

  # Get main contract source code
  delimiters = main_contract.src.split(':')
  main_contract_source = source_code[int(delimiters[0]):int(delimiters[0]) + int(delimiters[1])]

  # Get the functions for which we want to generate unit tests
  functions = [item.name for item in main_contract.children() if item.nodeType == 'FunctionDefinition' and item.name != '' and item.visibility in ['public', 'external']]

  # Construct prompt
  prompt = prompt_template % (functions, main_contract_source)
  #print(prompt)

  # Query LLM for test code. 
  # TODO: Remove temporary placeholder

  print(main_contract)

  key = ''
  client = OpenAI(api_key=key)

  try:
     completion = client.chat.completions.create(
        model=Model,
        messages=[
          {"role": "system", "content": "your task is to generate Brownie unit tests for solidity functions"} 
          ,{"role": "user", "content": prompt}
        ]
      )
  except Exception as e:
     print("open ai model raised an error", e)

  #print(completion.choices[0].message)
  # Pattern to match text enclosed in ```python and ```
  pattern = r"```python\n(.*?)\n```"

  # Use re.DOTALL to make '.' match newline characters as well
  matches = re.findall(pattern, completion.choices[0].message.content, re.DOTALL)

  # Joining all matches with two newlines as a separator
  python_code = '\n\n'.join(matches)

  insert_test_code(index, Model, python_code)
