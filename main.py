import re
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import solcx
from py_solidity_parser.main import from_standard_output

from utils.prompt import prompt_template
from utils.compile_sol import compile_contract_standard
from utils.filters import CONTRACTS_FILTER
from utils.placeholders import ph_llm_response, ph_contract_source

# Read a random parquet file
table = pq.read_table('slither-audited-smart-contracts/data/raw/contracts0.parquet')

# Convert the file to a pandas dataframe
pd_table = table.to_pandas()

# Sample a random contract entry
contract = pd_table.sample()

# Get source code.
# source_code = contract.iloc[0, 1]
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
functions = [item.name for item in main_contract.children() if item.nodeType == 'FunctionDefinition' and item.name != '']

# Construct prompt
prompt = prompt_template % (functions, main_contract_source)

# Query LLM for test code. 
# TODO: Remove temporary placeholder
test_code = ph_llm_response

# Save resulting code to a python file

# Load into Brownie and run

# Assess coverage