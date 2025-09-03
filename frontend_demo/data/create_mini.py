import pandas as pd

# Read the CSV
df = pd.read_csv('big_tech.csv')

# Define the major tech companies we want to include
companies = ['APPLE INC.', 'AMAZON.COM SERVICES LLC', 'IBM', 'MICROSOFT CORPORATION', 
            'ORACLE CORPORATION', 'INTEL CORPORATION', 'BYTEDANCE INC.', '"GOOGLE']

# Filter for these companies and get first 20 entries each
mini_df = pd.DataFrame()
for company in companies:
    company_data = df[df['client_name'] == company].head(20)
    mini_df = pd.concat([mini_df, company_data], ignore_index=True)

# Remove the issue_text column
columns_to_keep = [col for col in mini_df.columns if col != 'issue_text']
mini_df = mini_df[columns_to_keep]

# Save to new CSV
mini_df.to_csv('big_oil_mini.csv', index=False)

print(f'Created big_oil_mini.csv with {len(mini_df)} total entries')
print(f'Columns: {list(mini_df.columns)}')
print('Entries per company:')
print(mini_df['client_name'].value_counts())