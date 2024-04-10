from solcx import compile_source, compile_standard


def compile_contract(contract_source_code):
    # Compile the contract source code
    compiled_contract = compile_source(contract_source_code)

    # Extract contract interface and bytecode
    contract_interface = compiled_contract['<stdin>:MyContract']
    # contract_bytecode = contract_interface['bin']

    return contract_interface


def compile_contract_standard(contract_source_code):
    # Define compiler input
    compiler_input = {
        "language": "Solidity",
        "sources": {
            "Contract.sol": {
                "content": contract_source_code
            }
        },
        "settings": {
            # "outputSelection": {
            #     "*": {
            #         "*": ["*"]
            #     }
            # },
            "outputSelection": {
                "*": {
                    "*": [
                        "metadata", "evm.bytecode" # Enable the metadata and bytecode outputs of every single contract., "evm.bytecode.sourceMap" // Enable the source map output of every single contract.
                    ],
                    "": [
                        "ast" # Enable the AST output of every single file.
                    ]
                },
                # Enable the abi and opcodes output of MyContract defined in file def .
                "def": {
                    "Contract": ["abi", "evm.bytecode.opcodes"]
                }
            },
        }
    }

    # Compile the contract source code
    compiled_contract = compile_standard(compiler_input)

    # Extract contract interface and bytecode
    # contract_interface = compiled_contract["contracts"]["MyContract.sol"]["MyContract"]
    # contract_bytecode = contract_interface["evm"]["bytecode"]["object"]

    return compiled_contract
