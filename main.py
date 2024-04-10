import os
import re
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import solcx
import brownie
import pytest
from py_solidity_parser.main import from_standard_output

from utils.prompt import prompt_template
from utils.compile_sol import compile_contract_standard
from utils.filters import CONTRACTS_FILTER
from utils.placeholders import ph_llm_response, ph_contract_source
from utils.parsers import parse_cov_lines

# Read a random parquet file
table = pq.read_table('slither-audited-smart-contracts/data/raw/contracts0.parquet')

# Convert the file to a pandas dataframe
pd_table = table.to_pandas()

# Sample a random contract entry
contract = pd_table.sample()

# Get source code.
# source_code = contract.iloc[0, 1]
contract_address = contract.iloc[0, 0]
# TODO: Remove temporary placeholder source code used for testing
source_code = ph_contract_source

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
compiler_out_json = compile_contract_standard(source_code)

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

# Query LLM for test code. 
# TODO: Remove temporary placeholder
test_code = ph_llm_response

# Create Brownie project directory
if not os.path.isdir(f"brownie_projects/p_{contract_address}"):
    os.makedirs(f"brownie_projects/p_{contract_address}")

# Initialize Brownie project
brownie.project.new(f"brownie_projects/p_{contract_address}")

# Write contract to Brownie project
with open(f"brownie_projects/p_{contract_address}/contracts/Contract.sol", "w") as f:
    f.write(source_code)

# Write tests to Brownie project
# Note: test filenames must be in one of the following formats "test_*.py" or "_test.py"
with open(f"brownie_projects/p_{contract_address}/tests/llm_test.py", "w") as f:
    f.write(test_code)

# Load & Compile project using Brownie
b_project = brownie.project.load(f"brownie_projects/p_{contract_address}", name="Contract")

# Run tests and assess coverage
os.chdir(f"brownie_projects/p_{contract_address}")
try:
    pytest.main(['tests/'])
except:
    print("Pytest raised error during testing.")
os.chdir(f"../..")
# brownie.test.coverage.get_coverage_eval()
coverage_lines = brownie.test.output._build_coverage_output(brownie.test.coverage.get_merged_coverage_eval())
contract_cov, func_cov = parse_cov_lines(coverage_lines)

# Print results
print(f"Contract coverage: {contract_cov}")
print(f"Function coverage: {func_cov}")