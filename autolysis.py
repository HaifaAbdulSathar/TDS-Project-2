# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "seaborn",
#   "pandas",
#   "matplotlib",
#   "httpx",
#   "chardet",
#   "numpy",
#   "platformdirs",
#   "python-dotenv",
#   "rich",
# ]
# ///


import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import os
import sys
import requests

# Function to load dataset
def load_dataset(file_path):
    try:
        data = pd.read_csv(file_path,encoding='latin-1')
        print(f"Dataset loaded: {file_path} with shape {data.shape}")
        return data
    except Exception as e:
        print(f"Error loading dataset: {e}")
        sys.exit(1)

# Function to analyze dataset
def analyze_dataset(data):
    numeric_data = data.select_dtypes(include=[np.number])
    correlation_matrix = numeric_data.corr()
    summary_stats = numeric_data.describe().T
    summary_stats["skewness"] = numeric_data.skew()
    summary_stats["kurtosis"] = numeric_data.kurtosis()

    # Detecting outliers
    outliers = numeric_data.apply(lambda x: ((x < (x.quantile(0.25) - 1.5 * (x.quantile(0.75) - x.quantile(0.25)))) |
                                             (x > (x.quantile(0.75) + 1.5 * (x.quantile(0.75) - x.quantile(0.25))))).sum())

    analysis_summary = {
        "columns": data.columns.tolist(),
        "missing_values": data.isnull().sum().to_dict(),
        "summary_stats": summary_stats.to_dict(orient="index"),
        "correlation_matrix": correlation_matrix.to_dict(),
        "outliers": outliers.to_dict()
    }
    return analysis_summary

# Function to create visualizations
def create_visualizations(data, max_visuals=3):
    numeric_data = data.select_dtypes(include=[np.number])
    visualizations = []

    # 1. Heatmap of correlation matrix
    plt.figure(figsize=(10, 8))
    sns.heatmap(numeric_data.corr(), annot=True, cmap='coolwarm', fmt=".2f")
    plt.title("Correlation Heatmap")
    filename = "correlation_heatmap.png"
    plt.savefig(filename, dpi=300)
    plt.close()
    visualizations.append(("Correlation Heatmap", filename))

    # 2. Histogram for most skewed column
    most_skewed_column = numeric_data.skew().idxmax()
    plt.figure(figsize=(8, 6))
    sns.histplot(data[most_skewed_column], kde=True, color='blue', bins=20)
    plt.title(f"Distribution of {most_skewed_column}")
    filename = f"histogram_{most_skewed_column}.png"
    plt.savefig(filename, dpi=300)
    plt.close()
    visualizations.append((f"Histogram of {most_skewed_column}", filename))

    # 3. Boxplot for column with highest variance
    highest_variance_column = numeric_data.var().idxmax()
    plt.figure(figsize=(8, 6))
    sns.boxplot(x=data[highest_variance_column], color='orange')
    plt.title(f"Boxplot of {highest_variance_column}")
    filename = f"boxplot_{highest_variance_column}.png"
    plt.savefig(filename, dpi=300)
    plt.close()
    visualizations.append((f"Boxplot of {highest_variance_column}", filename))

    return visualizations[:max_visuals]

# Function to communicate with the LLM
def call_openai_api(prompt, model="gpt-4o-mini", max_tokens=300):
    api_token = os.environ.get("AIPROXY_TOKEN")
    if not api_token:
        print("AIPROXY_TOKEN is not set. Please set it and try again.")
        sys.exit(1)

    url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a data science assistant. Help analyze the dataset."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print(f"LLM API error: {response.status_code}, {response.text}")
        sys.exit(1)

# Function to generate narrative
def generate_narrative(analysis, visualizations):
    prompt = (
        f"Here is the dataset analysis:\n"
        f"- Columns: {analysis['columns']}\n"
        f"- Missing values: {analysis['missing_values']}\n"
        f"- Summary statistics: {analysis['summary_stats']}\n"
        f"- Outliers: {analysis['outliers']}\n"
        f"- Correlations: {analysis['correlation_matrix']}\n"
        "Please provide a detailed narrative describing the data, insights, and implications.Sound like a human"
    )
    narrative = call_openai_api(prompt)

    visualization_descriptions = "\n".join([f"- {desc}: ![{desc}]({path})" for desc, path in visualizations])
    narrative += f"\n\n## Visualizations\n\n{visualization_descriptions}"
    return narrative

# Main function
def main():
    if len(sys.argv) < 2:
        print("Please provide a dataset filename as an argument.")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)

    data = load_dataset(file_path)
    analysis = analyze_dataset(data)
    visualizations = create_visualizations(data)

    if not visualizations:
        print("No visualizations created. Check your dataset for numeric columns.")
        sys.exit(1)

    narrative = generate_narrative(analysis, visualizations)
    with open("README.md", "w") as f:
        f.write("# Automated Data Analysis\n\n")
        f.write("## Summary\n\n")
        f.write(narrative)
        print("Analysis completed. README.md and visualizations created.")

if __name__ == "__main__":
    main()
