import pandas as pd
import glob
import os
import re

# --- 1. CONFIGURATION ---
# Replace this with the path to the folder containing your 12 CSVs
folder_path = r"data"


def normalize_columns(df):
    """Standardise common column-name variations across monthly files."""
    columns = list(df.columns)

    def find_column(*candidates):
        lower_candidates = {c.strip().lower() for c in candidates}
        for col in columns:
            if str(col).strip().lower() in lower_candidates:
                return col

        normalized_candidates = {re.sub(r'[^a-z0-9]+', '', c) for c in lower_candidates}
        for col in columns:
            if re.sub(r'[^a-z0-9]+', '', str(col).strip().lower()) in normalized_candidates:
                return col
        return None

    org_code_col = find_column('org code', 'orgcode', 'org_code', 'org-code')
    org_name_col = find_column('org name', 'orgname', 'org_name', 'org-name')
    parent_col = find_column('parent name', 'parent org', 'parentorg', 'parent_org', 'parent org name', 'parentorgname')

    rename_map = {}
    if org_code_col:
        rename_map[org_code_col] = 'org code'
    if org_name_col:
        rename_map[org_name_col] = 'org name'
    if parent_col:
        rename_map[parent_col] = 'parent name'

    df = df.rename(columns=rename_map)

    if 'org code' not in df.columns:
        print("WARNING: Could not find an organisation code column in one of the files.")
        return None

    if 'org name' not in df.columns:
        df['org name'] = ''
    if 'parent name' not in df.columns:
        df['parent name'] = ''

    return df


def norm_text(value):
    """Lower-case, trimmed version of a text value, used only for comparison."""
    if pd.isna(value):
        return ''
    return str(value).strip().lower()


# Find all CSV files and sort them (e.g., 01_Jan.csv, 02_Feb.csv)
files = sorted(glob.glob(os.path.join(folder_path, "*.csv")))

if not files:
    print("No CSV files found in the specified directory!")
    exit()

print(f"Found {len(files)} files. Starting analysis...")

# --- 2. LOAD DATA ---
monthly_data = {}

for f in files:
    file_name = os.path.basename(f)
    df = pd.read_csv(f)

    df = normalize_columns(df)
    if df is None:
        print(f"WARNING: Skipping {file_name} because it does not contain an organisation code column.")
        continue

    # Remove any duplicate org codes within the same month just in case
    df = df.drop_duplicates(subset=['org code'])

    # Add normalised comparison keys (not shown in the final report)
    df['_name_key'] = df['org name'].apply(norm_text)
    df['_parent_key'] = df['parent name'].apply(norm_text)

    monthly_data[file_name] = df

file_names = list(monthly_data.keys())

recoded_rows = []   # same identity (org name + parent name), code changed
renamed_rows = []   # same code, identity changed
added_rows = []     # genuinely new code, no matching identity elsewhere
removed_rows = []   # genuinely gone code, no matching identity elsewhere

# --- 3. COMPARE MONTH OVER MONTH ---
for i in range(1, len(file_names)):
    prev_file = file_names[i - 1]
    curr_file = file_names[i]

    prev_df = monthly_data[prev_file]
    curr_df = monthly_data[curr_file]

    prev_codes = set(prev_df['org code'])
    curr_codes = set(curr_df['org code'])

    common_codes = prev_codes & curr_codes
    added_codes = curr_codes - prev_codes
    removed_codes = prev_codes - curr_codes

    # --- 3a. Same code kept: has the identity underneath it changed? ---
    prev_indexed = prev_df.set_index('org code')
    curr_indexed = curr_df.set_index('org code')

    for code in common_codes:
        prev_row = prev_indexed.loc[code]
        curr_row = curr_indexed.loc[code]
        if isinstance(prev_row, pd.DataFrame):
            prev_row = prev_row.iloc[0]
        if isinstance(curr_row, pd.DataFrame):
            curr_row = curr_row.iloc[0]

        name_changed = prev_row['_name_key'] != curr_row['_name_key']
        parent_changed = prev_row['_parent_key'] != curr_row['_parent_key']

        if name_changed or parent_changed:
            if name_changed and parent_changed:
                change_type = 'Org name and parent name changed'
            elif name_changed:
                change_type = 'Org name changed'
            else:
                change_type = 'Parent name changed'

            renamed_rows.append({
                'Status': change_type,
                'Previous_Month': prev_file,
                'Current_Month': curr_file,
                'org code': code,
                'Previous_org_name': prev_row['org name'],
                'Current_org_name': curr_row['org name'],
                'Previous_parent_name': prev_row['parent name'],
                'Current_parent_name': curr_row['parent name'],
            })

    # --- 3b. Code changed: is the identity underneath it the same (a recode)? ---
    removed_df = prev_df[prev_df['org code'].isin(removed_codes)].copy()
    added_df = curr_df[curr_df['org code'].isin(added_codes)].copy()

    removed_lookup = {}
    for _, row in removed_df.iterrows():
        key = (row['_name_key'], row['_parent_key'])
        removed_lookup.setdefault(key, []).append(row)

    added_lookup = {}
    for _, row in added_df.iterrows():
        key = (row['_name_key'], row['_parent_key'])
        added_lookup.setdefault(key, []).append(row)

    matched_removed_codes = set()
    matched_added_codes = set()

    for key, removed_list in removed_lookup.items():
        # Skip blank name/parent pairs — matching on nothing is not reliable
        if key == ('', ''):
            continue

        if key in added_lookup:
            added_list = added_lookup[key]
            ambiguous = len(removed_list) != 1 or len(added_list) != 1
            pair_count = max(len(removed_list), len(added_list))

            for idx in range(pair_count):
                old_row = removed_list[idx] if idx < len(removed_list) else None
                new_row = added_list[idx] if idx < len(added_list) else None

                recoded_rows.append({
                    'Status': 'Recoded (ambiguous match — check by eye)' if ambiguous else 'Recoded',
                    'Previous_Month': prev_file,
                    'Current_Month': curr_file,
                    'org name': old_row['org name'] if old_row is not None else new_row['org name'],
                    'parent name': old_row['parent name'] if old_row is not None else new_row['parent name'],
                    'Previous_org_code': old_row['org code'] if old_row is not None else '',
                    'Current_org_code': new_row['org code'] if new_row is not None else '',
                })

                if old_row is not None:
                    matched_removed_codes.add(old_row['org code'])
                if new_row is not None:
                    matched_added_codes.add(new_row['org code'])

    # --- 3c. Whatever is left over is a genuine addition or removal ---
    true_removed = removed_df[~removed_df['org code'].isin(matched_removed_codes)]
    true_added = added_df[~added_df['org code'].isin(matched_added_codes)]

    for _, row in true_removed.iterrows():
        removed_rows.append({
            'Status': 'Removed',
            'Previous_Month': prev_file,
            'Current_Month': curr_file,
            'org code': row['org code'],
            'org name': row['org name'],
            'parent name': row['parent name'],
        })

    for _, row in true_added.iterrows():
        added_rows.append({
            'Status': 'Added',
            'Previous_Month': prev_file,
            'Current_Month': curr_file,
            'org code': row['org code'],
            'org name': row['org name'],
            'parent name': row['parent name'],
        })

# --- 4. EXPORT TO EXCEL ---
output_file = "Org_Changes_Report.xlsx"

total_changes = len(recoded_rows) + len(renamed_rows) + len(added_rows) + len(removed_rows)

if total_changes == 0:
    print("\nNo changes found! The org lists are identical across all months.")
else:
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        summary = pd.DataFrame({
            'Category': [
                'Recoded (same org name and parent name, code changed)',
                'Renamed or reparented (same code, org name and/or parent name changed)',
                'Added (new code, no matching identity found)',
                'Removed (code gone, no matching identity found)',
            ],
            'Count': [len(recoded_rows), len(renamed_rows), len(added_rows), len(removed_rows)],
        })
        summary.to_excel(writer, sheet_name='Summary', index=False)

        if recoded_rows:
            pd.DataFrame(recoded_rows).to_excel(writer, sheet_name='Recoded', index=False)
        if renamed_rows:
            pd.DataFrame(renamed_rows).to_excel(writer, sheet_name='Renamed_or_Reparented', index=False)
        if added_rows:
            pd.DataFrame(added_rows).to_excel(writer, sheet_name='Added', index=False)
        if removed_rows:
            pd.DataFrame(removed_rows).to_excel(writer, sheet_name='Removed', index=False)

    print(f"\nSuccess! Found {total_changes} changes across the year.")
    print(f"  Recoded (same identity, new code):          {len(recoded_rows)}")
    print(f"  Renamed or reparented (same code):          {len(renamed_rows)}")
    print(f"  Genuinely added:                            {len(added_rows)}")
    print(f"  Genuinely removed:                          {len(removed_rows)}")
    print(f"\nReport saved as: {output_file} in your current directory.")