import re

# Pattern to remove ANSI color escape codes
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def parse_cov_lines(lines: list[str]):
    # Dictionary with functions - coverage percentage
    func_cov = dict()
    contract_cov = dict()

    for line in lines:
        # Remove ANSI color escape codes
        line = ansi_escape.sub('', line)

        # Check if it's a contract line
        contract_res = re.search(r'contract:\s([A-z0-9]+)\s-\s(\d+\.\d+)%', line)
        if contract_res:
            contract_cov[contract_res.groups()[0]] = float(contract_res.groups()[1])
            continue

        # Check it it's a function line
        func_res = re.search(r'([A-z0-9]+\.[A-z0-9]+)\s-\s(\d+\.\d+)%', line)
        if func_res:
            func_cov[func_res.groups()[0]] = float(func_res.groups()[1])
            continue

    return contract_cov, func_cov