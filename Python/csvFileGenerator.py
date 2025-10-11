import pandas as pd
from faker import Faker
import random
import boto3

fake = Faker()

def generate_students(num_records=25):
    students = []
    for _ in range(num_records):
        students.append({
            "StudentID": fake.unique.uuid4(),
            "Name": fake.name(),
            "Age": random.randint(18, 25),
            "Gender": random.choice(["Male", "Female"]),
            "GPA": round(random.uniform(2.0, 4.0), 2),
            "Graduated": random.choice([True, False]),
            "EnrollmentDate": fake.date_between(start_date='-4y', end_date='today'),
            "Major": random.choice(["CS", "Math", "Physics", "Biology"]),
            "CreditsCompleted": random.randint(0, 120),
            "Email": fake.email()
        })
    return pd.DataFrame(students)

def generate_teachers(num_records=10):
    teachers = []
    for _ in range(num_records):
        teachers.append({
            "TeacherID": fake.unique.uuid4(),
            "Name": fake.name(),
            "Age": random.randint(25, 65),
            "Gender": random.choice(["Male", "Female"]),
            "Subject": random.choice(["CS", "Math", "Physics", "Biology"]),
            "HireDate": fake.date_between(start_date='-20y', end_date='today'),
            "FullTime": random.choice([True, False]),
            "Salary": round(random.uniform(40000, 120000), 2),
            "Email": fake.email(),
            "Phone": fake.phone_number()
        })
    return pd.DataFrame(teachers)

# Generate datasets
students_df = generate_students(125)
teachers_df = generate_teachers(110)

# Save to CSV
students_csv = r"C:\AI\Python\data\students.csv"
teachers_csv = r"C:\AI\Python\data\teachers.csv"
students_df.to_csv(students_csv, index=False)
teachers_df.to_csv(teachers_csv, index=False)

print("CSV files 'students.csv' and 'teachers.csv' created successfully.")

# Upload to S3
s3 = boto3.client('s3', region_name='us-east-1')
bucket_name = 'snowflakedemofile'
prefix = 'data/'

def upload_to_s3(local_path, s3_bucket, s3_key):
    with open(local_path, "rb") as f:
        s3.upload_fileobj(f, s3_bucket, s3_key)
    print(f"Uploaded {local_path} to s3://{s3_bucket}/{s3_key}")

upload_to_s3(students_csv, bucket_name, prefix + "students.csv")
upload_to_s3(teachers_csv, bucket_name, prefix + "teachers.csv")