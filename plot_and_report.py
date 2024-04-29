import sqlite3
import matplotlib.pyplot as plt
import numpy as np

def print_all_function_coverage():
    conn = sqlite3.connect('results.db')
    cur = conn.cursor()
    try:
        cur.execute('SELECT * FROM FunctionCoverage')
        rows = cur.fetchall()  # Fetch all results
        print("Function Coverage:")
        for row in rows:
            print(f"ID: {row[0]}, Prompt: {row[1]}, model name : {row[2]} Contract Address: {row[3]}, Function Name: {row[4]}, Coverage: {row[5]}")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()


def print_all_overall_statistics():
    conn = sqlite3.connect('results.db')
    cur = conn.cursor()
    try:
        cur.execute('SELECT * FROM OverallStatistics')
        rows = cur.fetchall()  # Fetch all results
        print("Overall Statistics:")
        for row in rows:
            print(f"ID: {row[0]}, Prompt: {row[1]}, model name: {row[2]}, Contract Address: {row[3]}, Crashed: {row[4]}, Failed: {row[5]}, Success: {row[6]}")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()



def fetch_data_for_model_quality_plot():
    conn = sqlite3.connect('results.db')
    cur = conn.cursor()
    data = {}
    try:
        # Fetching data for prompt '2' and grouping by model_name to sum up the statistics
        cur.execute('''
            SELECT model_name, SUM(crashed), SUM(failed), SUM(succ)
            FROM OverallStatistics
            WHERE prompt = '2'
            GROUP BY model_name
        ''')
        rows = cur.fetchall()
        for row in rows:
            model = row[0]
            crashed = row[1]
            failed = row[2]
            success = row[3]
            total = crashed + failed + success
            data[model] = {
                'Crashed': (crashed / total) * 100,
                'Failed': (failed / total) * 100,
                'Success': (success / total) * 100
            }
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()
    return data





def plot_model_quality():
    data = fetch_data_for_model_quality_plot()
    print(data)
    categories = ['Success', 'Crashed', 'Failed']
    models = ['gpt4', 'gpt35']
    width = 0.25  # width of the bars
    colors = {'Success': 'green', 'Crashed': 'orange', 'Failed': 'red'}  # Colors for each category

    fig, ax = plt.subplots()

    # Define positions for GPT-4 and GPT-3.5 bars
    gpt4_positions = [0.5 + i * 0.5 for i in range(len(categories))]  # GPT-4 bars on the left
    gpt35_positions = [3 + width + i * 0.5 for i in range(len(categories))]  # GPT-3.5 bars on the right

    # Assigning model positions to a dictionary for clarity
    positions = {'gpt4': gpt4_positions, 'gpt35': gpt35_positions}

    # Plotting bars for each model
    for model, offset in positions.items():
        model_data = [data.get(model, {}).get(cat, 0) for cat in categories]
        for idx, val in enumerate(model_data):
            ax.bar(offset[idx], val, width, color=colors[categories[idx]], label=categories[idx] if model == 'gpt4' and idx == 0 else "")

    # Setting chart title and labels
    ax.set_ylabel('Percentage')
    ax.set_title('Test Results by Model')
    
    # Set x-ticks to the middle of each group, making sure to align with bar groups
    ax.set_xticks([np.mean(val) for val in positions.values()])
    ax.set_xticklabels([model.upper() for model in models])

    # Adding legend and axis labels
    #ax.legend(title='Category')

    # Adding labels to each bar for clarity
    for rect, cat in zip(ax.patches, categories * len(models)):
        height = rect.get_height()
        ax.annotate(f'{cat}\n{height:.1f}%',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')

    plt.savefig('overall_performance.png', dpi=300, bbox_inches='tight')  # Save as PNG file with high resolution
    plt.show()





import sqlite3



def fetch_and_process_coverage_data():
    conn = sqlite3.connect('results.db')
    cur = conn.cursor()
    # Initialize dictionaries for each model
    coverage_data = {
        "gpt35": {"contract": [], "contract_func": [], "lib_func": []},
        "gpt4": {"contract": [], "contract_func": [], "lib_func": []}
    }
    current_contract = None
    current_model = None

    try:
        cur.execute('''
            SELECT model_name, function_name, coverage FROM FunctionCoverage
            WHERE prompt = '2' ORDER BY model_name
        ''')
        rows = cur.fetchall()

        for model_name, function_name, coverage in rows:
            coverage_value = float(coverage.strip('%'))

            # Determine the model from the function name


            if '.' not in function_name:
                # Update current contract and reset tracking if it's a main contract name
                current_contract = function_name
                coverage_data[model_name]["contract"].append(coverage_value)
                print(current_contract, coverage_value)
            else:
                # Classify function based on its name containing the current contract
                if current_contract and function_name.startswith(current_contract + '.'):
                    coverage_data[model_name]["contract_func"].append(coverage_value)
                    print(function_name,coverage_value )
                else:
                    coverage_data[model_name]["lib_func"].append(coverage_value)

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

    # Calculate averages for each category in each model
    results = {}
    for model, data in coverage_data.items():
        results[model] = {
            "contract_avg": sum(data["contract"]) / len(data["contract"]) if data["contract"] else 0,
            "contract_func_avg": sum(data["contract_func"]) / len(data["contract_func"]) if data["contract_func"] else 0,
            "lib_func_avg": sum(data["lib_func"]) / len(data["lib_func"]) if data["lib_func"] else 0
        }

    return results







import matplotlib.pyplot as plt

def plot_coverage_comparison():
    coverage_data = fetch_and_process_coverage_data()  # This function should return a dictionary with models as keys

    categories = ['Contract', 'Contract Functions', 'Library Functions']  # Category labels
    models = ['gpt4', 'gpt35']  # Model labels
    colors = ['black', 'blue', 'brown']  # Colors for each category
    width = 0.25  # Width of each bar
    gap_between_groups = 0.5  # Gap between groups of models

    # Start plotting
    fig, ax = plt.subplots()

    # Variables to store the position of the first and last bar in each group
    group_start_end_positions = []

    # Plot bars for each model and category
    for i, model in enumerate(models):
        # Calculate the starting position for each model's group of bars
        base_offset = i * (len(categories) * width + gap_between_groups)
        offsets = [base_offset + j * width for j in range(len(categories))]
        averages = [coverage_data[model.lower()]['contract_avg'], coverage_data[model.lower()]['contract_func_avg'], coverage_data[model.lower()]['lib_func_avg']]
        
        # Plot bars and store positions
        for idx, (avg, color) in enumerate(zip(averages, colors)):
            ax.bar(offsets[idx], avg, width, color=color, label=categories[idx] if i == 0 else "")
        
        # Store the first and last positions for x-tick calculation
        group_start_end_positions.append((offsets[0], offsets[-1] + width))

    # Set labels and titles
    ax.set_ylabel('Average Coverage (%)')
    ax.set_title('Average Function Coverage by Model and Type')

    # Calculate and set x-tick positions to be centered in each group
    x_ticks = [(start + end) / 2 for start, end in group_start_end_positions]
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(models)  # Set model names as x-tick labels

    ax.legend(title='Coverage Type', loc='upper left')
    # Save the figure
    plt.savefig('coverage_comparison.png', dpi=300, bbox_inches='tight')  # Save as PNG file with high resolution
    plt.show()


plot_coverage_comparison()










plot_model_quality()







#print_all_overall_statistics()
#print_all_function_coverage()

