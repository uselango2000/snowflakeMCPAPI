import pandas as pd
import random
import numpy as np

# Generate sample data
data = {
    "StudentID": [f"S{i:03d}" for i in range(1, 26)],  # String IDs
    "Name": [f"Student_{i}" for i in range(1, 26)],  # Names
    "Age": [random.randint(18, 25) for _ in range(25)],  # Integer ages
    "Gender": [random.choice(["Male", "Female"]) for _ in range(25)],  # Gender
    "GPA": [round(random.uniform(2.0, 4.0), 2) for _ in range(25)],  # Float GPAs
    "Graduated": [random.choice([True, False]) for _ in range(25)],  # Boolean
    "EnrollmentDate": pd.date_range(start="2020-01-01", periods=25).tolist(),  # Dates
    "Major": [random.choice(["CS", "Math", "Physics", "Biology"]) for _ in range(25)],  # String majors
    "CreditsCompleted": [random.randint(0, 120) for _ in range(25)],  # Integer credits
    "Email": [f"student{i}@university.com" for i in range(1, 26)],  # Email addresses
}

# Create a DataFrame
df = pd.DataFrame(data)

# Save as a Parquet file
parquet_file = "students.parquet"
df.to_parquet(parquet_file, engine="pyarrow", index=False)

print(f"Parquet file '{parquet_file}' created successfully with 25 records.")