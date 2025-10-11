import json, boto3
import snowflake.connector

def get_secret(secret_name, region="us-east-1"):
    sm = boto3.client("secretsmanager", region_name=region)
    s = sm.get_secret_value(SecretId=secret_name)
    return json.loads(s["SecretString"])

def lambda_handler(event, context):
    secret = get_secret("snowflake/demo_user")
    query = event.get("sql", "SELECT current_version()")

    conn = snowflake.connector.connect(
        user=secret["user"],
        password=secret["password"],
        account=secret["account"],
        warehouse=secret["warehouse"],
        database=secret["database"],
        schema=secret["schema"]
    )

    cs = conn.cursor()
    cs.execute(query)
    rows = cs.fetchall()
    cs.close()
    conn.close()

    return {"query": query, "rows": rows}
