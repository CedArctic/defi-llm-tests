prompt_template = """
The below code is a smart contract written in Solidity. Please write Python code that uses the Brownie framework and generate unit tests for these functions: %s. when you write tests that send some transactions make sure the amount of the transactions are well below 100 because the maximum balance of each node in ganache is 100. 

Solidity code: 
%s
"""